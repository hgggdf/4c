import { createRouter, createWebHistory } from 'vue-router'
import ChatPage from '../views/ChatPage.vue'
import StockDetail from '../views/StockDetail.vue'
import DiagnosePage from '../views/DiagnosePage.vue'
import RiskPage from '../views/RiskPage.vue'
import ReportPage from '../views/ReportPage.vue'

const routes = [
  { path: '/', name: 'chat', component: ChatPage },
  { path: '/stock/:symbol', name: 'stock-detail', component: StockDetail, props: true },
  { path: '/diagnose', name: 'diagnose', component: DiagnosePage },
  { path: '/risk', name: 'risk', component: RiskPage },
  { path: '/report', name: 'report', component: ReportPage },
]

export default createRouter({
  history: createWebHistory(),
  routes
})
