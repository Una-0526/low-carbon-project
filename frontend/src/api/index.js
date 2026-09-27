import axios from 'axios'
import { useAuth } from '../stores/auth'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// 请求拦截：自动携带 JWT
api.interceptors.request.use((config) => {
  const { token } = useAuth()
  if (token.value) {
    config.headers.Authorization = `Bearer ${token.value}`
  }
  return config
})

// 响应拦截：401 说明未登录 / token 失效，清空登录态回到登录页
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && location.pathname !== '/login') {
      useAuth().clearAuth()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

/** 登录 */
export function login(data) {
  return api.post('/auth/login', data)
}

/** 当前登录用户信息 */
export function getMe() {
  return api.get('/auth/me')
}

/** 提交低碳行为记录 */
export function createActivity(data) {
  return api.post('/activities', data)
}

/** 查询低碳行为记录 */
export function listActivities(params) {
  return api.get('/activities', { params })
}

/** 碳排放统计（教师） */
export function getStats() {
  return api.get('/activities/stats')
}

/** 删除低碳行为记录（教师） */
export function deleteActivity(id) {
  return api.delete(`/activities/${id}`)
}

/** 查询建筑能耗记录（含逐条碳核算结果，教师） */
export function getCarbonRecords(params) {
  return api.get('/carbon/records', { params })
}

/** 录入建筑能耗记录（后端按因子自动核算，教师） */
export function createCarbonRecord(data) {
  return api.post('/carbon/records', data)
}

/** 修改能耗记录并重算（教师） */
export function updateCarbonRecord(id, data) {
  return api.put(`/carbon/records/${id}`, data)
}

/** 删除能耗记录（教师） */
export function deleteCarbonRecord(id) {
  return api.delete(`/carbon/records/${id}`)
}

/** 碳排放统计：group_by = building | month | semester（教师） */
export function getCarbonStats(params) {
  return api.get('/carbon/stats', { params })
}

/** 排放因子表 */
export function getCarbonFactors() {
  return api.get('/carbon/factors')
}

/** 打卡任务类型与基础积分 */
export function getCheckinTasks() {
  return api.get('/checkins/tasks')
}

/** 提交打卡（FormData：task_type / latitude / longitude / note / photo） */
export function createCheckin(formData) {
  return api.post('/checkins', formData, { timeout: 30000 })
}

/** 我的打卡记录 */
export function getMyCheckins() {
  return api.get('/checkins/me')
}

/** 我的积分与连续打卡天数 */
export function getMyCheckinSummary() {
  return api.get('/checkins/me/summary')
}

/** 我的积分流水 */
export function getMyPoints() {
  return api.get('/points/me')
}

/** 全部打卡记录（教师）：status=pending|approved|rejected / ai_flagged / user_id */
export function getAllCheckins(params) {
  return api.get('/checkins', { params })
}

/** 审核通过打卡（教师）：积分入账 + 连续奖励 */
export function approveCheckin(id) {
  return api.post(`/checkins/${id}/approve`)
}

/** 审核驳回打卡（教师），reason 选填 */
export function rejectCheckin(id, reason) {
  return api.post(`/checkins/${id}/reject`, { reason: reason || null })
}

/** 建筑异常诊断（本月环比 + 夜间用电占比） */
export function getBuildingDiagnosis() {
  return api.get('/diagnosis/buildings')
}

/** 方案库列表（含年减碳量/年省电费/回收期测算） */
export function getSolutions() {
  return api.get('/diagnosis/solutions')
}

/** 新增方案 */
export function createSolution(data) {
  return api.post('/diagnosis/solutions', data)
}

/** 修改方案参数 */
export function updateSolution(id, data) {
  return api.put(`/diagnosis/solutions/${id}`, data)
}

/** 删除方案 */
export function deleteSolution(id) {
  return api.delete(`/diagnosis/solutions/${id}`)
}

/** 碳中和路径模拟（三情景逐年排放 + 达峰/中和年份） */
export function getCarbonPathway() {
  return api.get('/pathway/simulate')
}
