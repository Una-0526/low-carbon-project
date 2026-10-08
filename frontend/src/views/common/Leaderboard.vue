<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import echarts from '../../utils/echarts'
import { getLeaderboard } from '../../api'
import { useAuth } from '../../stores/auth'

const TOP_N = 10 // 主榜展示前 10 名，榜单外用"我的排名"窗口定位

const type = ref('personal')
const period = ref('month')
const loading = ref(false)
const board = ref({ items: [], me: null })

const TYPE_OPTIONS = [
  { value: 'personal', label: '个人榜' },
  { value: 'dorm', label: '宿舍榜' },
  { value: 'class', label: '班级榜' },
]
const PERIOD_OPTIONS = [
  { value: 'month', label: '本月' },
  { value: 'year', label: '本年' },
]

const isPersonal = computed(() => type.value === 'personal')
const periodLabel = computed(() => (period.value === 'month' ? '本月' : '本年'))
// 注意：useAuth() 返回普通对象，user 是原始 Ref，必须 .value 取值（模板外不会自动解包）
const { user } = useAuth()
const isStudent = computed(() => user.value?.role === 'student')

const topItems = computed(() => board.value.items.slice(0, TOP_N))

// 我的名次是否已在前 10，若不在则额外展示 me±2 的窗口
const meInTop = computed(() => {
  if (!board.value.me) return true
  return board.value.items.findIndex((it) => it.rank === board.value.me.rank) < TOP_N
})

const meWindow = computed(() => {
  if (!board.value.me || meInTop.value) return []
  const r = board.value.me.rank
  const len = board.value.items.length
  return board.value.items.slice(Math.max(0, r - 3), Math.min(len, r + 2))
})

async function fetchBoard() {
  loading.value = true
  try {
    const { data } = await getLeaderboard({ type: type.value, period: period.value })
    board.value = data
    await nextTick()
    renderBar() // 数据到位后必渲染一次，避免维度/周期切换时图表停留在旧数据
  } finally {
    loading.value = false
  }
}

watch([type, period], fetchBoard)
onMounted(fetchBoard)

function rowClass({ row }) {
  if (!board.value.me) return ''
  return row.rank === board.value.me.rank ? 'me-row' : ''
}

function medal(rank) {
  return ['🥇', '🥈', '🥉'][rank - 1] || rank
}

function changeText(row) {
  if (row.rank_change === null || row.rank_change === undefined) return '新'
  if (row.rank_change > 0) return `↑${row.rank_change}`
  if (row.rank_change < 0) return `↓${-row.rank_change}`
  return '—'
}

function changeClass(row) {
  if (row.rank_change > 0) return 'up'
  if (row.rank_change < 0) return 'down'
  return 'flat'
}

// ---------- Top10 积分对比柱状图 ----------
const chartRef = ref(null)
let chart = null

const barTitle = computed(
  () => `${TYPE_OPTIONS.find((t) => t.value === type.value).label}${periodLabel.value}积分对比 Top10`,
)

const barTip = computed(() => {
  if (isPersonal.value) return '绿色柱子 = 我的积分'
  return type.value === 'dorm' ? '绿色柱子 = 我所在的宿舍' : '绿色柱子 = 我所在的班级'
})

// 当前登录学生对应的柱子（个人榜=本人，宿舍/班级榜=所在组），教师无高亮
const myKey = computed(() => {
  if (!isStudent.value) return null
  return isPersonal.value ? user.value?.username : type.value === 'dorm' ? user.value?.dormitory : user.value?.class_name
})

// 图表数据：Top10；我（或我所在组）不在前 10 时追加到末尾，保证绿色高亮柱始终可见
const barItems = computed(() => {
  const items = topItems.value.slice()
  const me = board.value.me
  if (me && !items.some((it) => it.rank === me.rank)) items.push(me)
  return items
})

function renderBar() {
  if (!chart) return
  chart.resize() // 容器常驻渲染，先同步一次实际尺寸，避免按旧尺寸绘制
  const items = barItems.value
  if (!items.length) {
    chart.clear()
    return
  }
  const toName = (it) => (isPersonal.value ? it.username : it.key)
  chart.setOption(
    {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (ps) => `${ps[0].name}<br/>${periodLabel.value}积分：<b>${ps[0].value}</b>`,
      },
      grid: { left: 8, right: 16, top: 30, bottom: 0, containLabel: true },
      xAxis: {
        type: 'category',
        data: items.map(toName),
        axisLabel: {
          interval: 0,
          rotate: 24,
          fontSize: 11,
          formatter: (n) => (n === myKey.value ? `${n}(我)` : n),
        },
      },
      yAxis: { type: 'value', name: '积分' },
      series: [
        {
          type: 'bar',
          barMaxWidth: 40,
          itemStyle: { borderRadius: [4, 4, 0, 0] },
          data: items.map((it) => ({
            value: it.points,
            itemStyle: { color: toName(it) === myKey.value ? '#4caf50' : '#409eff' },
          })),
          label: { show: true, position: 'top', fontSize: 11, color: '#606266' },
        },
      ],
    },
    true, // notMerge：切换维度时类目数量不同（12人/4组），必须全量替换
  )
}

function onResize() {
  chart?.resize()
}

onMounted(async () => {
  await nextTick()
  chart = echarts.init(chartRef.value)
  window.addEventListener('resize', onResize)
  renderBar()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div v-loading="loading">
    <!-- 维度 / 周期切换 -->
    <el-card shadow="never">
      <div class="toolbar">
        <el-radio-group v-model="type">
          <el-radio-button v-for="t in TYPE_OPTIONS" :key="t.value" :value="t.value">
            {{ t.label }}
          </el-radio-button>
        </el-radio-group>
        <el-radio-group v-model="period">
          <el-radio-button v-for="p in PERIOD_OPTIONS" :key="p.value" :value="p.value">
            {{ p.label }}
          </el-radio-button>
        </el-radio-group>
      </div>
    </el-card>

    <!-- Top10 积分对比柱状图 -->
    <el-card class="mt">
      <template #header>
        <div class="chart-head">
          <span>{{ barTitle }}</span>
          <span class="chart-tip">{{ barTip }}</span>
        </div>
      </template>
      <!-- 图表容器始终保持渲染（避免 0 尺寸 init），空数据时用浮层提示 -->
      <div class="chart-wrap">
        <div ref="chartRef" class="chart" />
        <div v-if="!barItems.length" class="chart-empty">
          <el-empty description="本期暂无积分数据" :image-size="80" />
        </div>
      </div>
    </el-card>

    <!-- 主榜 -->
    <el-card class="mt" :header="`${TYPE_OPTIONS.find((t) => t.value === type).label}（${periodLabel}获得积分）`">
      <el-alert
        v-if="isStudent && !board.me"
        type="info"
        :closable="false"
        show-icon
        :title="`你${periodLabel}暂无获得积分记录，去绿色打卡攒积分上榜吧！`"
        class="no-me-tip"
      />
      <el-table :data="topItems" stripe :row-class-name="rowClass">
        <el-table-column label="名次" width="80" align="center">
          <template #default="{ row }">
            <span class="medal">{{ medal(row.rank) }}</span>
          </template>
        </el-table-column>
        <template v-if="isPersonal">
          <el-table-column prop="username" label="姓名" min-width="110" />
          <el-table-column prop="class_name" label="班级" min-width="130" />
          <el-table-column prop="dormitory" label="宿舍" min-width="120" />
        </template>
        <el-table-column v-else :prop="'key'" :label="type === 'dorm' ? '宿舍' : '班级'" min-width="150" />
        <el-table-column v-if="!isPersonal" prop="member_count" label="成员" width="90" align="center" />
        <el-table-column :label="`${periodLabel}积分`" width="120" align="right">
          <template #default="{ row }">
            <span class="points">{{ row.points }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="isPersonal" label="较上期" width="90" align="center">
          <template #default="{ row }">
            <span :class="changeClass(row)">{{ changeText(row) }}</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 我的名次窗口（未进前 10 时展示前后各 2 名） -->
      <el-card v-if="board.me && !meInTop" shadow="never" class="me-card">
        <template #header>
          <span class="me-title">我的排名 — 第 {{ board.me.rank }} 名</span>
        </template>
        <el-table :data="meWindow" :row-class-name="rowClass" size="small">
          <el-table-column label="名次" width="70" align="center">
            <template #default="{ row }">{{ row.rank }}</template>
          </el-table-column>
          <template v-if="isPersonal">
            <el-table-column prop="username" label="姓名" min-width="100" />
            <el-table-column prop="class_name" label="班级" min-width="120" />
          </template>
          <el-table-column v-else :prop="'key'" :label="type === 'dorm' ? '宿舍' : '班级'" min-width="130" />
          <el-table-column :label="`${periodLabel}积分`" width="100" align="right">
            <template #default="{ row }">{{ row.points }}</template>
          </el-table-column>
          <el-table-column v-if="isPersonal" label="较上期" width="80" align="center">
            <template #default="{ row }">
              <span :class="changeClass(row)">{{ changeText(row) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-card>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.mt {
  margin-top: 16px;
}

.chart-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

.chart-tip {
  font-size: 12px;
  color: #909399;
  font-weight: normal;
}

.chart-wrap {
  position: relative;
}

.chart {
  width: 100%;
  height: 360px;
}

.chart-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
}

.no-me-tip {
  margin-bottom: 12px;
}

.medal {
  font-size: 16px;
}

.points {
  color: #2e7d32;
  font-weight: bold;
}

.up {
  color: #67c23a;
  font-weight: bold;
}

.down {
  color: #f56c6c;
  font-weight: bold;
}

.flat {
  color: #909399;
}

.me-card {
  margin-top: 16px;
}

.me-title {
  color: #2e7d32;
  font-weight: bold;
}

/* 高亮"我的排名"行 */
:deep(.me-row) {
  --el-table-tr-bg-color: #e8f5e9;
  background: #e8f5e9;
}
</style>
