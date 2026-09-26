<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '../api'
import { useAuth } from '../stores/auth'

const router = useRouter()
const { setAuth, homeByRole } = useAuth()

const form = reactive({ username: '', password: '' })
const loading = ref(false)

async function onLogin() {
  if (!form.username.trim() || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const { data } = await login({ username: form.username.trim(), password: form.password })
    setAuth(data.access_token, data.user)
    ElMessage.success(`欢迎，${data.user.username}`)
    router.push(homeByRole(data.role))
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <el-card class="login-card">
      <template #header>
        <div class="login-title">🌱 低碳校园 · 登录</div>
      </template>
      <el-form label-width="70px" @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" @keyup.enter="onLogin" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" @keyup.enter="onLogin" />
        </el-form-item>
        <el-form-item>
          <el-button type="success" class="login-btn" :loading="loading" @click="onLogin">登 录</el-button>
        </el-form-item>
      </el-form>
      <el-alert type="info" :closable="false">
        <p>演示账号（密码均为 123456）：</p>
        <p>学生：张三　教师：李老师</p>
      </el-alert>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
}

.login-card {
  width: 400px;
}

.login-title {
  font-size: 20px;
  font-weight: bold;
  color: #2e7d32;
  text-align: center;
}

.login-btn {
  width: 100%;
}

.el-alert p {
  line-height: 1.6;
}
</style>
