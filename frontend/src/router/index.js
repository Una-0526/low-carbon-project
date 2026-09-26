import { createRouter, createWebHistory } from 'vue-router'
import StudentView from '../views/student/StudentView.vue'
import TeacherView from '../views/teacher/TeacherView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/student' },
    {
      path: '/student',
      name: 'student',
      component: StudentView,
    },
    {
      path: '/teacher',
      name: 'teacher',
      component: TeacherView,
    },
  ],
})

export default router
