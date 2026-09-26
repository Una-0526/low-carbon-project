<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createActivity, listActivities } from '../../api'
import { useAuth } from '../../stores/auth'

const { user } = useAuth()

const ACTIVITY_TYPES = ['步行', '骑行', '公交/地铁', '光盘行动', '随手关灯', '双面打印']

const form = reactive({
  activity_type: '步行',
  carbon_saved_kg: 0.5,
  description: '',
})

const records = ref([])
const loading = ref(false)
const submitting = ref(false)

async function fetchRecords() {
  loading.value = true
  try {
    // 学生接口只返回本人记录，无需传筛选参数
    const { data } = await listActivities()
    records.value = data
  } finally {
    loading.value = false
  }
}

async function onSubmit() {
  submitting.value = true
  try {
    await createActivity({
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
      <el-card>
        <template #header>
          <div>
            我的低碳行为
            <el-tag type="success" size="small" class="ml">{{ user?.class_name }}</el-tag>
            <el-tag type="info" size="small" class="ml">{{ user?.dormitory }}</el-tag>
          </div>
        </template>
        <el-form label-width="90px">
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
        <el-table :data="records" v-loading="loading" stripe>
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

<style scoped>
.ml {
  margin-left: 8px;
}
</style>
