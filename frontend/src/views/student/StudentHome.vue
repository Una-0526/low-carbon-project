<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createActivity, getWeekCard, getWeekHistory, listActivities } from '../../api'
import { useAuth } from '../../stores/auth'

const { user } = useAuth()

// ---------- 碳周报 ----------
const week = ref(null)
const history = ref([])
const showHistory = ref(false)
const historyLoading = ref(false)

async function fetchWeek() {
  const { data } = await getWeekCard()
  week.value = data
}

async function openHistory() {
  showHistory.value = true
  historyLoading.value = true
  try {
    const { data } = await getWeekHistory()
    history.value = data
  } finally {
    historyLoading.value = false
  }
}

function fmtSigned(n, unit = '') {
  const v = Number(n) || 0
  return `${v > 0 ? '+' : ''}${v}${unit}`
}

function carbonChangeClass(n) {
  return n > 0 ? 'up' : n < 0 ? 'down' : 'flat'
}

function rankText(rank) {
  return rank ? `第 ${rank} 名` : '未上榜'
}

function rankChangeText(row) {
  if (row.rank_change === null || row.rank_change === undefined) return '-'
  if (row.rank_change > 0) return `↑${row.rank_change}`
  if (row.rank_change < 0) return `↓${-row.rank_change}`
  return '—'
}

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

onMounted(() => {
  fetchRecords()
  fetchWeek()
})
</script>

<template>
  <!-- 我的碳周报 -->
  <el-card v-loading="!week" class="week-card">
    <template #header>
      <div class="week-head">
        <span>我的碳周报 <el-tag size="small" type="success">{{ week?.week_start }} 当周</el-tag></span>
        <el-button link type="primary" @click="openHistory">历史周报</el-button>
      </div>
    </template>
    <div class="week-stats">
      <div class="stat">
        <div class="stat-label">本周减碳量</div>
        <div class="stat-value">{{ week?.carbon_kg ?? 0 }} <small>kg</small></div>
        <div :class="['stat-sub', carbonChangeClass(week?.carbon_change)]">
          较上周 {{ fmtSigned(week?.carbon_change, ' kg') }}
        </div>
      </div>
      <div class="stat">
        <div class="stat-label">本周获得积分</div>
        <div class="stat-value">{{ week?.points ?? 0 }}</div>
        <div class="stat-sub flat">打卡攒积分</div>
      </div>
      <div class="stat">
        <div class="stat-label">本周打卡次数</div>
        <div class="stat-value">{{ week?.checkin_count ?? 0 }} <small>次</small></div>
        <div class="stat-sub flat">绿色行为留痕</div>
      </div>
      <div class="stat">
        <div class="stat-label">本周全校排名</div>
        <div class="stat-value">{{ rankText(week?.rank) }}</div>
        <div :class="['stat-sub', week?.rank_change > 0 ? 'up' : week?.rank_change < 0 ? 'down' : 'flat']">
          <template v-if="week?.rank_change > 0">较上周 ↑{{ week.rank_change }} 名</template>
          <template v-else-if="week?.rank_change < 0">较上周 ↓{{ -week.rank_change }} 名</template>
          <template v-else>较上周持平 / 首次上榜</template>
        </div>
      </div>
    </div>
    <el-divider class="divider" />
    <div class="summary">💡 {{ week?.summary }}</div>
  </el-card>

  <!-- 历史周报弹窗 -->
  <el-dialog v-model="showHistory" title="历史周报" width="760px">
    <el-table :data="history" v-loading="historyLoading" stripe>
      <el-table-column prop="week_start" label="周开始" width="110" />
      <el-table-column label="减碳(kg)" width="100" align="right">
        <template #default="{ row }">{{ row.carbon_kg }}</template>
      </el-table-column>
      <el-table-column prop="points" label="积分" width="80" align="right" />
      <el-table-column prop="checkin_count" label="打卡次数" width="90" align="center" />
      <el-table-column label="全校排名" width="90" align="center">
        <template #default="{ row }">{{ row.rank ? `第${row.rank}名` : '未上榜' }}</template>
      </el-table-column>
      <el-table-column label="较上周" width="80" align="center">
        <template #default="{ row }">
          <span :class="row.rank_change > 0 ? 'up' : row.rank_change < 0 ? 'down' : 'flat'">
            {{ rankChangeText(row) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="summary" label="周报总结" show-overflow-tooltip />
    </el-table>
  </el-dialog>

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

.week-card {
  margin-bottom: 20px;
}

.week-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.week-stats {
  display: flex;
  justify-content: space-around;
  text-align: center;
  flex-wrap: wrap;
  gap: 12px;
}

.stat-label {
  color: #909399;
  font-size: 13px;
}

.stat-value {
  font-size: 26px;
  font-weight: bold;
  color: #2e7d32;
  margin: 4px 0;
}

.stat-sub {
  font-size: 12px;
}

.up {
  color: #67c23a;
}

.down {
  color: #f56c6c;
}

.flat {
  color: #909399;
}

.divider {
  margin: 14px 0 10px;
}

.summary {
  color: #606266;
  font-size: 14px;
}
</style>
