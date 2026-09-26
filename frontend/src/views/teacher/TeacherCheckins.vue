<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { approveCheckin, getAllCheckins, rejectCheckin } from '../../api'
import { DISPLAY, STATUS_MAP } from '../../constants/checkin'

const FILTERS = [
  { value: 'pending', label: '待审核' },
  { value: 'approved', label: '已通过' },
  { value: 'rejected', label: '已驳回' },
  { value: 'flagged', label: 'AI 已标记' },
  { value: 'all', label: '全部' },
]

const loading = ref(false)
const records = ref([])
const filter = ref('pending')

async function fetchRecords() {
  loading.value = true
  try {
    const params = {}
    if (filter.value === 'flagged') params.ai_flagged = true
    else if (filter.value !== 'all') params.status = filter.value
    const { data } = await getAllCheckins(params)
    records.value = data
  } finally {
    loading.value = false
  }
}

async function onApprove(row) {
  try {
    await ElMessageBox.confirm(
      `确认通过 ${row.username} 的「${DISPLAY[row.task_type]?.label || row.task_type}」打卡？通过后积分正式入账。`,
      '审核通过',
      { confirmButtonText: '通过', cancelButtonText: '取消', type: 'success' }
    )
  } catch {
    return
  }
  const { data } = await approveCheckin(row.id)
  const bonusText = data.bonus ? `，另发连续 ${data.streak} 天奖励 +${data.bonus} 分` : ''
  ElMessage.success(`已通过：入账 ${data.checkin.points_awarded} 分${bonusText}`)
  await fetchRecords()
}

async function onReject(row) {
  let reason
  try {
    const res = await ElMessageBox.prompt('驳回后不发放积分，请输入原因（学生可见，可留空）', `驳回 ${row.username} 的打卡`, {
      confirmButtonText: '驳回',
      cancelButtonText: '取消',
      inputPlaceholder: '如：照片模糊 / 打卡间隔过近',
      inputValidator: (v) => !v || v.length <= 200 || '不能超过 200 字',
    })
    reason = res.value?.trim()
  } catch {
    return
  }
  await rejectCheckin(row.id, reason)
  ElMessage.success('已驳回')
  await fetchRecords()
}

function fmtTime(t) {
  return new Date(t).toLocaleString('zh-CN')
}

onMounted(fetchRecords)
</script>

<template>
  <el-card>
    <template #header>
      <div class="toolbar">
        <span>学生打卡审核</span>
        <el-radio-group v-model="filter" @change="fetchRecords">
          <el-radio-button v-for="f in FILTERS" :key="f.value" :value="f.value">
            {{ f.label }}
          </el-radio-button>
        </el-radio-group>
      </div>
    </template>

    <el-table :data="records" v-loading="loading" stripe>
      <el-table-column prop="username" label="学生" width="90" fixed />
      <el-table-column label="任务" width="110">
        <template #default="{ row }">{{ DISPLAY[row.task_type]?.label || row.task_type }}</template>
      </el-table-column>
      <el-table-column label="照片" width="90">
        <template #default="{ row }">
          <el-image
            v-if="row.photo_path"
            :src="row.photo_path"
            :preview-src-list="[row.photo_path]"
            preview-teleported
            fit="cover"
            class="thumb"
          />
          <span v-else class="muted">无</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="STATUS_MAP[row.status].type" size="small">{{ STATUS_MAP[row.status].label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="AI 防作弊" min-width="180">
        <template #default="{ row }">
          <el-tooltip v-if="row.ai_flagged" :content="row.ai_flags.join('；')" placement="top">
            <el-tag type="danger" size="small">已标记</el-tag>
          </el-tooltip>
          <span v-else class="muted">正常</span>
        </template>
      </el-table-column>
      <el-table-column prop="note" label="备注" show-overflow-tooltip>
        <template #default="{ row }">{{ row.note || '-' }}</template>
      </el-table-column>
      <el-table-column label="积分" width="80">
        <template #default="{ row }">
          <span v-if="row.points_awarded" class="points">+{{ row.points_awarded }}</span>
          <span v-else class="muted">-</span>
        </template>
      </el-table-column>
      <el-table-column label="打卡时间" width="170">
        <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-button type="success" size="small" @click="onApprove(row)">通过</el-button>
            <el-button type="danger" size="small" plain @click="onReject(row)">驳回</el-button>
          </template>
          <span v-else-if="row.status === 'rejected' && row.review_reason" class="reject">
            {{ row.review_reason }}
          </span>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无符合条件的打卡记录" />
      </template>
    </el-table>
  </el-card>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.thumb {
  width: 56px;
  height: 56px;
  border-radius: 6px;
  display: block;
}

.muted {
  color: #c0c4cc;
  font-size: 12px;
}

.points {
  color: #2e7d32;
  font-weight: bold;
}

.reject {
  color: #f56c6c;
  font-size: 12px;
}
</style>
