<template>
  <div class="card">
    <h2 class="card-title">股票详情</h2>

    <div v-if="loading" class="empty-state">加载中...</div>

    <template v-else-if="quote">
      <div style="display: flex; align-items: center; justify-content: space-between;">
        <div>
          <div style="font-size: 24px; font-weight: 800;">{{ quote.name }} ({{ quote.symbol }})</div>
          <div style="color: #6b7280; margin-top: 6px;">{{ quote.time }}</div>
        </div>
        <div>
          <div class="quote-value" :class="getChangeClass(quote.change)">
            {{ quote.price }}
          </div>
          <div :class="getChangeClass(quote.change)">
            {{ quote.change }} ({{ quote.change_percent }}%)
          </div>
        </div>
      </div>

      <div class="quote-grid">
        <div class="quote-box">
          <div class="quote-label">开盘</div>
          <div class="quote-value">{{ quote.open }}</div>
        </div>
        <div class="quote-box">
          <div class="quote-label">最高</div>
          <div class="quote-value">{{ quote.high }}</div>
        </div>
        <div class="quote-box">
          <div class="quote-label">最低</div>
          <div class="quote-value">{{ quote.low }}</div>
        </div>
        <div class="quote-box">
          <div class="quote-label">成交量</div>
          <div class="quote-value">{{ quote.volume }}</div>
        </div>
      </div>

      <div class="card" style="margin-top: 18px;">
        <h3 class="card-title">近 {{ days }} 日走势</h3>
        <StockChart :kline="kline" />
      </div>
    </template>

    <div v-else class="empty-state">暂无数据</div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getQuote, getKline } from '../api/stock'
import { getChangeClass } from '../utils/format'
import StockChart from '../components/StockChart.vue'

const route = useRoute()
const quote = ref(null)
const kline = ref([])
const loading = ref(false)
const days = 30

async function loadData() {
  loading.value = true
  try {
    quote.value = await getQuote(route.params.symbol)
    kline.value = await getKline(route.params.symbol, days)
  } finally {
    loading.value = false
  }
}

watch(() => route.params.symbol, loadData)
onMounted(loadData)
</script>
