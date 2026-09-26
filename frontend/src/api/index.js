import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

/** 提交低碳行为记录 */
export function createActivity(data) {
  return api.post('/activities', data)
}

/** 查询低碳行为记录 */
export function listActivities(params) {
  return api.get('/activities', { params })
}

/** 碳排放统计 */
export function getStats() {
  return api.get('/activities/stats')
}

/** 删除低碳行为记录 */
export function deleteActivity(id) {
  return api.delete(`/activities/${id}`)
}
