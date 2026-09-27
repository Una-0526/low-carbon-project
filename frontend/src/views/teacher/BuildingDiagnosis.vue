<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createSolution,
  deleteSolution,
  getBuildingDiagnosis,
  getSolutions,
  updateSolution,
} from '../../api'

const loading = ref(false)
const diagnoses = ref([])
const solutions = ref([])

const CATEGORY_TAG = {
  光伏: 'warning',
  储能: 'primary',
  节能改造: 'success',
  峰谷策略: 'info',
}

async function fetchAll() {
  loading.value = true
  try {
    const [d, s] = await Promise.all([getBuildingDiagnosis(), getSolutions()])
    diagnoses.value = d.data
    solutions.value = s.data
  } finally {
    loading.value = false
  }
}

// ---------- 方案编辑 ----------
const dialogVisible = ref(false)
const editingId = ref(null) // null = 新增
const submitting = ref(false)
const form = reactive({
  name: '',
  category: '光伏',
  annual_electricity_kwh: null,
  investment: null,
  electricity_price: null,
  factor: null,
  description: '',
})

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    name: '', category: '光伏', annual_electricity_kwh: null,
    investment: null, electricity_price: null, factor: null, description: '',
  })
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name, category: row.category,
    annual_electricity_kwh: row.annual_electricity_kwh,
    investment: row.investment, electricity_price: row.electricity_price,
    factor: row.factor, description: row.description || '',
  })
  dialogVisible.value = true
}

async function onSubmit() {
  submitting.value = true
  try {
    const payload = { ...form, factor: form.factor || null }
    if (editingId.value === null) {
      await createSolution(payload)
      ElMessage.success('方案已添加')
    } else {
      await updateSolution(editingId.value, payload)
      ElMessage.success('方案已更新')
    }
    dialogVisible.value = false
    await fetchAll()
  } finally {
    submitting.value = false
  }
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除方案「${row.name}」？`, '删除方案', { type: 'warning' })
  } catch {
    return
  }
  await deleteSolution(row.id)
  ElMessage.success('已删除')
  await fetchAll()
}

function fmtMoney(v) {
  return Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

onMounted(fetchAll)
</script>

<template>
  <div v-loading="loading">
    <!-- 建筑异常诊断 -->
    <el-card header="建筑异常诊断（本月碳排放环比 > 15% 且 夜间用电占比 > 40% 判定为异常）">
      <el-table :data="diagnoses" stripe>
        <el-table-column prop="building" label="建筑" width="110" fixed />
        <el-table-column label="本月 / 上月碳排放（tCO2e）" width="220">
          <template #default="{ row }">
            <span v-if="row.current_emission_kg != null && row.last_emission_kg != null">
              {{ (row.current_emission_kg / 1000).toFixed(2) }} / {{ (row.last_emission_kg / 1000).toFixed(2) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="环比" width="120">
          <template #default="{ row }">
            <template v-if="row.mom_change_pct != null">
              <el-tag :type="row.mom_change_pct > 15 ? 'danger' : 'success'" size="small" effect="plain">
                {{ row.mom_change_pct >= 0 ? '+' : '' }}{{ row.mom_change_pct }}%
              </el-tag>
            </template>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="夜间用电占比" min-width="160">
          <template #default="{ row }">
            <template v-if="row.night_ratio_pct != null">
              <el-progress
                :percentage="row.night_ratio_pct"
                :color="row.night_ratio_pct > 40 ? '#f56c6c' : '#67c23a'"
                :stroke-width="10"
                class="night-bar"
              />
            </template>
            <span v-else class="muted">无用电数据</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === '异常' ? 'danger' : row.status === '正常' ? 'success' : 'info'" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="诊断结论" min-width="280" show-overflow-tooltip />
      </el-table>
    </el-card>

    <!-- 方案库 -->
    <el-card class="mt">
      <template #header>
        <div class="toolbar">
          <span>节能减碳方案库（年减碳量 = 电量 × 因子，年省电费 = 电量 × 电价，回收期 = 投资 ÷ 年省电费）</span>
          <el-button type="success" @click="openCreate">新增方案</el-button>
        </div>
      </template>
      <el-table :data="solutions" stripe>
        <el-table-column prop="name" label="方案" min-width="180" show-overflow-tooltip />
        <el-table-column label="类别" width="110">
          <template #default="{ row }">
            <el-tag :type="CATEGORY_TAG[row.category] || 'info'" size="small">{{ row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="年覆盖电量" width="130">
          <template #default="{ row }">{{ fmtMoney(row.annual_electricity_kwh) }} kWh</template>
        </el-table-column>
        <el-table-column label="投资" width="130">
          <template #default="{ row }">{{ fmtMoney(row.investment) }} 元</template>
        </el-table-column>
        <el-table-column label="年减碳量" width="140">
          <template #default="{ row }">
            <span class="green">{{ (row.annual_carbon_reduction_kg / 1000).toFixed(1) }} t</span>
          </template>
        </el-table-column>
        <el-table-column label="年省电费" width="130">
          <template #default="{ row }">{{ fmtMoney(row.annual_saving_yuan) }} 元</template>
        </el-table-column>
        <el-table-column label="回收期" width="100">
          <template #default="{ row }">
            <span v-if="row.payback_years != null">{{ row.payback_years }} 年</span>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button type="danger" size="small" plain @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 方案编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId === null ? '新增方案' : '编辑方案'" width="520px">
      <el-form label-width="110px">
        <el-form-item label="方案名称">
          <el-input v-model="form.name" maxlength="50" placeholder="如：教学楼A屋顶光伏" />
        </el-form-item>
        <el-form-item label="类别">
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="c in ['光伏', '储能', '节能改造', '峰谷策略']" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="年覆盖电量">
          <el-input-number v-model="form.annual_electricity_kwh" :min="0" :step="10000" controls-position="right" style="width: 100%" />
          <span class="unit">kWh</span>
        </el-form-item>
        <el-form-item label="投资额">
          <el-input-number v-model="form.investment" :min="0" :step="10000" controls-position="right" style="width: 100%" />
          <span class="unit">元</span>
        </el-form-item>
        <el-form-item label="折算电价">
          <el-input-number v-model="form.electricity_price" :min="0" :step="0.05" :precision="3" controls-position="right" style="width: 100%" />
          <span class="unit">元/kWh</span>
        </el-form-item>
        <el-form-item label="减碳因子">
          <el-input-number v-model="form.factor" :min="0" :step="0.05" :precision="4" controls-position="right" style="width: 100%" placeholder="留空用电网因子" />
          <span class="unit">kgCO2e/kWh</span>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="2" maxlength="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="success" :loading="submitting" @click="onSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.mt {
  margin-top: 16px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.night-bar {
  width: 130px;
}

.muted {
  color: #c0c4cc;
  font-size: 12px;
}

.green {
  color: #2e7d32;
  font-weight: bold;
}

.unit {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}
</style>
