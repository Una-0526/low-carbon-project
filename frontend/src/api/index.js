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

/** 碳排放统计：group_by = building | month | semester（教师） */
export function getCarbonStats(params) {
  return api.get('/carbon/stats', { params })
}

/** 排放因子表 */
export function getCarbonFactors() {
  return api.get('/carbon/factors')
}
