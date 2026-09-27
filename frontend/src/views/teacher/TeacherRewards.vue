<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createRewardItem,
  fulfillRedemption,
  getAdminRedemptions,
  getAdminRewardItems,
  updateRewardItem,
} from '../../api'
import { CATEGORY_OPTIONS, REDEEM_STATUS_MAP } from '../../constants/mall'

const loading = ref(false)
const submitting = ref(false)
const items = ref([])
const records = ref([])
const filterStatus = ref('')
const editingId = ref(null)

const formRef = ref()
const form = reactive({
  name: '',
  category: '食堂',
  points_cost: 50,
  stock: 10,
  is_active: true,
  description: '',
})

const rules = {
  name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
}

async function loadItems() {
  const { data } = await getAdminRewardItems()
  items.value = data
}

async function loadRecords() {
  const { data } = await getAdminRedemptions(
    filterStatus.value ? { status: filterStatus.value } : {},
  )
  records.value = data
}

async function fetchAll() {
  loading.value = true
  try {
    await Promise.all([loadItems(), loadRecords()])
  } finally {
    loading.value = false
  }
}

function resetForm() {
  editingId.value = null
  form.name = ''
  form.category = '食堂'
  form.points_cost = 50
  form.stock = 10
  form.is_active = true
  form.description = ''
  formRef.value?.clearValidate()
}

function startEdit(row) {
  editingId.value = row.id
  form.name = row.name
  form.category = row.category
  form.points_cost = row.points_cost
  form.stock = row.stock
  form.is_active = row.is_active
  form.description = row.description || ''
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function submit() {
  await formRef.value.validate()
  const payload = {
    name: form.name.trim(),
    category: form.category,
    points_cost: form.points_cost,
    stock: form.stock,
    is_active: form.is_active,
    description: form.description.trim() || null,
  }
  if (editingId.value) {
    await updateRewardItem(editingId.value, payload)
    ElMessage.success('商品已更新')
  } else {
    await createRewardItem(payload)
    ElMessage.success('商品已上架')
  }
  resetForm()
  await loadItems()
}

async function toggleActive(row) {
  const action = row.is_active ? '下架' : '上架'
  await ElMessageBox.confirm(`确认${action}「${row.name}」？`, `${action}确认`, { type: 'warning' })
  await updateRewardItem(row.id, {
    name: row.name,
    category: row.category,
    points_cost: row.points_cost,
    stock: row.stock,
    is_active: !row.is_active,
    description: row.description,
  })
  ElMessage.success(`已${action}`)
  await loadItems()
}

async function fulfill(row) {
  await ElMessageBox.confirm(
    `确认「${row.username}」已领取「${row.item_name}」？`,
    '发放确认',
    { type: 'warning' },
  )
  await fulfillRedemption(row.id)
  ElMessage.success('已标记领取')
  await loadRecords()
}

function fmtTime(t) {
  return new Date(t).toLocaleString('zh-CN')
}

onMounted(fetchAll)
</script>

<template>
  <div v-loading="loading">
    <!-- 新增 / 编辑表单 -->
    <el-card :header="editingId ? '编辑商品' : '新增商品'" class="form-card">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="商品名称" prop="name">
          <el-input v-model="form.name" maxlength="50" placeholder="如：食堂优惠券" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="form.category" class="w">
            <el-option v-for="c in CATEGORY_OPTIONS" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="所需积分">
          <el-input-number v-model="form.points_cost" :min="1" :step="10" :controls="false" class="w" />
        </el-form-item>
        <el-form-item label="库存">
          <el-input-number v-model="form.stock" :min="0" :step="5" :controls="false" class="w" />
        </el-form-item>
        <el-form-item label="上架状态">
          <el-switch v-model="form.is_active" active-text="上架" inactive-text="下架" />
        </el-form-item>
        <el-form-item label="商品说明">
          <el-input v-model="form.description" type="textarea" :rows="2" maxlength="200" placeholder="选填，如：面值 5 元，全校食堂通用" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="submit">{{ editingId ? '保存修改' : '新增商品' }}</el-button>
          <el-button v-if="editingId" @click="resetForm">取消编辑</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 商品列表 -->
    <el-card header="商品管理（上下架 / 调整积分 / 库存）" class="mt">
      <el-table :data="items" stripe>
        <el-table-column prop="name" label="商品" min-width="130" />
        <el-table-column prop="category" label="分类" width="90" />
        <el-table-column label="所需积分" width="100" align="right">
          <template #default="{ row }">
            <span class="points">{{ row.points_cost }}</span>
          </template>
        </el-table-column>
        <el-table-column label="库存" width="80" align="right">
          <template #default="{ row }">
            <span :class="{ soldout: row.stock <= 0 }">{{ row.stock }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '上架中' : '已下架' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" show-overflow-tooltip>
          <template #default="{ row }">{{ row.description || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="startEdit(row)">编辑</el-button>
            <el-button link :type="row.is_active ? 'danger' : 'success'" size="small" @click="toggleActive(row)">
              {{ row.is_active ? '下架' : '上架' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 兑换记录 -->
    <el-card class="mt">
      <template #header>
        <div class="card-header">
          <span>兑换记录（学生兑换后凭记录线下发放）</span>
          <el-select v-model="filterStatus" placeholder="全部状态" clearable class="filter" @change="loadRecords">
            <el-option label="待领取" value="pending" />
            <el-option label="已领取" value="fulfilled" />
          </el-select>
        </div>
      </template>
      <el-table :data="records" stripe>
        <el-table-column prop="username" label="学生" width="120" />
        <el-table-column prop="item_name" label="商品" min-width="130" />
        <el-table-column label="消耗积分" width="100" align="right">
          <template #default="{ row }">-{{ row.points_cost }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="REDEEM_STATUS_MAP[row.status]?.type || 'info'" size="small">
              {{ REDEEM_STATUS_MAP[row.status]?.label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="兑换时间" width="170">
          <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'pending'" link type="success" size="small" @click="fulfill(row)">
              标记已领取
            </el-button>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.form-card {
  max-width: 520px;
}

.w {
  width: 220px;
}

.mt {
  margin-top: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.filter {
  width: 120px;
}

.points {
  color: #2e7d32;
  font-weight: bold;
}

.soldout {
  color: #f56c6c;
}

.muted {
  color: #c0c4cc;
  font-size: 12px;
}
</style>
