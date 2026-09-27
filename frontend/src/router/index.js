import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../stores/auth'
import LoginView from '../views/LoginView.vue'
import StudentHome from '../views/student/StudentHome.vue'
import StudentCheckin from '../views/student/StudentCheckin.vue'
import TeacherDashboard from '../views/teacher/TeacherDashboard.vue'
import TeacherCheckins from '../views/teacher/TeacherCheckins.vue'
import CarbonAccounting from '../views/teacher/CarbonAccounting.vue'
import BuildingDiagnosis from '../views/teacher/BuildingDiagnosis.vue'
import PathwayView from '../views/teacher/PathwayView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { public: true },
    },
    {
      path: '/student/home',
      name: 'student-home',
      component: StudentHome,
      meta: { role: 'student' },
    },
    {
      path: '/student/checkin',
      name: 'student-checkin',
      component: StudentCheckin,
      meta: { role: 'student' },
    },
    {
      path: '/teacher/dashboard',
      name: 'teacher-dashboard',
      component: TeacherDashboard,
      meta: { role: 'teacher' },
    },
    {
      path: '/teacher/checkins',
      name: 'teacher-checkins',
      component: TeacherCheckins,
      meta: { role: 'teacher' },
    },
    {
      path: '/teacher/carbon',
      name: 'teacher-carbon',
      component: CarbonAccounting,
      meta: { role: 'teacher' },
    },
    {
      path: '/teacher/diagnosis',
      name: 'teacher-diagnosis',
      component: BuildingDiagnosis,
      meta: { role: 'teacher' },
    },
    {
      path: '/teacher/pathway',
      name: 'teacher-pathway',
      component: PathwayView,
      meta: { role: 'teacher' },
    },
    // 兼容旧路径
    { path: '/student', redirect: '/student/home' },
    { path: '/teacher', redirect: '/teacher/dashboard' },
    { path: '/', redirect: '/login' },
    { path: '/:pathMatch(.*)*', redirect: '/login' },
  ],
})

// 路由守卫：拦截未登录、按角色拦截越权访问
router.beforeEach((to) => {
  const { user, homeByRole } = useAuth()

  // 已登录访问登录页 → 跳回对应首页
  if (to.path === '/login' && user.value) {
    return homeByRole(user.value.role)
  }
  // 公开页面（登录页）直接放行
  if (to.meta.public) {
    return true
  }
  // 未登录 → 登录页
  if (!user.value) {
    return '/login'
  }
  // 角色不匹配（越权）→ 跳回自己角色的首页
  if (to.meta.role && to.meta.role !== user.value.role) {
    return homeByRole(user.value.role)
  }
  return true
})

export default router
