import { createRouter, createWebHistory } from 'vue-router'
import ChatPage from '../views/ChatPage.vue'
import StockDetail from '../views/StockDetail.vue'

const routes = [
  { path: '/', name: 'chat', component: ChatPage },
  { path: '/stock/:symbol', name: 'stock-detail', component: StockDetail, props: true }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
