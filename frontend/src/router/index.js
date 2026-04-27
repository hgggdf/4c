import { createRouter, createWebHistory } from 'vue-router'
import MainPage from '../views/MainPage.vue'
import LoginPage from '../views/LoginPage.vue'

const routes = [
  { path: '/login', name: 'login', component: LoginPage },
  { path: '/', name: 'main', component: MainPage, meta: { requiresAuth: true } },
  { path: '/diagnose', name: 'diagnose', component: () => import('../views/DiagnosePage.vue'), meta: { requiresAuth: true } },
  { path: '/risk', name: 'risk', component: () => import('../views/RiskPage.vue'), meta: { requiresAuth: true } },
  { path: '/report', name: 'report', component: () => import('../views/ReportPage.vue'), meta: { requiresAuth: true } },
  { path: '/stock/:symbol', name: 'stockDetail', component: () => import('../views/StockDetail.vue'), meta: { requiresAuth: true } },
  { path: '/chat', name: 'chat', component: () => import('../views/ChatPage.vue'), meta: { requiresAuth: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const loggedIn = sessionStorage.getItem('user')
  if (to.meta.requiresAuth && !loggedIn) {
    next('/login')
  } else if (to.path === '/login' && loggedIn) {
    next('/')
  } else {
    next()
  }
})

export default router
