<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  createCheckin,
  getCheckinTasks,
  getMyCheckinSummary,
  getMyCheckins,
} from '../../api'
import { DISPLAY, STATUS_MAP } from '../../constants/checkin'

const summary = ref({ total_points: 0, streak_days: 0 })
const tasks = ref([])
const records = ref([])
const loading = ref(false)

// 打卡弹窗
const dialogVisible = ref(false)
const current = ref(null)
const submitting = ref(false)
const locating = ref(false)
const fileList = ref([])
const form = reactive({ note: '', latitude: null, longitude: null })

async function fetchAll() {
  loading.value = true
  try {
    const [s, t, r] = await Promise.all([getMyCheckinSummary(), getCheckinTasks(), getMyCheckins()])
    summary.value = s.data
    tasks.value = t.data
    records.value = r.data
  } finally {
    loading.value = false
  }
}

function openCheckin(task) {
  current.value = task
  form.note = ''
  form.latitude = null
  form.longitude = null
  fileList.value = []
  dialogVisible.value = true
  locate()
}

function locate() {
  if (!navigator.geolocation) {
    ElMessage.warning('当前浏览器不支持定位，可不带位置直接提交')
    return
  }
  locating.value = true
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      form.latitude = Number(pos.coords.latitude.toFixed(6))
      form.longitude = Number(pos.coords.longitude.toFixed(6))
      locating.value = false
      ElMessage.success('定位成功')
    },
    (err) => {
      locating.value = false
      ElMessage.warning(`定位失败（${err.message}），可继续提交，仅缺少位置信息`)
    },
    { enableHighAccuracy: true, timeout: 8000 }
  )
}

async function onSubmit() {
  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('task_type', current.value.task_type)
    if (form.note.trim()) fd.append('note', form.note.trim())
    if (form.latitude != null && form.longitude != null) {
      fd.append('latitude', form.latitude)
      fd.append('longitude', form.longitude)
    }
    if (fileList.value.length) fd.append('photo', fileList.value[0].raw)

    const { data } = await createCheckin(fd)
    if (data.ai_flagged) {
      ElMessage.warning(`打卡已提交，但被 AI 标记待人工审核：${data.ai_flags.join('；')}`)
    } else {
      ElMessage.success('打卡提交成功，等待教师审核')
    }
    dialogVisible.value = false
    await fetchAll()
  } finally {
    submitting.value = false
  }
}

function fmtTime(t) {
  return new Date(t).toLocaleString('zh-CN')
}

onMounted(fetchAll)
</script>

<template>
  <div v-loading="loading">
    <!-- 顶部：积分 / 连续天数 -->
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="hover">
          <el-statistic title="当前碳积分" :value="summary.total_points">
            <template #suffix>分</template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <el-statistic title="连续打卡" :value="summary.streak_days">
            <template #suffix>天</template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>

    <!-- 任务卡片 -->
    <el-card header="今日绿色打卡（点击任务开始）" class="mt">
      <div class="task-row">
        <div v-for="t in tasks" :key="t.task_type" class="task-card" @click="openCheckin(t)">
          <div class="task-icon">{{ DISPLAY[t.task_type]?.icon || '✅' }}</div>
          <div class="task-name">{{ DISPLAY[t.task_type]?.label || t.task_type }}</div>
          <el-tag type="success" effect="plain" size="small">+{{ t.points }} 分</el-tag>
        </div>
      </div>
    </el-card>

    <!-- 我的打卡记录 -->
    <el-card header="我的打卡记录" class="mt">
      <el-table :data="records" v-loading="loading" stripe>
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
            <span v-else class="no-photo">无</span>
          </template>
        </el-table-column>
        <el-table-column label="任务" width="110">
          <template #default="{ row }">{{ DISPLAY[row.task_type]?.label || row.task_type }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="STATUS_MAP[row.status].type" size="small">{{ STATUS_MAP[row.status].label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="AI 防作弊" width="110">
          <template #default="{ row }">
            <el-tooltip v-if="row.ai_flagged" :content="row.ai_flags.join('；')" placement="top">
              <el-tag type="danger" size="small" effect="plain">已标记</el-tag>
            </el-tooltip>
            <span v-else class="muted">正常</span>
          </template>
        </el-table-column>
        <el-table-column label="积分" width="80">
          <template #default="{ row }">
            <span v-if="row.points_awarded" class="points">+{{ row.points_awarded }}</span>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="note" label="备注" show-overflow-tooltip>
          <template #default="{ row }">{{ row.note || '-' }}</template>
        </el-table-column>
        <el-table-column label="驳回原因" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.review_reason" class="reject">{{ row.review_reason }}</span>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="打卡时间" width="170">
          <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 打卡弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="`打卡：${current ? DISPLAY[current.task_type]?.label || current.task_type : ''}（+${current?.points ?? 0} 分）`"
      width="480px"
    >
      <el-form label-width="90px">
        <el-form-item label="拍照上传">
          <el-upload
            v-model:file-list="fileList"
            :auto-upload="false"
            :limit="1"
            accept="image/jpeg,image/png,image/webp"
            list-type="picture-card"
          >
            <el-icon><Plus /></el-icon>
            <template #tip>
              <div class="upload-tip">jpg/png/webp，不超过 5MB，选填</div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="位置确认">
          <div class="loc">
            <template v-if="form.latitude != null">
              <el-tag type="success" effect="plain">已定位</el-tag>
              <span class="loc-text">纬度 {{ form.latitude }}，经度 {{ form.longitude }}</span>
            </template>
            <template v-else>
              <el-tag type="info" effect="plain">未定位</el-tag>
              <span class="loc-text">仅用于防作弊校验（距宿舍 2km 内为正常）</span>
            </template>
            <el-button size="small" :loading="locating" @click="locate">重新定位</el-button>
          </div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" type="textarea" :rows="2" maxlength="200" placeholder="选填，如：在二食堂光盘" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="success" :loading="submitting" @click="onSubmit">提交打卡</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.mt {
  margin-top: 16px;
}

.task-row {
  display: flex;
  gap: 14px;
}

.task-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 18px 0;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.task-card:hover {
  border-color: #2e7d32;
  box-shadow: 0 4px 12px rgba(46, 125, 50, 0.15);
  transform: translateY(-2px);
}

.task-icon {
  font-size: 32px;
}

.task-name {
  font-weight: bold;
}

.thumb {
  width: 56px;
  height: 56px;
  border-radius: 6px;
  display: block;
}

.no-photo,
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

.upload-tip {
  font-size: 12px;
  color: #909399;
}

.loc {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.loc-text {
  font-size: 12px;
  color: #909399;
}
</style>
