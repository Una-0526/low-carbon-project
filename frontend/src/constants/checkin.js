/** 打卡任务展示名与图标（task_type 为后端约定值） */
export const DISPLAY = {
  骑行: { label: '骑行上学', icon: '🚲' },
  光盘: { label: '光盘行动', icon: '🍚' },
  自带水杯: { label: '自带水杯', icon: '🥤' },
  爬楼: { label: '爬楼', icon: '🏃' },
  随手关灯: { label: '随手关灯', icon: '💡' },
}

/** 打卡状态 -> 标签文案 / 颜色 */
export const STATUS_MAP = {
  pending: { label: '待审核', type: 'warning' },
  approved: { label: '已通过', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
}
