<template>
  <div class="detail-panel">
    <!-- Header -->
    <div class="detail-header">
      <button class="back-btn" @click="$emit('back')">← 返回</button>
      <div>
        <span class="detail-name">{{ stock.name }}</span>
        <span class="detail-code">{{ stock.symbol }}</span>
      </div>
      <div class="detail-price-row">
        <span class="detail-price" :class="stock.change >= 0 ? 'red' : 'green'">
          {{ stock.price?.toFixed(2) }}
        </span>
        <span class="detail-change" :class="stock.change >= 0 ? 'red' : 'green'">
          {{ stock.change >= 0 ? '+' : '' }}{{ stock.change?.toFixed(2) }}
          ({{ getChangePercent(stock).toFixed(2) }}%)
        </span>
      </div>
    </div>

    <!-- Tab 切换 -->
    <div class="tab-bar" style="margin-left:0;">
      <button
        v-for="t in tabs"
        :key="t.key"
        class="tab-btn"
        :class="{ active: activeTab === t.key }"
        @click="activeTab = t.key"
      >{{ t.label }}</button>
    </div>

    <!-- 内容区 -->
    <div style="flex:1; overflow-y:auto; margin-top:16px;">

      <!-- 数据 Tab -->
      <template v-if="activeTab === 'data'">
        <!-- K线图 -->
        <div class="chart-container" style="height:260px; margin-bottom:16px;">
          <div ref="chartRef" style="width:100%;height:100%;"></div>
        </div>

        <!-- 核心指标 -->
        <div class="section-title">核心财务指标</div>
        <div class="metric-grid">
          <div v-for="(val, key) in metrics" :key="key" class="metric-card">
            <div class="metric-label">{{ key }}</div>
            <div class="metric-value">{{ val }}</div>
          </div>
        </div>
      </template>

      <!-- 研报 Tab -->
      <template v-else-if="activeTab === 'report'">
        <div class="section-title">最新研报</div>
        <div v-if="loading" class="empty-state">加载中…</div>
        <div v-else-if="reports.length === 0" class="empty-state">暂无研报数据</div>
        <div class="report-list">
          <div
            v-for="r in reports"
            :key="r.id"
            class="report-item"
          >
            <div class="report-title">{{ r.title }}</div>
            <div class="report-meta">
              {{ formatReportMeta(r) }}
              <template v-if="r.target"> · 目标价：{{ r.target }}</template>
            </div>
            <span
              class="report-rating"
              :class="{
                'rating-buy':  r.rating === '买入' || r.rating === '增持',
                'rating-hold': r.rating === '中性',
                'rating-sell': r.rating === '卖出' || r.rating === '减持',
              }"
            >{{ r.rating }}</span>
          </div>
        </div>
      </template>

    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getKline, getStockMetrics, getReports } from '../api/stock'

const props = defineProps({
  stock: { type: Object, required: true }
})
defineEmits(['back'])

const activeTab = ref('data')
const tabs = [
  { key: 'data',   label: '行情数据' },
  { key: 'report', label: '研报' },
]

const chartRef = ref(null)
let chartInst = null
const metrics = ref({})
const reports = ref([])
const loading = ref(false)

// 加载数据
async function loadData() {
  loading.value = true
  try {
    const [kline, m, r] = await Promise.all([
      getKline(props.stock.symbol, 60),
      getStockMetrics(props.stock.symbol),
      getReports(props.stock.symbol),
    ])
    metrics.value = m
    reports.value = r
    await nextTick()
    renderChart(kline)
  } finally {
    loading.value = false
  }
}

function renderChart(kline) {
  if (!chartRef.value) return
  if (!chartInst) chartInst = echarts.init(chartRef.value)
  const dates  = kline.map(d => d.date)
  const values = kline.map(d => [d.open, d.close, d.low, d.high])
  const vols   = kline.map(d => d.volume ?? d.vol ?? 0)

  chartInst.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['K线', '成交量'], textStyle: { color: '#64748b' }, top: 4 },
    grid: [
      { left: 60, right: 20, top: 32, bottom: 90 },
      { left: 60, right: 20, top: '72%', bottom: 30 },
    ],
    xAxis: [
      { type: 'category', data: dates, gridIndex: 0,
        axisLabel: { color: '#94a3b8', fontSize: 10 },
        axisLine: { lineStyle: { color: '#e2e8f0' } } },
      { type: 'category', data: dates, gridIndex: 1, show: false },
    ],
    yAxis: [
      { type: 'value', gridIndex: 0, scale: true,
        axisLabel: { color: '#94a3b8', fontSize: 10 },
        splitLine: { lineStyle: { color: '#f1f5f9' } } },
      { type: 'value', gridIndex: 1, scale: true,
        axisLabel: { color: '#94a3b8', fontSize: 10 },
        splitLine: { lineStyle: { color: '#f1f5f9' } } },
    ],
    series: [
      {
        name: 'K线', type: 'candlestick',
        xAxisIndex: 0, yAxisIndex: 0,
        data: values,
        itemStyle: {
          color: '#ef4444', color0: '#22c55e',
          borderColor: '#ef4444', borderColor0: '#22c55e',
        },
      },
      {
        name: '成交量', type: 'bar',
        xAxisIndex: 1, yAxisIndex: 1,
        data: vols,
        itemStyle: { color: 'rgba(56,189,248,0.4)' },
      },
    ],
  })
}

function getChangePercent(stock) {
  return Number(stock?.change_pct ?? stock?.change_percent ?? 0)
}

function formatReportMeta(report) {
  return [report.broker, report.industry, report.date].filter(Boolean).join(' · ')
}

function onResize() { chartInst?.resize() }

watch(() => props.stock, loadData, { immediate: false })
onMounted(() => {
  loadData()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chartInst?.dispose()
})
</script>
