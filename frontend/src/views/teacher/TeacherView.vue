<script setup>
import { onMounted, ref } from 'vue'
import { listActivities, getStats } from '../../api'

const stats = ref({
  total_records: 0,
  total_carbon_saved_kg: 0,
  carbon_saved_by_role: {},
  carbon_saved_by_type: {},
})

const records = ref([])
const loading = ref(false)

async function fetchData() {
  loading.value = true
  try {
    const [statsRes, recordsRes] = await Promise.all([getStats(), listActivities({})])
    stats.value = statsRes.data
    records.value = recordsRes.data
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<template>
  <div v-loading="loading">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="hover">
          <el-statistic title="累计记录数" :value="stats.total_records" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <el-statistic title="累计减碳量 (kg)" :value="stats.total_carbon_saved_kg" :precision="2" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <el-statistic title="参与人数（按姓名去重）" :value="new Set(records.map((r) => r.username)).size" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="mt">
      <el-col :span="12">
        <el-card header="学生 / 教师减碳量 (kg)">
          <el-table :data="Object.entries(stats.carbon_saved_by_role).map(([role, v]) => ({ role, total: v }))" stripe>
            <el-table-column prop="role" label="角色">
              <template #default="{ row }">
                <el-tag :type="row.role === 'student' ? 'success' : 'warning'">
                  {{ row.role === 'student' ? '学生' : '教师' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="total" label="减碳量(kg)" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card header="各行为类型减碳量 (kg)">
          <el-table :data="Object.entries(stats.carbon_saved_by_type).map(([type, v]) => ({ type, total: v }))" stripe>
            <el-table-column prop="type" label="行为类型" />
            <el-table-column prop="total" label="减碳量(kg)" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-card header="全部低碳记录" class="mt">
      <el-table :data="records" stripe>
        <el-table-column prop="username" label="姓名" width="120" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 'student' ? 'success' : 'warning'">
              {{ row.role === 'student' ? '学生' : '教师' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="activity_type" label="行为类型" width="140" />
        <el-table-column prop="carbon_saved_kg" label="减碳量(kg)" width="120" />
        <el-table-column prop="description" label="备注" show-overflow-tooltip />
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString('zh-CN') }}
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无数据" />
        </template>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.mt {
  margin-top: 20px;
}
</style>
