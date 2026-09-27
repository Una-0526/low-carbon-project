<script setup>
import { onMounted, ref } from 'vue'
import { getMyDiagnosis } from '../../api'

const loading = ref(false)
const d = ref(null)

const CATEGORY_COLORS = { 出行: '#409eff', 饮食: '#67c23a', 节约用电: '#e6a23c' }
// 分类满层次数（用于进度条比例）
const CATEGORY_FULL = 10

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await getMyDiagnosis()
    d.value = data
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-loading="loading">
    <!-- 顶部统计 -->
    <el-row v-if="d" :gutter="16">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="label">本周减碳量</div>
          <div class="value green">{{ d.week_carbon_kg }} kg</div>
          <div class="sub">{{ d.week_count }} 次打卡</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="label">碳积分</div>
          <div class="value blue">{{ d.total_points }}</div>
          <div class="sub">累计积分</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="label">连续打卡天数</div>
          <div class="value orange">{{ d.streak_days }} 天</div>
          <div class="sub">最近打卡在今天或昨天才连续</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="label">本月减碳量</div>
          <div class="value">{{ d.month_carbon_kg }} kg</div>
          <div class="sub">{{ d.month_count }} 次打卡</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 行为分类统计 -->
    <el-card v-if="d" header="本周行为分类统计" class="mt">
      <el-row :gutter="24">
        <el-col v-for="c in d.categories" :key="c.category" :span="8">
          <div class="cat">
            <div class="cat-title">
              <span class="dot" :style="{ background: CATEGORY_COLORS[c.category] }" />
              {{ c.category }}
            </div>
            <el-progress :percentage="Math.min(100, Math.round(c.week_count / CATEGORY_FULL * 100))"
                         :color="CATEGORY_COLORS[c.category]" :stroke-width="10" />
            <div class="cat-sub">{{ c.week_count }} 次，减碳 {{ c.week_carbon_kg }} kg</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 个性化建议 -->
    <el-card v-if="d" header="个性化低碳建议" class="mt">
      <el-alert v-for="(a, i) in d.advice" :key="i" :title="a" type="info" :closable="false"
                class="advice" :class="{ first: i === 0 }" show-icon />
    </el-card>

    <!-- 月度碳报告 -->
    <el-card v-if="d" class="mt report">
      <template #header>
        <span>月度碳报告 · {{ d.monthly_report.month }}</span>
        <el-tag type="success" size="small" effect="plain" class="report-tag">自动生成</el-tag>
      </template>
      <el-row :gutter="16" align="middle">
        <el-col :span="8" class="report-main">
          <div class="label">本月减碳总量</div>
          <div class="value big green">{{ d.monthly_report.carbon_kg }} kg</div>
          <div class="sub">来自 {{ d.monthly_report.checkin_count }} 次已通过打卡</div>
        </el-col>
        <el-col :span="16" v-if="d.monthly_report.rank">
          <div class="report-rank">
            <div>
              班级 <b>{{ d.monthly_report.class_name }}</b> 排名：
              <span class="value blue inline">第 {{ d.monthly_report.rank }} 名</span>
              <span class="sub">/ 共 {{ d.monthly_report.class_size }} 人</span>
            </div>
            <el-progress type="dashboard" :percentage="d.monthly_report.percentile" :width="110"
                         color="#67c23a">
              <template #default>
                <div class="pct">{{ d.monthly_report.percentile }}%</div>
                <div class="pct-sub">超过同学</div>
              </template>
            </el-progress>
          </div>
        </el-col>
        <el-col :span="16" v-else>
          <el-empty description="未设置班级，暂无班级排名" :image-size="60" />
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<style scoped>
.mt {
  margin-top: 16px;
}

.label {
  font-size: 13px;
  color: #909399;
}

.value {
  font-size: 26px;
  font-weight: bold;
  margin: 6px 0 2px;
}

.value.big {
  font-size: 34px;
}

.value.inline {
  font-size: 18px;
}

.green { color: #67c23a; }
.blue { color: #409eff; }
.orange { color: #e6a23c; }

.sub {
  font-size: 12px;
  color: #c0c4cc;
}

.cat {
  padding: 4px 8px;
}

.cat-title {
  font-weight: bold;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.cat-sub {
  margin-top: 8px;
  font-size: 13px;
  color: #606266;
}

.advice {
  margin-bottom: 10px;
}

.advice.first {
  margin-top: 0;
}

.report-tag {
  margin-left: 10px;
}

.report {
  background: linear-gradient(135deg, #f0f9eb 0%, #ffffff 55%);
}

.report-main {
  text-align: center;
}

.report-rank {
  display: flex;
  align-items: center;
  justify-content: space-around;
  font-size: 15px;
}

.pct {
  font-size: 20px;
  font-weight: bold;
  color: #67c23a;
}

.pct-sub {
  font-size: 12px;
  color: #909399;
}
</style>
