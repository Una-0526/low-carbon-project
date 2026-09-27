<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createCarbonRecord,
  deleteCarbonRecord,
  getCarbonFactors,
  getCarbonRecords,
  updateCarbonRecord,
} from '../../api'

const BUILDINGS = ['教学楼A', '教学楼B', '宿舍楼', '图书馆', '食堂', '公务车']

const loading = ref(false)
const records = ref([])
const factors = ref({})
const editingId = ref(null)
const filterBuilding = ref('')
const filterYear = ref('')

const formRef = ref()
const form = reactive({
  building: '',
  monthStr: '',
  electricity_kwh: 0,
  night_electricity_kwh: 0,
  natural_gas_m3: 0,
  gasoline_l: 0,
})

const rules = {
  building: [{ required: true, message: '请选择建筑', trigger: 'change' }],
  monthStr: [{ required: true, message: '请选择年月', trigger: 'change' }],
}

// 实时换算预览：Scope2 = 电 × 电网因子；Scope1 = 气 × 因子 + 油 × 因子
const preview = computed(() => {
  const f = factors.value
  const scope2 = form.electricity_kwh * (f.grid_electricity ?? 0)
  const scope1 = form.natural_gas_m3 * (f.natural_gas ?? 0) + form.gasoline_l * (f.gasoline ?? 0)
  return { scope1, scope2, total: scope1 + scope2 }
})

const filteredRecords = computed(() =>
  records.value.filter(
    (r) =>
      (!filterBuilding.value || r.building === filterBuilding.value) &&
      (!filterYear.value || String(r.year) === filterYear.value),
  ),
)

async function loadRecords() {
  loading.value = true
  try {
    const { data } = await getCarbonRecords()
    records.value = data
  } finally {
    loading.value = false
  }
}

function resetForm() {
  editingId.value = null
  form.building = ''
  form.monthStr = ''
  form.electricity_kwh = 0
  form.night_electricity_kwh = 0
  form.natural_gas_m3 = 0
  form.gasoline_l = 0
  formRef.value?.clearValidate()
}

function startEdit(row) {
  editingId.value = row.id
  form.building = row.building
  form.monthStr = `${row.year}-${String(row.month).padStart(2, '0')}`
  form.electricity_kwh = row.electricity_kwh
  form.night_electricity_kwh = row.night_electricity_kwh
  form.natural_gas_m3 = row.natural_gas_m3
  form.gasoline_l = row.gasoline_l
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function submit() {
  await formRef.value.validate()
  const [year, month] = form.monthStr.split('-').map(Number)
  const payload = {
    building: form.building,
    year,
    month,
    electricity_kwh: form.electricity_kwh,
    night_electricity_kwh: form.night_electricity_kwh,
    natural_gas_m3: form.natural_gas_m3,
    gasoline_l: form.gasoline_l,
    pv_kwh: 0,
    storage_kwh: 0,
    saving_kwh: 0,
  }
  if (editingId.value) {
    const { data } = await updateCarbonRecord(editingId.value, payload)
    ElMessage.success(`已修改并重算：总排放 ${data.emissions.total_emission.toFixed(1)} kgCO2e`)
  } else {
    const { data } = await createCarbonRecord(payload)
    ElMessage.success(`已录入并核算：总排放 ${data.emissions.total_emission.toFixed(1)} kgCO2e`)
  }
  resetForm()
  await loadRecords()
}

async function remove(row) {
  await ElMessageBox.confirm(
    `确认删除 ${row.building} ${row.year}-${String(row.month).padStart(2, '0')} 的能耗记录？`,
    '删除确认',
    { type: 'warning' },
  )
  await deleteCarbonRecord(row.id)
  ElMessage.success('已删除')
  await loadRecords()
}

const fmt = (v) => (v ?? 0).toFixed(1)

onMounted(async () => {
  const { data } = await getCarbonFactors()
  factors.value = Object.fromEntries(data.map((f) => [f.factor_key, f.factor]))
  await loadRecords()
})
</script>

<template>
  <div v-loading="loading">
    <!-- 录入 / 修改表单 -->
    <el-card :header="editingId ? '修改能耗记录' : '录入建筑能耗'" class="form-card">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" class="form">
        <el-form-item label="建筑" prop="building">
          <el-select v-model="form.building" placeholder="选择建筑" class="w">
            <el-option v-for="b in BUILDINGS" :key="b" :label="b" :value="b" />
          </el-select>
        </el-form-item>
        <el-form-item label="年月" prop="monthStr">
          <el-date-picker v-model="form.monthStr" type="month" value-format="YYYY-MM"
                          placeholder="选择年月" class="w" />
        </el-form-item>
        <el-form-item label="用电量 (kWh)">
          <el-input-number v-model="form.electricity_kwh" :min="0" :step="100" :controls="false" class="w" />
        </el-form-item>
        <el-form-item label="夜间用电 (kWh)">
          <el-input-number v-model="form.night_electricity_kwh" :min="0" :step="100" :controls="false" class="w" />
          <span class="tip">22:00-6:00 电量，用于异常诊断，应 ≤ 用电量</span>
        </el-form-item>
        <el-form-item label="天然气 (m³)">
          <el-input-number v-model="form.natural_gas_m3" :min="0" :step="10" :controls="false" class="w" />
        </el-form-item>
        <el-form-item label="汽油 (L)">
          <el-input-number v-model="form.gasoline_l" :min="0" :step="10" :controls="false" class="w" />
        </el-form-item>
        <el-form-item label="实时换算">
          <div class="preview">
            Scope2（用电）{{ preview.scope2.toFixed(1) }} kg ＋
            Scope1（燃气/燃油）{{ preview.scope1.toFixed(1) }} kg ＝
            <b>总排放 {{ preview.total.toFixed(1) }} kgCO2e</b>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="submit">{{ editingId ? '保存修改' : '提交录入' }}</el-button>
          <el-button v-if="editingId" @click="resetForm">取消编辑</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 历史记录 -->
    <el-card header="历史录入记录" class="mt">
      <div class="filters">
        <el-select v-model="filterBuilding" placeholder="全部建筑" clearable class="filter">
          <el-option v-for="b in BUILDINGS" :key="b" :label="b" :value="b" />
        </el-select>
        <el-select v-model="filterYear" placeholder="全部年份" clearable class="filter filter-sm">
          <el-option v-for="y in [...new Set(records.map((r) => r.year))].sort().reverse()"
                     :key="y" :label="y" :value="String(y)" />
        </el-select>
        <span class="count">共 {{ filteredRecords.length }} 条</span>
      </div>
      <el-table :data="filteredRecords" size="small" stripe>
        <el-table-column prop="building" label="建筑" width="90" />
        <el-table-column label="年月" width="80">
          <template #default="{ row }">{{ row.year }}-{{ String(row.month).padStart(2, '0') }}</template>
        </el-table-column>
        <el-table-column prop="semester" label="学期" width="110" />
        <el-table-column label="用电 (kWh)" width="100" align="right">
          <template #default="{ row }">{{ fmt(row.electricity_kwh) }}</template>
        </el-table-column>
        <el-table-column label="燃气 (m³)" width="90" align="right">
          <template #default="{ row }">{{ fmt(row.natural_gas_m3) }}</template>
        </el-table-column>
        <el-table-column label="汽油 (L)" width="80" align="right">
          <template #default="{ row }">{{ fmt(row.gasoline_l) }}</template>
        </el-table-column>
        <el-table-column label="Scope1 (kg)" width="100" align="right">
          <template #default="{ row }">{{ fmt(row.emissions.scope1) }}</template>
        </el-table-column>
        <el-table-column label="Scope2 (kg)" width="100" align="right">
          <template #default="{ row }">{{ fmt(row.emissions.scope2) }}</template>
        </el-table-column>
        <el-table-column label="总排放 (kg)" width="105" align="right">
          <template #default="{ row }">
            <b>{{ fmt(row.emissions.total_emission) }}</b>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="startEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.mt {
  margin-top: 16px;
}

.form-card {
  max-width: 560px;
}

.w {
  width: 220px;
}

.tip {
  margin-left: 10px;
  font-size: 12px;
  color: #909399;
}

.preview {
  font-size: 13px;
  color: #606266;
  background: #f5f7fa;
  padding: 6px 10px;
  border-radius: 4px;
}

.filters {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
}

.filter {
  width: 140px;
}

.filter-sm {
  width: 110px;
}

.count {
  font-size: 13px;
  color: #909399;
  margin-left: auto;
}
</style>
