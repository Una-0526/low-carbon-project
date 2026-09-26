<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createActivity, listActivities } from '../../api'

const ACTIVITY_TYPES = ['步行', '骑行', '公交/地铁', '光盘行动', '随手关灯', '双面打印']

const form = reactive({
  username: '',
  activity_type: '步行',
  carbon_saved_kg: 0.5,
  description: '',
})

const records = ref([])
const loading = ref(false)
const submitting = ref(false)

const recordsRef = ref()

async function fetchRecords() {
  loading.value = true
  try {
    const { data } = await listActivities({ role: 'student' })
    records.value = data
  } finally {
    loading.value = false
  }
}

async function onSubmit() {
  if (!form.username.trim()) {
    ElMessage.warning('请填写姓名')
    return
  }
  submitting.value = true
  try {
    await createActivity({
      username: form.username.trim(),
      role: 'student',
      activity_type: form.activity_type,
      carbon_saved_kg: Number(form.carbon_saved_kg),
      description: form.description.trim() || null,
    })
    ElMessage.success('记录提交成功，为低碳出一份力！')
    form.description = ''
    await fetchRecords()
  } finally {
    submitting.value = false
  }
}

onMounted(fetchRecords)
</script>

<template>
  <el-row :gutter="20">
    <el-col :span="8">
      <el-card header="记录我的低碳行为">
        <el-form label-width="90px">
          <el-form-item label="姓名" required>
            <el-input v-model="form.username" placeholder="请输入姓名" />
          </el-form-item>
          <el-form-item label="行为类型">
            <el-select v-model="form.activity_type">
              <el-option v-for="t in ACTIVITY_TYPES" :key="t" :label="t" :value="t" />
            </el-select>
          </el-form-item>
          <el-form-item label="减碳(kg)">
            <el-input-number v-model="form.carbon_saved_kg" :min="0" :step="0.1" />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="form.description" type="textarea" placeholder="选填" />
          </el-form-item>
          <el-form-item>
            <el-button type="success" :loading="submitting" @click="onSubmit">提交记录</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </el-col>

    <el-col :span="16">
      <el-card header="我的低碳记录">
        <el-table ref="recordsRef" :data="records" v-loading="loading" stripe>
          <el-table-column prop="username" label="姓名" width="120" />
          <el-table-column prop="activity_type" label="行为类型" width="140" />
          <el-table-column prop="carbon_saved_kg" label="减碳量(kg)" width="120" />
          <el-table-column prop="description" label="备注" show-overflow-tooltip />
          <el-table-column prop="created_at" label="时间" width="180">
            <template #default="{ row }">
              {{ new Date(row.created_at).toLocaleString('zh-CN') }}
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="还没有记录，快去提交第一条低碳行为吧" />
          </template>
        </el-table>
      </el-card>
    </el-col>
  </el-row>
</template>
