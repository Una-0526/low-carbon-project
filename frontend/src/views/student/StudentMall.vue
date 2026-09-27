<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMallItems, getMyPoints, getMyRedemptions, redeemItem } from '../../api'
import { CATEGORY_DISPLAY, REDEEM_STATUS_MAP } from '../../constants/mall'

const loading = ref(false)
const submitting = ref(false)
const totalPoints = ref(0)
const items = ref([])
const records = ref([])

async function fetchAll() {
  loading.value = true
  try {
    const [p, i, r] = await Promise.all([getMyPoints(), getMallItems(), getMyRedemptions()])
    totalPoints.value = p.data.total_points
    items.value = i.data
    records.value = r.data
  } finally {
    loading.value = false
  }
}

async function onRedeem(item) {
  if (item.stock <= 0) {
    ElMessage.warning('该商品已兑完，等待补货')
    return
  }
  if (totalPoints.value < item.points_cost) {
    ElMessage.warning(`积分不足，还差 ${item.points_cost - totalPoints.value} 分`)
    return
  }
  await ElMessageBox.confirm(
    `确认花费 ${item.points_cost} 碳积分兑换「${item.name}」？`,
    '兑换确认',
    { confirmButtonText: '确认兑换', type: 'warning' },
  )
  submitting.value = true
  try {
    const { data } = await redeemItem(item.id)
    ElMessage.success(`兑换成功！剩余 ${data.remaining_points} 碳积分，请到"我的兑换"查看状态`)
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
    <!-- 顶部：当前积分 -->
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="hover">
          <el-statistic title="当前碳积分" :value="totalPoints">
            <template #suffix>分</template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <div class="hint">绿色打卡攒积分，商城好礼随心兑 🌿</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 商品列表 -->
    <el-card header="碳积分商城" class="mt">
      <div class="goods-row">
        <div v-for="item in items" :key="item.id" class="goods-card">
          <div class="goods-icon">{{ CATEGORY_DISPLAY[item.category]?.icon || '🎁' }}</div>
          <div class="goods-name">{{ item.name }}</div>
          <div class="goods-desc">{{ item.description || '—' }}</div>
          <div class="goods-meta">
            <el-tag type="success" effect="plain">{{ item.points_cost }} 积分</el-tag>
            <span class="stock" :class="{ soldout: item.stock <= 0 }">
              库存 {{ item.stock }}
            </span>
          </div>
          <el-button
            type="success"
            class="redeem-btn"
            :disabled="item.stock <= 0 || totalPoints < item.points_cost"
            :loading="submitting"
            @click="onRedeem(item)"
          >
            {{ item.stock <= 0 ? '已兑完' : '立即兑换' }}
          </el-button>
        </div>
        <el-empty v-if="!items.length" description="暂无上架商品" class="empty" />
      </div>
    </el-card>

    <!-- 我的兑换 -->
    <el-card header="我的兑换" class="mt">
      <el-table :data="records" stripe>
        <el-table-column prop="item_name" label="商品" min-width="140" />
        <el-table-column label="消耗积分" width="100">
          <template #default="{ row }">
            <span class="points">-{{ row.points_cost }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="REDEEM_STATUS_MAP[row.status]?.type || 'info'" size="small">
              {{ REDEEM_STATUS_MAP[row.status]?.label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="兑换时间" width="170">
          <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="领取时间" width="170">
          <template #default="{ row }">
            {{ row.fulfilled_at ? fmtTime(row.fulfilled_at) : '-' }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.mt {
  margin-top: 16px;
}

.hint {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #2e7d32;
  font-size: 15px;
}

.goods-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.goods-card {
  flex: 1;
  min-width: 220px;
  max-width: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 16px;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  transition: all 0.2s;
}

.goods-card:hover {
  border-color: #2e7d32;
  box-shadow: 0 4px 12px rgba(46, 125, 50, 0.15);
  transform: translateY(-2px);
}

.goods-icon {
  font-size: 40px;
}

.goods-name {
  font-weight: bold;
  font-size: 16px;
}

.goods-desc {
  font-size: 12px;
  color: #909399;
  text-align: center;
  min-height: 18px;
}

.goods-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stock {
  font-size: 12px;
  color: #606266;
}

.stock.soldout {
  color: #f56c6c;
}

.redeem-btn {
  width: 120px;
}

.points {
  color: #e6a23c;
  font-weight: bold;
}

.empty {
  width: 100%;
}
</style>
