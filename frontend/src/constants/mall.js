/** 兑换状态 -> 标签文案 / 颜色（学生端"我的兑换"与教师端兑换记录共用） */
export const REDEEM_STATUS_MAP = {
  pending: { label: '待领取', type: 'warning' },
  fulfilled: { label: '已领取', type: 'success' },
}

/** 商品分类展示图标（category 为后端约定值） */
export const CATEGORY_DISPLAY = {
  食堂: { icon: '🍚' },
  超市: { icon: '🛒' },
  文具: { icon: '✏️' },
}

/** 商品分类下拉选项（教师端管理用） */
export const CATEGORY_OPTIONS = ['食堂', '超市', '文具']
