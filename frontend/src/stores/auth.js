import { ref } from 'vue'

const TOKEN_KEY = 'lc_token'
const USER_KEY = 'lc_user'

const token = ref(localStorage.getItem(TOKEN_KEY) || '')
const user = ref(JSON.parse(localStorage.getItem(USER_KEY) || 'null'))

function setAuth(newToken, newUser) {
  token.value = newToken
  user.value = newUser
  localStorage.setItem(TOKEN_KEY, newToken)
  localStorage.setItem(USER_KEY, JSON.stringify(newUser))
}

function clearAuth() {
  token.value = ''
  user.value = null
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

/** 按角色返回对应首页路径 */
function homeByRole(role) {
  return role === 'teacher' ? '/teacher/dashboard' : '/student/home'
}

export function useAuth() {
  return { token, user, setAuth, clearAuth, homeByRole }
}
