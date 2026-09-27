<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import echarts from '../../utils/echarts'
import { getCarbonPathway } from '../../api'

const COLORS = { baseline: '#f56c6c', efficiency: '#409eff', solar: '#67c23a' }
const TAG_TYPES = { 保守: 'info', 现实推荐: 'success', 理想激进: 'warning' }

const loading = ref(false)
const result = ref(null)
const chartEl = ref(null)
let chart = null

function renderChart() {
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)
  const years = result.value.scenarios[0].series.map((p) => p.year)
  chart.setOption({
    tooltip: {
      trigger: 'axis',
      valueFormatter: (v) => `${v} tCO2e`,
    },
    legend: { top: 4 },
    grid: { left: 64, right: 24, top: 40, bottom: 32 },
    xAxis: { type: 'category', data: years, name: '年份' },
    yAxis: { type: 'value', name: '排放量 (tCO2e)' },
    series: result.value.scenarios.map((s) => ({
      name: s.name,
      type: 'line',
      data: s.series.map((p) => p.emission_t),
      symbol: 'none',
      lineStyle: { width: 2.5, color: COLORS[s.key] },
      itemStyle: { color: COLORS[s.key] },
      markLine: {
        silent: true,
        symbol: 'none',
        lineStyle: { type: 'dashed', color: '#909399' },
        data: [
          { xAxis: String(result.value.target_peak_year), label: { formatter: `${result.value.target_peak_year} 碳达峰目标` } },
          { xAxis: String(result.value.target_neutral_year), label: { formatter: `${result.value.target_neutral_year} 碳中和目标` } },
        ],
      },
    })),
  })
}

function onResize() {
  chart?.resize()
}

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await getCarbonPathway()
    result.value = data
    renderChart()
    window.addEventListener('resize', onResize)
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div v-loading="loading">
    <!-- 三情景结论卡片 -->
    <el-row v-if="result" :gutter="16">
      <el-col v-for="s in result.scenarios" :key="s.key" :span="8">
        <el-card shadow="hover">
          <div class="s-title">
            <span class="dot" :style="{ background: COLORS[s.key] }" />
            {{ s.name }}
            <el-tag :type="TAG_TYPES[s.tag]" size="small" effect="dark" class="tag">{{ s.tag }}</el-tag>
          </div>
          <el-descriptions :column="1" size="small" class="s-body">
            <el-descriptions-item label="达峰年份">
              {{ s.peak_year }} 年（{{ s.peak_emission_t }} tCO2e）
            </el-descriptions-item>
            <el-descriptions-item label="中和年份">
              <el-tag v-if="s.neutral_year" type="success" size="small">{{ s.neutral_year }} 年</el-tag>
              <el-tag v-else type="info" size="small">{{ s.neutral_note }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item v-if="s.annual_decline_t > 0" label="达峰后减排">
              每年 {{ s.annual_decline_t }} tCO2e
            </el-descriptions-item>
            <el-descriptions-item label="2060 年排放">{{ s.emission_2060_t }} tCO2e</el-descriptions-item>
            <el-descriptions-item label="说明">{{ s.description }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <!-- 三情景折线对比 -->
    <el-card header="三情景碳排放路径对比（2026-2060）" class="mt">
      <div ref="chartEl" class="chart" />
    </el-card>

    <el-alert v-if="result" :title="`结论：${result.conclusion}`" type="success" :closable="false" class="mt" />
    <el-alert v-if="result" :title="result.note" type="info" :closable="false" class="mt" />
  </div>
</template>

<style scoped>
.mt {
  margin-top: 16px;
}

.s-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
  margin-bottom: 10px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.tag {
  margin-left: auto;
}

.chart {
  width: 100%;
  height: 420px;
}
</style>
