<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { getCarbonRecords } from '../../api'
import echarts from '../../utils/echarts'

const KG_TO_T = 1000 // kgCO2e -> tCO2e

const loading = ref(false)
const records = ref([])

// 顶部汇总（吨 CO2e）
const summary = ref({ total: 0, scope1: 0, scope2: 0, reduction: 0, net: 0 })
// Scope 分项统计表（按建筑）
const scopeTable = ref([])

const barRef = ref(null)
const pieRef = ref(null)
const lineRef = ref(null)
let charts = []
let monthKeys = []

const BUILDING_ORDER = ['教学楼A', '教学楼B', '宿舍楼', '图书馆', '食堂', '公务车']
const CHART_COLORS = ['#2e7d32', '#66bb6a', '#ffca28', '#ef6c00', '#42a5f5', '#8d6e63']

function monthKey(r) {
  return `${r.year}-${String(r.month).padStart(2, '0')}`
}

function aggregate() {
  monthKeys = [...new Set(records.value.map(monthKey))].sort()
  const buildings = BUILDING_ORDER.filter((b) => records.value.some((r) => r.building === b))

  // 按建筑聚合 Scope1 / Scope2 / 减碳
  const byBuilding = {}
  for (const r of records.value) {
    const b = (byBuilding[r.building] ??= {
      building: r.building, scope1: 0, scope2: 0, total: 0, reduction: 0, net: 0,
    })
    b.scope1 += r.emissions.scope1
    b.scope2 += r.emissions.scope2
    b.total += r.emissions.total_emission
    b.reduction += r.emissions.total_reduction
    b.net += r.emissions.net_emission
  }
  scopeTable.value = Object.values(byBuilding).map((b) => ({
    ...b,
    scope1Rate: b.total ? (b.scope1 / b.total) * 100 : 0,
  }))

  const sum = (fn) => records.value.reduce((acc, r) => acc + fn(r.emissions), 0)
  summary.value = {
    total: sum((e) => e.total_emission),
    scope1: sum((e) => e.scope1),
    scope2: sum((e) => e.scope2),
    reduction: sum((e) => e.total_reduction),
    net: sum((e) => e.net_emission),
  }

  return { buildings }
}

function seriesByMonth(field, buildings) {
  return buildings.map((b) => ({
    name: b,
    type: 'bar',
    stack: 'total',
    data: monthKeys.map((m) =>
      round2(records.value
        .filter((r) => r.building === b && monthKey(r) === m)
        .reduce((acc, r) => acc + r.emissions[field], 0))
    ),
  }))
}

function round2(n) {
  return Math.round(n * 100) / 100
}

function renderBar(instance, buildings) {
  instance.setOption({
    color: CHART_COLORS,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v) => `${v} kgCO2e` },
    legend: { top: 0 },
    grid: { left: 70, right: 20, top: 40, bottom: 50 },
    xAxis: { type: 'category', data: monthKeys, name: '月份' },
    yAxis: { type: 'value', name: 'kgCO2e' },
    dataZoom: [{ type: 'inside' }],
    series: seriesByMonth('total_emission', buildings),
  })
}

function renderPie(instance) {
  instance.setOption({
    color: ['#ef6c00', '#2e7d32'],
    tooltip: { trigger: 'item', formatter: '{b}: {c} kgCO2e（{d}%）' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      center: ['50%', '45%'],
      label: { formatter: '{b}\n{d}%' },
      data: [
        { name: 'Scope1 燃气/燃油', value: round2(summary.value.scope1) },
        { name: 'Scope2 外购电力', value: round2(summary.value.scope2) },
      ],
    }],
  })
}

function renderLine(instance) {
  const mk = (field, name, color, area) => ({
    name,
    type: 'line',
    smooth: true,
    symbolSize: 6,
    itemStyle: { color },
    areaStyle: area ? { opacity: 0.12 } : undefined,
    data: monthKeys.map((m) => round2(records.value
      .filter((r) => monthKey(r) === m)
      .reduce((acc, r) => acc + r.emissions[field], 0))),
  })
  instance.setOption({
    tooltip: { trigger: 'axis', valueFormatter: (v) => `${v} kgCO2e` },
    legend: { top: 0 },
    grid: { left: 70, right: 20, top: 40, bottom: 50 },
    xAxis: { type: 'category', data: monthKeys, name: '月份', boundaryGap: false },
    yAxis: { type: 'value', name: 'kgCO2e' },
    series: [
      mk('total_emission', '总排放', '#d84315'),
      mk('scope2', 'Scope2 用电', '#2e7d32', true),
      mk('scope1', 'Scope1 燃气/燃油', '#ef6c00'),
      mk('total_reduction', '减碳量', '#42a5f5'),
    ],
  })
}

function disposeCharts() {
  charts.forEach((c) => c.dispose())
  charts = []
}

const onResize = () => charts.forEach((c) => c.resize())

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await getCarbonRecords()
    records.value = data
    const { buildings } = aggregate()
    disposeCharts()
    // 每个 DOM 只 init 一次，后续仅 setOption
    const instances = [barRef, pieRef, lineRef]
      .filter((r) => r.value)
      .map((r) => echarts.init(r.value))
    charts = instances
    if (instances[0]) renderBar(instances[0], buildings)
    if (instances[1]) renderPie(instances[1])
    if (instances[2]) renderLine(instances[2])
    window.addEventListener('resize', onResize)
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  disposeCharts()
})
</script>

<template>
  <div v-loading="loading">
    <!-- 汇总卡片 -->
    <el-row :gutter="16">
      <el-col :span="5">
        <el-card shadow="hover">
          <el-statistic title="总碳排放 (tCO2e)" :value="summary.total / KG_TO_T" :precision="1" />
        </el-card>
      </el-col>
      <el-col :span="5">
        <el-card shadow="hover">
          <el-statistic title="Scope1 燃气/燃油 (t)" :value="summary.scope1 / KG_TO_T" :precision="1" value-style="color:#ef6c00" />
        </el-card>
      </el-col>
      <el-col :span="5">
        <el-card shadow="hover">
          <el-statistic title="Scope2 外购电力 (t)" :value="summary.scope2 / KG_TO_T" :precision="1" value-style="color:#2e7d32" />
        </el-card>
      </el-col>
      <el-col :span="5">
        <el-card shadow="hover">
          <el-statistic title="减碳量 (t)" :value="summary.reduction / KG_TO_T" :precision="1" value-style="color:#42a5f5" />
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <el-statistic title="净排放 (t)" :value="summary.net / KG_TO_T" :precision="1" value-style="color:#d84315" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 各建筑按月碳排放：堆叠柱状图 -->
    <el-card header="各建筑按月碳排放（堆叠）" class="mt">
      <div ref="barRef" class="chart-lg" />
    </el-card>

    <el-row :gutter="16" class="mt">
      <!-- Scope 分项统计 -->
      <el-col :span="14">
        <el-card header="Scope1 / Scope2 分项统计（近 12 个月）">
          <el-table :data="scopeTable" stripe size="small">
            <el-table-column prop="building" label="建筑/主体" width="110" fixed />
            <el-table-column label="Scope1 (kg)" width="120">
              <template #default="{ row }">{{ row.scope1.toLocaleString('zh-CN', { maximumFractionDigits: 1 }) }}</template>
            </el-table-column>
            <el-table-column label="Scope2 (kg)" width="130">
              <template #default="{ row }">{{ row.scope2.toLocaleString('zh-CN', { maximumFractionDigits: 1 }) }}</template>
            </el-table-column>
            <el-table-column label="总排放 (kg)" width="130">
              <template #default="{ row }">{{ row.total.toLocaleString('zh-CN', { maximumFractionDigits: 1 }) }}</template>
            </el-table-column>
            <el-table-column label="Scope1 占比" width="140">
              <template #default="{ row }">
                <el-progress :percentage="Number(row.scope1Rate.toFixed(1))" :stroke-width="10" color="#ef6c00" />
              </template>
            </el-table-column>
            <el-table-column label="减碳 (kg)" width="110">
              <template #default="{ row }">{{ row.reduction.toLocaleString('zh-CN', { maximumFractionDigits: 1 }) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <!-- Scope 占比饼图 -->
      <el-col :span="10">
        <el-card header="排放结构：Scope1 vs Scope2">
          <div ref="pieRef" class="chart-sm" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 月度趋势 -->
    <el-card header="月度碳排放趋势" class="mt">
      <div ref="lineRef" class="chart-lg" />
    </el-card>
  </div>
</template>

<style scoped>
.mt {
  margin-top: 16px;
}

.chart-lg {
  height: 360px;
}

.chart-sm {
  height: 320px;
}
</style>
