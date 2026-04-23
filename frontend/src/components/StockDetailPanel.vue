<template>
  <div class="detail-panel">
    <!-- Header -->
    <div class="detail-header">
      <button class="back-btn" @click="$emit('back')">
        <span class="back-arrow">‹</span>
        <span class="back-text">返回</span>
      </button>
      <span class="detail-name">{{ stock.name }}</span>
      <span class="detail-code">{{ stock.symbol }}</span>
      <div class="detail-spacer"></div>
      <span class="detail-price" :class="stock.change >= 0 ? 'red' : 'green'">{{ stock.price?.toFixed(2) }}</span>
      <span class="detail-change" :class="stock.change >= 0 ? 'red' : 'green'">
        {{ stock.change >= 0 ? '+' : '' }}{{ stock.change?.toFixed(2) }}({{ getChangePercent(stock).toFixed(2) }}%)
      </span>
    </div>

    <!-- Tab 切换 -->
    <div class="tab-bar">
      <button
        v-for="t in tabs"
        :key="t.key"
        class="tab-btn"
        :class="{ active: activeTab === t.key }"
        @click="switchTab(t.key)"
      >
        <span class="tab-icon">{{ t.icon }}</span>
        <span class="tab-label">{{ t.label }}</span>
      </button>
    </div>

    <!-- 内容区（相对定位，遮罩层绝对定位在此内） -->
    <div class="content-scroll">

      <!-- 行情数据 Tab -->
      <div v-if="activeTab === 'data'" key="data">

        <!-- 概念题材栏 -->
        <div class="concept-bar" v-if="concepts.aliases.length || concepts.industries.length">
          <span class="concept-label">概念</span>
          <div class="concept-tags">
            <span v-for="tag in concepts.aliases" :key="tag" class="concept-tag tag-alias">{{ tag }}</span>
            <span v-for="ind in concepts.industries" :key="ind" class="concept-tag tag-industry">{{ ind }}</span>
          </div>
        </div>

        <div class="chart-container">
          <div ref="chartRef" style="width:100%;height:100%;"></div>
        </div>
        <div class="section-title">核心财务指标</div>
        <div class="metric-grid">
          <div v-for="(val, key) in metrics" :key="key" class="metric-card">
            <div class="metric-label">{{ key }}</div>
            <div class="metric-value">{{ val }}</div>
          </div>
        </div>
      </div>

      <!-- 研报 Tab -->
      <div v-else-if="activeTab === 'report'" key="report">
        <div class="section-title">最新研报</div>
        <div v-if="loading" class="empty-state">加载中…</div>
        <div v-else-if="reports.length === 0" class="empty-state">暂无研报数据</div>
        <div class="report-list">
          <div v-for="r in reports" :key="r.id" class="report-item">
            <div class="report-title">{{ r.title }}</div>
            <div class="report-meta">
              {{ formatReportMeta(r) }}
              <template v-if="r.target"> · 目标价：{{ r.target }}</template>
            </div>
            <span class="report-rating" :class="{
              'rating-buy':  r.rating === '买入' || r.rating === '增持',
              'rating-hold': r.rating === '中性',
              'rating-sell': r.rating === '卖出' || r.rating === '减持',
            }">{{ r.rating }}</span>
          </div>
        </div>
      </div>

      <!-- 事件 Tab -->
      <div v-else-if="activeTab === 'event'" key="event">
        <div class="section-title">公司大事件</div>
        <div v-if="loading" class="empty-state">加载中…</div>
        <div v-else-if="events.length === 0" class="empty-state">暂无事件数据</div>
        <div class="report-list">
          <div v-for="(e, i) in events" :key="i" class="report-item">
            <div class="report-title">{{ e.title }}</div>
            <div class="report-meta">
              {{ e.date }}<template v-if="e.category"> · {{ e.category }}</template>
            </div>
            <span class="report-rating" :class="e.type === 'announcement' ? 'rating-hold' : 'rating-buy'">
              {{ e.type === 'announcement' ? '公告' : '新闻' }}
            </span>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getKline, getStockMetrics, getReports, getConcepts, getEvents } from '../api/stock'

const props = defineProps({
  stock: { type: Object, required: true },
  panelWidth: { type: Number, default: 0 },
})
defineEmits(['back'])

const activeTab = ref('data')
const tabs = [
  { key: 'data',   label: '数据', icon: '📊' },
  { key: 'event',  label: '事件', icon: '📰' },
  { key: 'report', label: '研报', icon: '📄' },
]

// ── 覆盖式过场动画 ────────────────────────────────
const coverClass = ref('')

function switchTab(key) {
  if (key === activeTab.value) return
  activeTab.value = key
}

// ── 数据 ──────────────────────────────────────────
const chartRef = ref(null)
let chartInst = null
const metrics  = ref({})
const reports  = ref([])
const concepts = ref({ aliases: [], industries: [] })
const events   = ref([])
const loading  = ref(false)

// ── 数据加载 ──────────────────────────────────────
async function loadMarketData() {
  loading.value = true
  try {
    const [kline, m, r, c, ev] = await Promise.all([
      getKline(props.stock.symbol, 60),
      getStockMetrics(props.stock.symbol),
      getReports(props.stock.symbol),
      getConcepts(props.stock.symbol),
      getEvents(props.stock.symbol),
    ])
    metrics.value  = m
    reports.value  = r
    concepts.value = c
    events.value   = ev
    await nextTick()
    renderChart(kline)
  } finally {
    loading.value = false
  }
}

// ── 图表渲染 ──────────────────────────────────────
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
      { name: 'K线', type: 'candlestick', xAxisIndex: 0, yAxisIndex: 0, data: values,
        itemStyle: { color: '#ef4444', color0: '#22c55e', borderColor: '#ef4444', borderColor0: '#22c55e' } },
      { name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: vols,
        itemStyle: { color: 'rgba(75,169,154,0.4)' } },
    ],
  })
}

// ── 工具函数 ──────────────────────────────────────
function getChangePercent(stock) {
  return Number(stock?.change_pct ?? stock?.change_percent ?? 0)
}

function formatReportMeta(report) {
  return [report.broker, report.industry, report.date].filter(Boolean).join(' · ')
}

function onResize() { chartInst?.resize() }

watch(() => props.panelWidth, () => {
  nextTick(() => chartInst?.resize())
})

watch(() => props.stock, () => {
  activeTab.value = 'data'
  loadMarketData()
}, { immediate: false })

onMounted(() => {
  loadMarketData()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chartInst?.dispose()
})
</script>

<style scoped>
.detail-panel {
  display: flex; flex-direction: column; height: 100%;
  background: var(--bg-panel);
}

.detail-header {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  overflow: hidden;
}

.back-btn {
  display: inline-flex; align-items: center; gap: 4px;
  background: var(--bg-card2);
  border: 1px solid var(--border);
  border-radius: 24px;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 13px; font-weight: 500;
  padding: 5px 12px 5px 8px;
  flex-shrink: 0;
  transition: background .2s, border-color .2s, color .2s, transform .15s;
}
.back-btn:hover {
  background: rgba(75,169,154,0.1);
  border-color: var(--accent);
  color: var(--accent);
  transform: translateX(-2px);
}
.back-arrow { font-size: 18px; line-height: 1; font-weight: 300; }
.back-text { font-size: 13px; }

.detail-name {
  font-size: 15px; font-weight: 700; color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  min-width: 0; flex-shrink: 1;
}
.detail-code {
  font-size: 11px; color: var(--text-muted);
  background: var(--bg-card2);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1px 5px;
  white-space: nowrap; flex-shrink: 0;
}
.detail-spacer { flex: 1; }
.detail-price {
  font-size: 16px; font-weight: 800;
  white-space: nowrap; flex-shrink: 0;
}
.detail-change {
  font-size: 11px; font-weight: 500;
  white-space: nowrap; flex-shrink: 0;
}
.red   { color: var(--red); }
.green { color: var(--green); }

/* ── Tab 栏（三个按钮均匀排布，高度收紧） ── */
.tab-bar {
  display: flex;
  flex-shrink: 0;
  width: 100%;
  border-bottom: 2px solid var(--border);
  background: var(--bg-card);
}

.tab-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 12px 0;
  background: none;
  border: none;
  border-right: 1px solid var(--border);
  border-bottom: 3px solid transparent;
  color: var(--text-muted);
  font-weight: 500;
  font-size: 13px;
  cursor: pointer;
  transition: all .2s;
  outline: none;
}
.tab-btn:last-child { border-right: none; }
.tab-btn:hover { color: var(--text-primary); background: rgba(75,169,154,0.08); }
.tab-btn.active {
  color: var(--accent);
  background: rgba(75,169,154,0.12);
  border-bottom-color: var(--accent);
  font-weight: 600;
}
.tab-icon { font-size: 22px; line-height: 1; display: block; }
.tab-label { font-size: 13px; font-weight: 600; letter-spacing: 0.02em; }

.content-scroll { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 16px; }

/* ── 概念题材栏 ── */
.concept-bar {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 14px;
}
.concept-label {
  font-size: 11px; font-weight: 600;
  color: var(--text-muted);
  white-space: nowrap;
  padding-top: 2px;
}
.concept-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.concept-tag {
  font-size: 11px; padding: 2px 8px;
  border-radius: 20px; font-weight: 500;
}
.tag-alias    { background: rgba(75,169,154,0.12); color: var(--accent2); border: 1px solid rgba(75,169,154,0.25); }
.tag-industry { background: rgba(232,160,32,0.1);  color: var(--gold);    border: 1px solid rgba(232,160,32,0.25); }

/* ── 行情 ── */
.chart-container { height: 260px; margin-bottom: 16px; }
.section-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 10px; }
.metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 16px; }
.metric-card { background: var(--bg-card); border-radius: 8px; padding: 10px 12px; border: 1px solid var(--border); }
.metric-label { font-size: 11px; color: var(--text-muted); margin-bottom: 4px; }
.metric-value { font-size: 14px; font-weight: 600; color: var(--text-primary); }

/* ── 研报 & 事件（共用同一套卡片样式） ── */
.report-list { display: flex; flex-direction: column; gap: 10px; }
.report-item { background: var(--bg-card); border-radius: 10px; padding: 12px; border: 1px solid var(--border); position: relative; }
.report-title { font-size: 13px; font-weight: 500; color: var(--text-primary); margin-bottom: 6px; padding-right: 60px; }
.report-meta { font-size: 11px; color: var(--text-muted); }
.report-rating { position: absolute; top: 12px; right: 12px; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
.rating-buy  { background: rgba(34,197,94,.12);  color: var(--green); }
.rating-hold { background: rgba(245,158,11,.12); color: var(--gold); }
.rating-sell { background: rgba(239,68,68,.12);  color: var(--red); }

.empty-state { text-align: center; padding: 32px; color: var(--text-muted); font-size: 13px; }
.error-state { text-align: center; padding: 20px; color: var(--red); font-size: 13px; }
</style>
