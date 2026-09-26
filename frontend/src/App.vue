<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuth } from './stores/auth'

const route = useRoute()
const router = useRouter()
const { user, clearAuth } = useAuth()

const isLogin = computed(() => route.path === '/login')

const menuItems = computed(() => {
  if (!user.value) return []
  return user.value.role === 'teacher'
    ? [
        { index: '/teacher/dashboard', label: '教师端' },
        { index: '/teacher/checkins', label: '打卡审核' },
        { index: '/teacher/carbon', label: '校园碳核算' },
      ]
    : [{ index: '/student/home', label: '首页' }, { index: '/student/checkin', label: '绿色打卡' }]
})

function onLogout() {
  clearAuth()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<template>
  <el-container v-if="!isLogin" class="layout">
    <el-header class="header">
      <div class="logo">🌱 低碳校园</div>
      <el-menu mode="horizontal" :default-active="route.path" router :ellipsis="false">
        <el-menu-item v-for="item in menuItems" :key="item.index" :index="item.index">
          {{ item.label }}
        </el-menu-item>
      </el-menu>
      <div class="user-area">
        <el-tag :type="user?.role === 'teacher' ? 'warning' : 'success'">
          {{ user?.role === 'teacher' ? '教师' : '学生' }}
        </el-tag>
        <span class="username">{{ user?.username }}</span>
        <el-button link type="danger" @click="onLogout">退出登录</el-button>
      </div>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>

  <!-- 登录页不套布局 -->
  <router-view v-else />
</template>

<style>
* {
  margin: 0;
  padding: 0;
}

.layout {
  min-height: 100vh;
}

.header {
  display: flex;
  align-items: center;
  gap: 24px;
  border-bottom: 1px solid #e4e7ed;
}

.logo {
  font-size: 20px;
  font-weight: bold;
  color: #2e7d32;
  white-space: nowrap;
}

.user-area {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}

.username {
  font-weight: bold;
}
</style>
