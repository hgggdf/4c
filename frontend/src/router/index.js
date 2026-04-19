import { createRouter, createWebHistory } from 'vue-router'
import DiagnosePage from '../views/DiagnosePage.vue'
import RiskPage from '../views/RiskPage.vue'
import ReportPage from '../views/ReportPage.vue'
import MainPage from '../views/MainPage.vue'

const routes = [
  { path: '/', name: 'main', component: MainPage },
  { path: '/diagnose', name: 'diagnose', component: DiagnosePage },
  { path: '/risk', name: 'risk', component: RiskPage },
  { path: '/report', name: 'report', component: ReportPage },
]

export default createRouter({
  history: createWebHistory(),
  routes
})
