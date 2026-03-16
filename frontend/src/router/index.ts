import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    { path: '/', component: () => import('@/views/DashboardView.vue') },
    { path: '/analysis/:id', component: () => import('@/views/AnalysisDetailView.vue') },
    { path: '/duplicates', component: () => import('@/views/DuplicatesView.vue') },
    { path: '/settings', component: () => import('@/views/SettingsView.vue') },
  ],
})

// 네비게이션 가드 — 미인증 시 /login으로 리다이렉트
router.beforeEach((to) => {
  const authStore = useAuthStore()
  if (!to.meta.public && !authStore.isAuthenticated) {
    return '/login'
  }
  if (to.path === '/login' && authStore.isAuthenticated) {
    return '/'
  }
})

export default router
