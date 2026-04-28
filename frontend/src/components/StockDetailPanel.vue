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
          <button class="chart-expand-btn" @click="openChartModal" title="放大查看">⤢</button>
        </div>
        <div class="section-title">核心财务指标</div>
        <div class="fin-kpi-grid" v-if="parsedFinancial.hasData">
          <div v-for="kpi in parsedFinancial.kpis" :key="kpi.key" class="fin-kpi-card">
            <div class="fin-kpi-label">{{ kpi.label }}</div>
            <div class="fin-kpi-value" :class="kpi.valueClass">{{ kpi.value }}</div>
            <div class="fin-kpi-sub" v-if="kpi.sub">{{ kpi.sub }}</div>
            <div class="fin-kpi-yoy" v-if="kpi.yoy !== null">
              <span :class="kpi.yoy >= 0 ? 'fin-up' : 'fin-down'">
                {{ kpi.yoy >= 0 ? '▲' : '▼' }} {{ Math.abs(kpi.yoy).toFixed(1) }}%
              </span>
              <span class="fin-yoy-label">同比</span>
            </div>
          </div>
        </div>
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
          <a
            v-for="r in reports"
            :key="r.id"
            class="report-item"
            :href="r.pdfUrl || r.url || '#'"
            target="_blank"
            rel="noopener"
          >
            <div class="report-title">{{ r.title }}</div>
            <div class="report-meta">
              {{ formatReportMeta(r) }}
              <template v-if="r.target"> · 目标价：{{ r.target }}</template>
              <span class="preview-hint">点击跳转 ↗</span>
            </div>
            <span class="report-rating" :class="{
              'rating-buy':  r.rating === '买入' || r.rating === '增持',
              'rating-hold': r.rating === '中性',
              'rating-sell': r.rating === '卖出' || r.rating === '减持',
            }">{{ r.rating }}</span>
          </a>
        </div>
      </div>

      <!-- 事件 Tab -->
      <div v-else-if="activeTab === 'event'" key="event">
        <div class="section-title">公司大事件</div>
        <div v-if="loading" class="empty-state">加载中…</div>
        <div v-else-if="events.length === 0" class="empty-state">暂无事件数据</div>
        <div class="report-list">
          <div v-for="(e, i) in events" :key="i" class="report-item" @click="openEventPreview(e)">
            <div class="report-title">{{ e.title }}</div>
            <div class="report-meta">
              {{ e.date }}<template v-if="e.category"> · {{ e.category }}</template>
              <span class="preview-hint">点击查看</span>
            </div>
            <span class="report-rating" :class="e.type === 'announcement' ? 'rating-hold' : 'rating-buy'">
              {{ e.type === 'announcement' ? '公告' : '新闻' }}
            </span>
          </div>
        </div>
      </div>

      <!-- 公司 Tab -->
      <div v-else-if="activeTab === 'company'" key="company">
        <div v-if="!companyProfile" class="empty-state">加载中…</div>
        <template v-else>
          <!-- 基本信息行 -->
          <div class="co-info-row" v-if="parsedProfile.founded || parsedProfile.location || parsedProfile.exchange">
            <span v-if="parsedProfile.founded"  class="co-badge co-badge--year">🗓 {{ parsedProfile.founded }}</span>
            <span v-if="parsedProfile.location"  class="co-badge co-badge--loc">📍 {{ parsedProfile.location }}</span>
            <span v-if="parsedProfile.exchange"  class="co-badge co-badge--ex">🏛 {{ parsedProfile.exchange }}</span>
          </div>

          <!-- 主营业务 -->
          <div class="co-block" v-if="parsedProfile.business">
            <div class="co-block-head">
              <span class="co-block-icon">🏭</span>
              <span class="co-block-title">主营业务</span>
            </div>
            <p class="co-block-text">{{ parsedProfile.business }}</p>
          </div>

          <!-- 市场地位 / 荣誉 -->
          <div class="co-block" v-if="parsedProfile.rankings.length">
            <div class="co-block-head">
              <span class="co-block-icon">🏆</span>
              <span class="co-block-title">市场地位</span>
            </div>
            <div class="co-tags">
              <span v-for="r in parsedProfile.rankings" :key="r" class="co-tag co-tag--rank">{{ r }}</span>
            </div>
          </div>

          <!-- 产品 & 业务板块 -->
          <div class="co-block" v-if="parsedProfile.products.length || parsedProfile.segments.length">
            <div class="co-block-head">
              <span class="co-block-icon">💊</span>
              <span class="co-block-title">产品 & 业务</span>
            </div>
            <div class="co-tags">
              <span v-for="p in parsedProfile.products" :key="p" class="co-tag co-tag--product">{{ p }}</span>
              <span v-for="s in parsedProfile.segments" :key="s" class="co-tag co-tag--segment">{{ s }}</span>
            </div>
          </div>

          <!-- 战略方向 -->
          <div class="co-block" v-if="parsedProfile.strategy">
            <div class="co-block-head">
              <span class="co-block-icon">🎯</span>
              <span class="co-block-title">战略方向</span>
            </div>
            <p class="co-block-text">{{ parsedProfile.strategy }}</p>
          </div>

          <!-- 完整简介折叠 -->
          <div class="co-full-wrap" v-if="companyProfile.business_summary">
            <button class="co-full-toggle" @click="showFullSummary = !showFullSummary">
              {{ showFullSummary ? '收起完整简介 ▲' : '查看完整简介 ▼' }}
            </button>
            <div v-if="showFullSummary" class="co-full-text">{{ companyProfile.business_summary }}</div>
          </div>
        </template>
      </div>

      <!-- 财务 Tab -->
      <div v-else-if="activeTab === 'financial'" key="financial">
        <div v-if="!financialSummary" class="empty-state">加载中…</div>
        <div v-else-if="!parsedFinancial.hasData" class="empty-state">暂无财务数据</div>
        <template v-else>

          <!-- 最新期标题 -->
          <div class="fin-period-bar">
            <span class="fin-period-label">最新报告期</span>
            <span class="fin-period-val">{{ parsedFinancial.latestPeriod }}</span>
          </div>

          <!-- 核心指标卡片 2×2 -->
          <div class="fin-kpi-grid">
            <div v-for="kpi in parsedFinancial.kpis" :key="kpi.key" class="fin-kpi-card">
              <div class="fin-kpi-label">{{ kpi.label }}</div>
              <div class="fin-kpi-value" :class="kpi.valueClass">{{ kpi.value }}</div>
              <div class="fin-kpi-sub" v-if="kpi.sub">{{ kpi.sub }}</div>
              <div class="fin-kpi-yoy" v-if="kpi.yoy !== null">
                <span :class="kpi.yoy >= 0 ? 'fin-up' : 'fin-down'">
                  {{ kpi.yoy >= 0 ? '▲' : '▼' }} {{ Math.abs(kpi.yoy).toFixed(1) }}%
                </span>
                <span class="fin-yoy-label">同比</span>
              </div>
            </div>
          </div>

          <!-- 盈利能力指标行 -->
          <div class="fin-section-title">盈利能力</div>
          <div class="fin-ratio-row" v-if="parsedFinancial.ratios.length">
            <div v-for="r in parsedFinancial.ratios" :key="r.key" class="fin-ratio-item">
              <div class="fin-ratio-label">{{ r.label }}</div>
              <div class="fin-ratio-bar-wrap">
                <div class="fin-ratio-bar" :style="{ width: r.barPct + '%', background: r.color }"></div>
              </div>
              <div class="fin-ratio-val" :style="{ color: r.color }">{{ r.value }}</div>
            </div>
          </div>

          <!-- 资产负债 & 费用结构 并排 -->
          <div class="fin-two-col" v-if="parsedFinancial.balanceItems.length || parsedFinancial.expenseItems.length">
            <div class="fin-mini-block" v-if="parsedFinancial.balanceItems.length">
              <div class="fin-mini-title">资产负债</div>
              <div v-for="item in parsedFinancial.balanceItems" :key="item.label" class="fin-mini-row">
                <span class="fin-mini-label">{{ item.label }}</span>
                <span class="fin-mini-val">{{ item.value }}</span>
              </div>
            </div>
            <div class="fin-mini-block" v-if="parsedFinancial.expenseItems.length">
              <div class="fin-mini-title">费用结构</div>
              <div v-for="item in parsedFinancial.expenseItems" :key="item.label" class="fin-mini-row">
                <span class="fin-mini-label">{{ item.label }}</span>
                <span class="fin-mini-val">{{ item.value }}</span>
              </div>
            </div>
          </div>

          <!-- 现金流 -->
          <div class="fin-cashflow-block" v-if="parsedFinancial.cashflowItems.length">
            <div class="fin-mini-title">现金流量</div>
            <div v-for="item in parsedFinancial.cashflowItems" :key="item.label" class="fin-cf-row">
              <span class="fin-cf-label">{{ item.label }}</span>
              <span class="fin-cf-bar-wrap">
                <span class="fin-cf-bar" :class="item.pos ? 'fin-cf-pos' : 'fin-cf-neg'"
                  :style="{ width: item.barPct + '%' }"></span>
              </span>
              <span class="fin-cf-val" :class="item.pos ? 'fin-pos' : 'fin-neg'">{{ item.value }}</span>
            </div>
          </div>

          <!-- 多期趋势表 -->
          <div class="fin-section-title" v-if="parsedFinancial.trendRows.length">历史趋势</div>
          <div class="fin-trend-wrap" v-if="parsedFinancial.trendRows.length">
            <div class="fin-trend-table">
              <div class="fin-trend-head">
                <span class="fin-trend-metric">指标</span>
                <span v-for="p in parsedFinancial.trendPeriods" :key="p" class="fin-trend-period">{{ p }}</span>
              </div>
              <div v-for="row in parsedFinancial.trendRows" :key="row.key" class="fin-trend-row">
                <span class="fin-trend-metric">{{ row.label }}</span>
                <span v-for="(v, i) in row.values" :key="i" class="fin-trend-cell"
                  :class="row.colorize ? (parseFloat(v) >= 0 ? 'fin-pos' : 'fin-neg') : ''">
                  {{ v }}
                </span>
              </div>
            </div>
          </div>

        </template>
      </div>

    </div>

    <!-- 事件详情弹窗 -->
    <Teleport to="body">
      <div v-if="eventPreview.visible" class="preview-overlay" @click.self="eventPreview.visible = false">
        <div class="preview-modal">
          <div class="preview-header">
            <span class="preview-title">{{ eventPreview.title }}</span>
            <a v-if="eventPreview.url" :href="eventPreview.url" target="_blank" class="preview-link-btn">查看原文 ↗</a>
            <button class="preview-close" @click="eventPreview.visible = false">✕</button>
          </div>
          <div class="preview-body">
            <div v-if="eventPreview.loading" class="preview-loading">
              <div class="spinner"></div>
              <span>加载中...</span>
            </div>
            <div v-else-if="eventPreview.error" class="preview-error">{{ eventPreview.error }}</div>
            <div v-else class="preview-pages">
              <div class="preview-page">
                <div class="preview-text">{{ eventPreview.content }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- K线放大弹窗 -->
    <Teleport to="body">
      <div v-if="chartModal.visible" class="chart-modal-overlay" @click.self="closeChartModal">
        <div class="chart-modal">
          <div class="chart-modal-header">
            <span class="chart-modal-title">{{ stock.name }} · K线图</span>
            <div class="chart-modal-periods">
              <button
                v-for="p in chartPeriods"
                :key="p.value"
                class="period-btn"
                :class="{ active: chartModal.period === p.value }"
                @click="switchChartPeriod(p.value)"
              >{{ p.label }}</button>
            </div>
            <button class="preview-close" @click="closeChartModal">✕</button>
          </div>
          <div class="chart-modal-body">
            <div ref="modalChartRef" style="width:100%;height:100%;"></div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getKline, getStockMetrics, getReports, getConcepts, getEvents } from '../api/stock'
import { getCompanyProfile } from '../api/company'
import { getFinancialSummary } from '../api/financial'

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
  { key: 'company', label: '公司', icon: '🏢' },
  { key: 'financial', label: '财务', icon: '💰' },
]

// ── 覆盖式过场动画 ────────────────────────────────
const coverClass = ref('')

// 事件详情弹窗
const eventPreview = ref({ visible: false, loading: false, title: '', content: '', error: '', url: '' })

async function openEventPreview(event) {
  const content = event.summary || event.content || ''
  eventPreview.value = { visible: true, loading: false, title: event.title, content, error: '', url: event.url }
}

function switchTab(key) {
  if (key === activeTab.value) return
  activeTab.value = key
}

watch(activeTab, async (val) => {
  if (val === 'data' && lastKline) {
    await nextTick()
    renderChart(lastKline)
  }
})

// ── 数据 ──────────────────────────────────────────
const chartRef = ref(null)
let chartInst = null
let lastKline = null

// K线放大弹窗
const modalChartRef = ref(null)
let modalChartInst = null
let fullKline = null  // 存完整日K数据用于聚合
const chartModal = ref({ visible: false, period: 'day' })
const chartPeriods = [
  { label: '日K', value: 'day' },
]

// 把日K聚合成周K或月K
function aggregateKline(dailyKline, type) {
  if (type === 'day') return dailyKline
  const groups = new Map()
  for (const bar of dailyKline) {
    const d = new Date(bar.date)
    let key
    if (type === 'week') {
      // 取该周周一的日期作为 key
      const day = d.getDay() || 7
      const mon = new Date(d)
      mon.setDate(d.getDate() - day + 1)
      key = mon.toISOString().slice(0, 10)
    } else {
      key = bar.date.slice(0, 7)  // YYYY-MM
    }
    if (!groups.has(key)) {
      groups.set(key, { date: key, open: bar.open, high: bar.high, low: bar.low, close: bar.close, volume: bar.volume ?? 0 })
    } else {
      const g = groups.get(key)
      g.high   = Math.max(g.high, bar.high)
      g.low    = Math.min(g.low,  bar.low)
      g.close  = bar.close
      g.volume = (g.volume ?? 0) + (bar.volume ?? 0)
    }
  }
  return Array.from(groups.values())
}

async function openChartModal() {
  chartModal.value.visible = true
  chartModal.value.period = 'day'
  // 拉取足够长的日K数据（365天）供聚合
  try {
    fullKline = await getKline(props.stock.symbol, 365)
  } catch (_) {
    fullKline = lastKline
  }
  await nextTick()
  renderModalChart(aggregateKline(fullKline, 'day'))
}

function closeChartModal() {
  chartModal.value.visible = false
  if (modalChartInst) { modalChartInst.dispose(); modalChartInst = null }
}

function switchChartPeriod(period) {
  chartModal.value.period = period
  if (!fullKline?.length) return
  renderModalChart(aggregateKline(fullKline, period))
}

function renderModalChart(kline) {
  if (!modalChartRef.value || !kline?.length) return
  if (modalChartInst) modalChartInst.dispose()
  modalChartInst = echarts.init(modalChartRef.value)
  const dates  = kline.map(d => d.date)
  const values = kline.map(d => [d.open, d.close, d.low, d.high])
  const vols   = kline.map(d => d.volume ?? d.vol ?? 0)
  modalChartInst.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['K线', '成交量'], textStyle: { color: '#64748b' }, top: 4 },
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 60, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1], start: 60, end: 100,
        bottom: 8, height: 24,
        fillerColor: 'rgba(75,169,154,0.15)',
        borderColor: 'var(--border)',
        handleStyle: { color: 'var(--accent)' },
        textStyle: { color: '#94a3b8', fontSize: 10 } },
    ],
    grid: [
      { left: 64, right: 20, top: 36, bottom: 80 },
      { left: 64, right: 20, top: '72%', bottom: 52 },
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
const metrics  = ref({})
const reports  = ref([])
const concepts = ref({ aliases: [], industries: [] })
const events   = ref([])
const loading  = ref(false)
const companyProfile = ref(null)
const financialSummary = ref(null)
const showFullSummary = ref(false)

// ── 数字格式化工具 ────────────────────────────────
function fmtAmount(v) {
  if (v == null || v === '') return '--'
  const n = Number(v)
  if (!isFinite(n)) return '--'
  const abs = Math.abs(n)
  if (abs >= 1e8)  return (n / 1e8).toFixed(2) + ' 亿'
  if (abs >= 1e4)  return (n / 1e4).toFixed(2) + ' 万'
  return n.toFixed(2)
}
function fmtPct(v) {
  if (v == null || v === '') return '--'
  const n = Number(v)
  if (!isFinite(n)) return '--'
  return (n * 100).toFixed(2) + '%'
}
function fmtPctDirect(v) {   // 已经是百分比值（如 0.35 表示 35%）
  if (v == null || v === '') return '--'
  const n = Number(v)
  if (!isFinite(n)) return '--'
  // 判断是否已经是百分比形式（>1 视为已是百分比）
  return Math.abs(n) > 1 ? n.toFixed(2) + '%' : (n * 100).toFixed(2) + '%'
}
function fmtNum(v, decimals = 2) {
  if (v == null || v === '') return '--'
  const n = Number(v)
  return isFinite(n) ? n.toFixed(decimals) : '--'
}
function calcYoy(curr, prev) {
  if (curr == null || prev == null || prev === 0) return null
  return ((curr - prev) / Math.abs(prev)) * 100
}

// ── 财务数据解析 ──────────────────────────────────
const parsedFinancial = computed(() => {
  const d = financialSummary.value
  if (!d || typeof d !== 'object') return { hasData: false }

  const stmts = d.income_statements || []
  const latest = d.latest_income || stmts[0] || null
  const prev   = stmts[1] || null

  if (!latest) return { hasData: false }

  const reportTypeMap = { annual: '年报', q1: '一季报', semiannual: '半年报', q3: '三季报', q4: '年报', daily: '日报' }
  const latestPeriod = latest.report_date
    ? `${latest.fiscal_year || ''} ${reportTypeMap[latest.report_type] || latest.report_type || ''} (${latest.report_date})`
    : '--'

  // 核心 KPI 卡片
  const kpis = [
    {
      key: 'revenue',
      label: '营业收入',
      value: fmtAmount(latest.revenue),
      sub: '元',
      yoy: calcYoy(latest.revenue, prev?.revenue),
      valueClass: '',
    },
    {
      key: 'net_profit',
      label: '归母净利润',
      value: fmtAmount(latest.net_profit),
      sub: '元',
      yoy: calcYoy(latest.net_profit, prev?.net_profit),
      valueClass: latest.net_profit > 0 ? 'fin-pos' : latest.net_profit < 0 ? 'fin-neg' : '',
    },
    {
      key: 'eps',
      label: '每股收益(EPS)',
      value: latest.eps != null ? fmtNum(latest.eps) + ' 元' : '--',
      sub: '',
      yoy: calcYoy(latest.eps, prev?.eps),
      valueClass: '',
    },
    {
      key: 'cashflow',
      label: '经营现金流',
      value: fmtAmount(latest.operating_cashflow),
      sub: '元',
      yoy: calcYoy(latest.operating_cashflow, prev?.operating_cashflow),
      valueClass: latest.operating_cashflow > 0 ? 'fin-pos' : latest.operating_cashflow < 0 ? 'fin-neg' : '',
    },
  ].filter(k => k.value !== '--')

  // 利润率 & 结构指标（带进度条）
  const km = d.key_metrics?.[0] || latest
  function toBarPct(v) {
    const n = Math.abs(Number(v))
    return Math.min(n > 1 ? n : n * 100, 100)
  }
  const ratios = []
  if (km.gross_margin != null) ratios.push({ key: 'gm',  label: '毛利率',    value: fmtPctDirect(km.gross_margin), barPct: toBarPct(km.gross_margin), color: '#4ba99a' })
  if (km.net_margin  != null) ratios.push({ key: 'nm',  label: '净利率',    value: fmtPctDirect(km.net_margin),  barPct: toBarPct(km.net_margin),  color: '#3d9688' })
  if (km.roe         != null) ratios.push({ key: 'roe', label: 'ROE',       value: fmtPctDirect(km.roe),         barPct: toBarPct(km.roe),         color: '#e8a020' })
  if (km.rd_ratio    != null) ratios.push({ key: 'rd',  label: '研发费用率', value: fmtPctDirect(km.rd_ratio),    barPct: toBarPct(km.rd_ratio),    color: '#6366f1' })
  if (km.debt_ratio  != null) ratios.push({ key: 'dr',  label: '资产负债率', value: fmtPctDirect(km.debt_ratio),  barPct: toBarPct(km.debt_ratio),  color: '#e05252' })

  // 资产负债摘要
  const balanceItems = []
  if (latest.total_assets    != null) balanceItems.push({ label: '总资产',   value: fmtAmount(latest.total_assets) })
  if (latest.total_liabilities != null) balanceItems.push({ label: '总负债', value: fmtAmount(latest.total_liabilities) })
  const equity = (latest.total_assets && latest.total_liabilities)
    ? latest.total_assets - latest.total_liabilities : null
  if (equity != null) balanceItems.push({ label: '净资产', value: fmtAmount(equity) })

  // 费用结构
  const expenseItems = []
  if (latest.selling_expense != null) expenseItems.push({ label: '销售费用', value: fmtAmount(latest.selling_expense) })
  if (latest.admin_expense   != null) expenseItems.push({ label: '管理费用', value: fmtAmount(latest.admin_expense) })
  if (latest.rd_expense      != null) expenseItems.push({ label: '研发费用', value: fmtAmount(latest.rd_expense) })

  // 现金流摘要（barPct 基于最大绝对值归一化）
  const cfRaw = [
    { label: '经营活动', raw: latest.operating_cashflow },
    { label: '投资活动', raw: latest.investing_cashflow },
    { label: '筹资活动', raw: latest.financing_cashflow },
  ].filter(x => x.raw != null)
  const cfMax = Math.max(...cfRaw.map(x => Math.abs(x.raw)), 1)
  const cashflowItems = cfRaw.map(x => ({
    label: x.label,
    value: fmtAmount(x.raw),
    pos: x.raw >= 0,
    barPct: Math.round(Math.abs(x.raw) / cfMax * 100),
  }))

  // 多期趋势表（最多 6 期）
  const trendSlice = stmts.slice(0, 6)
  const trendPeriods = trendSlice.map(s => {
    const t = reportTypeMap[s.report_type] || s.report_type || ''
    return s.report_date?.slice(0, 7) + (t ? `\n${t}` : '')
  })
  const trendRows = [
    { key: 'revenue',    label: '营收',    values: trendSlice.map(s => fmtAmount(s.revenue)),    colorize: false },
    { key: 'net_profit', label: '净利润',  values: trendSlice.map(s => fmtAmount(s.net_profit)), colorize: true  },
    { key: 'gross_margin', label: '毛利率', values: trendSlice.map(s => s.gross_margin != null ? fmtPctDirect(s.gross_margin) : '--'), colorize: false },
    { key: 'net_margin', label: '净利率',  values: trendSlice.map(s => s.net_margin  != null ? fmtPctDirect(s.net_margin)  : '--'), colorize: false },
    { key: 'eps',        label: 'EPS',     values: trendSlice.map(s => fmtNum(s.eps)),            colorize: true  },
    { key: 'rd_ratio',   label: '研发费率', values: trendSlice.map(s => s.rd_ratio != null ? fmtPctDirect(s.rd_ratio) : '--'), colorize: false },
  ].filter(r => r.values.some(v => v !== '--'))

  return { hasData: true, latestPeriod, kpis, ratios, balanceItems, expenseItems, cashflowItems, trendPeriods, trendRows }
})

// ── 公司概况解析 ──────────────────────────────────
const parsedProfile = computed(() => {
  const raw = companyProfile.value?.business_summary || ''
  const extra = companyProfile.value || {}

  // 成立年份：兼容多种表述
  const foundedMatch =
    raw.match(/(?:创立|成立|创建|创办)于(\d{4})年/) ||
    raw.match(/于(\d{4})年(?:在.{2,10})?(?:挂牌上市|上市|成立)/) ||
    raw.match(/(\d{4})年(?:创立|成立|创建|创办)/)
  const founded = foundedMatch ? foundedMatch[1] + ' 年成立' : ''

  // 总部地点
  const locMatch = raw.match(/总部(?:位于|设于|坐落于)([^,，。；\s]{2,12})/)
  const location = locMatch ? locMatch[1] : ''

  // 上市交易所
  const exMap = {
    '深交所': '深交所', '深圳证券交易所': '深交所',
    '上交所': '上交所', '上海证券交易所': '上交所',
    '科创板': '科创板', '创业板': '创业板',
    '港交所': '港交所', '香港联合交易所': '港交所',
    'A+H': 'A+H 两地上市',
  }
  let exchange = ''
  for (const [kw, label] of Object.entries(exMap)) {
    if (raw.includes(kw)) { exchange = label; break }
  }

  // 主营业务：优先找"主营/专注/聚焦/是一家"句，过滤上市/证券信息，fallback 取第一句
  const bizPatterns = [
    /主营([^。]{5,60})/,
    /(?:专注于|聚焦于?)([^，。]{5,50})/,
    /主要(?:从事|业务)([^。]{5,60})/,
    /是一家([^。]{5,60})/,
  ]
  const bizHardExclude = /上市|挂牌|证券交易所|股票代码/
  let business = ''
  for (const pat of bizPatterns) {
    const m = raw.match(pat)
    if (m && m[0].length <= 80 && !bizHardExclude.test(m[0])) { business = m[0]; break }
  }
  if (!business) {
    // fallback：取第一个不含上市/证券信息的句子（允许含使命/战略）
    for (const s of raw.split('。')) {
      const t = s.trim()
      if (t.length > 10 && !bizHardExclude.test(t)) {
        business = t.slice(0, 80) + (t.length > 80 ? '…' : '')
        break
      }
    }
  }

  // 市场地位 / 排名：按分隔符拆句，找含关键词的短句，排除愿景句
  const rankKeywords = [/第\d+位/, /前\d+/, /TOP\s*\d+/i, /百强/, /领军/, /龙头/, /第一/, /\d+强/, /标杆/, /冠军/]
  const rankExclude = /^(致力|坚持|奉行|秉承|始终|持续|不断)/
  const rankings = []
  for (const part of raw.split(/[;；,，。]/)) {
    const p = part.trim()
    if (p.length < 4 || p.length > 40) continue
    if (rankExclude.test(p)) continue
    if (rankKeywords.some(kw => kw.test(p))) rankings.push(p)
  }

  // 产品线：从 core_products_json 或文本中提取
  let products = []
  if (Array.isArray(extra.core_products_json) && extra.core_products_json.length) {
    products = extra.core_products_json.slice(0, 8)
  } else {
    // 从文本提取"主营X、Y、Z业务"模式
    const prodMatch = raw.match(/主营([^。]{5,60})业务/)
    if (prodMatch) {
      products = prodMatch[1].split(/[、,，]/).map(s => s.trim()).filter(s => s.length > 1 && s.length < 12).slice(0, 6)
    }
  }

  // 业务板块
  let segments = []
  if (Array.isArray(extra.main_segments_json) && extra.main_segments_json.length) {
    segments = extra.main_segments_json.slice(0, 6)
  }

  // 战略方向：提取含"战略"、"发展理念"、"致力"的句子
  const stratMatch = raw.match(/[^。]*(?:战略|发展理念|致力于|愿景|使命)[^。]{10,80}。/)
  const strategy = stratMatch ? stratMatch[0].trim() : ''

  return { founded, location, exchange, business, rankings: [...rankings].slice(0, 4), products, segments, strategy }
})

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
    lastKline = kline
    loadCompanyProfile()
    loadFinancialSummary()
  } finally {
    loading.value = false
  }
}

// ── 图表渲染 ──────────────────────────────────────
function renderChart(kline) {
  if (!chartRef.value) return
  chartInst = echarts.init(chartRef.value)
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

async function loadCompanyProfile() {
  try {
    const res = await getCompanyProfile(props.stock.symbol)
    companyProfile.value = res && typeof res === 'object' ? res : null
  } catch (err) {
    console.error('[loadCompanyProfile]', err)
  }
}

async function loadFinancialSummary() {
  try {
    const res = await getFinancialSummary(props.stock.symbol, 6)
    financialSummary.value = res && typeof res === 'object' ? res : null
  } catch (err) {
    console.error('[loadFinancialSummary]', err)
  }
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
  modalChartInst?.dispose()
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
.chart-container { height: 260px; margin-bottom: 16px; position: relative; }

.chart-expand-btn {
  position: absolute; top: 6px; right: 6px; z-index: 10;
  background: rgba(0,0,0,0.35); border: none; border-radius: 6px;
  color: #fff; font-size: 15px; width: 28px; height: 28px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: opacity .2s;
}
.chart-container:hover .chart-expand-btn { opacity: 1; }

/* K线放大弹窗 */
.chart-modal-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.7);
  display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(4px);
}
.chart-modal {
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: 14px;
  width: min(960px, 95vw);
  height: min(600px, 88vh);
  display: flex; flex-direction: column;
  box-shadow: 0 24px 60px rgba(0,0,0,0.4);
  overflow: hidden;
}
.chart-modal-header {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 18px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.chart-modal-title {
  font-size: 14px; font-weight: 700; color: var(--text-primary);
}
.chart-modal-periods {
  display: flex; gap: 4px; margin-left: 8px;
}
.period-btn {
  background: var(--bg-card2); border: 1px solid var(--border);
  border-radius: 6px; color: var(--text-muted);
  font-size: 12px; font-weight: 500; padding: 3px 10px;
  cursor: pointer; transition: all .15s;
}
.period-btn:hover { color: var(--text-primary); border-color: var(--accent); }
.period-btn.active {
  background: rgba(75,169,154,0.15);
  border-color: var(--accent); color: var(--accent); font-weight: 600;
}
.chart-modal-body { flex: 1; padding: 8px; min-height: 0; }
.section-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 10px; }
.metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 16px; }
.metric-card { background: var(--bg-card); border-radius: 8px; padding: 10px 12px; border: 1px solid var(--border); }
.metric-label { font-size: 11px; color: var(--text-muted); margin-bottom: 4px; }
.metric-value { font-size: 14px; font-weight: 600; color: var(--text-primary); }

/* ── 研报 & 事件（共用同一套卡片样式） ── */
.report-list { display: flex; flex-direction: column; gap: 10px; }
.report-item {
  background: var(--bg-card); border-radius: 10px; padding: 12px;
  border: 1px solid var(--border); position: relative;
  cursor: pointer; transition: border-color .2s, box-shadow .2s;
}
.report-item:hover {
  border-color: var(--accent);
  box-shadow: 0 2px 12px rgba(75,169,154,0.12);
}
.preview-hint {
  margin-left: auto; float: right;
  font-size: 10px; color: var(--accent);
  opacity: 0; transition: opacity .2s;
}
.report-item:hover .preview-hint { opacity: 1; }
.report-title { font-size: 13px; font-weight: 500; color: var(--text-primary); margin-bottom: 6px; padding-right: 60px; }
.report-meta { font-size: 11px; color: var(--text-muted); }
.report-rating { position: absolute; top: 12px; right: 12px; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
.rating-buy  { background: rgba(34,197,94,.12);  color: var(--green); }
.rating-hold { background: rgba(245,158,11,.12); color: var(--gold); }
.rating-sell { background: rgba(239,68,68,.12);  color: var(--red); }

.empty-state { text-align: center; padding: 32px; color: var(--text-muted); font-size: 13px; }
.error-state { text-align: center; padding: 20px; color: var(--red); font-size: 13px; }

/* ── 公司概况 ── */
.co-info-row {
  display: flex; flex-wrap: wrap; gap: 6px;
  margin-bottom: 14px;
}
.co-badge {
  font-size: 11px; font-weight: 600;
  padding: 3px 10px; border-radius: 20px;
  display: inline-flex; align-items: center; gap: 4px;
}
.co-badge--year { background: rgba(75,169,154,0.1); color: var(--accent2); border: 1px solid rgba(75,169,154,0.25); }
.co-badge--loc  { background: rgba(232,160,32,0.08); color: #a07010; border: 1px solid rgba(232,160,32,0.2); }
.co-badge--ex   { background: rgba(99,102,241,0.08); color: #4f46e5; border: 1px solid rgba(99,102,241,0.2); }

.co-block {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 10px;
}
.co-block-head {
  display: flex; align-items: center; gap: 6px;
  margin-bottom: 8px;
}
.co-block-icon { font-size: 15px; line-height: 1; }
.co-block-title {
  font-size: 12px; font-weight: 700;
  color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.04em;
}
.co-block-text {
  font-size: 12px; line-height: 1.75;
  color: var(--text-primary);
  margin: 0;
}

.co-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.co-tag {
  font-size: 11px; font-weight: 500;
  padding: 3px 9px; border-radius: 20px;
}
.co-tag--rank    { background: rgba(232,160,32,0.1); color: #a07010; border: 1px solid rgba(232,160,32,0.25); }
.co-tag--product { background: rgba(75,169,154,0.1); color: var(--accent2); border: 1px solid rgba(75,169,154,0.25); }
.co-tag--segment { background: rgba(99,102,241,0.08); color: #4f46e5; border: 1px solid rgba(99,102,241,0.2); }

.co-full-wrap { margin-top: 4px; }
.co-full-toggle {
  width: 100%; padding: 7px;
  background: none; border: 1px dashed var(--border);
  border-radius: 8px; cursor: pointer;
  font-size: 11px; color: var(--text-muted);
  transition: color .2s, border-color .2s;
}
.co-full-toggle:hover { color: var(--accent); border-color: var(--accent); }
.co-full-text {
  margin-top: 8px;
  font-size: 12px; line-height: 1.8;
  color: var(--text-secondary);
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 14px;
  white-space: pre-wrap;
}

/* ── 财务 Tab ── */
.fin-period-bar {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 14px;
  padding: 6px 10px;
  background: var(--bg-card2);
  border-radius: 8px;
  border: 1px solid var(--border);
}
.fin-period-label {
  font-size: 11px; font-weight: 600;
  color: var(--text-muted);
  white-space: nowrap;
}
.fin-period-val {
  font-size: 12px; font-weight: 700;
  color: var(--accent2);
}

/* KPI 卡片 2×2 */
.fin-kpi-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 12px;
}
.fin-kpi-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 12px 10px;
}
.fin-kpi-label {
  font-size: 11px; font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 4px;
}
.fin-kpi-value {
  font-size: 18px; font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
  margin-bottom: 2px;
}
.fin-kpi-sub {
  font-size: 10px; color: var(--text-muted);
}
.fin-kpi-yoy {
  display: flex; align-items: center; gap: 4px;
  margin-top: 4px;
}
.fin-yoy-label { font-size: 10px; color: var(--text-muted); }
.fin-up   { font-size: 11px; font-weight: 700; color: var(--red); }
.fin-down { font-size: 11px; font-weight: 700; color: var(--green); }
.fin-pos  { color: var(--red); }
.fin-neg  { color: var(--green); }

/* 利润率进度条 */
.fin-ratio-row {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 12px;
  display: flex; flex-direction: column; gap: 10px;
}
.fin-ratio-item {
  display: grid;
  grid-template-columns: 56px 1fr 48px;
  align-items: center;
  gap: 8px;
}
.fin-ratio-label {
  font-size: 11px; font-weight: 600;
  color: var(--text-muted);
  white-space: nowrap;
}
.fin-ratio-bar-wrap {
  height: 6px;
  background: var(--bg-card2);
  border-radius: 3px;
  overflow: hidden;
}
.fin-ratio-bar {
  height: 100%; border-radius: 3px;
  transition: width .4s ease;
}
.fin-ratio-val {
  font-size: 12px; font-weight: 700;
  text-align: right;
}

/* 小节标题 */
.fin-section-title {
  font-size: 11px; font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.05em;
  margin: 14px 0 6px;
}

/* 两列并排块 */
.fin-two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 12px;
}
.fin-mini-block {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 12px;
}
.fin-mini-title {
  font-size: 10px; font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.04em;
  margin-bottom: 8px;
}
.fin-mini-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 3px 0;
  border-bottom: 1px solid rgba(0,0,0,0.04);
}
.fin-mini-row:last-child { border-bottom: none; }
.fin-mini-label { font-size: 11px; color: var(--text-muted); }
.fin-mini-val   { font-size: 11px; font-weight: 600; color: var(--text-primary); }

/* 现金流块 */
.fin-cashflow-block {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 12px;
}
.fin-cf-row {
  display: grid;
  grid-template-columns: 52px 1fr 64px;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}
.fin-cf-label { font-size: 11px; font-weight: 600; color: var(--text-muted); white-space: nowrap; }
.fin-cf-bar-wrap {
  height: 6px; background: var(--bg-card2); border-radius: 3px; overflow: hidden;
}
.fin-cf-bar { display: block; height: 100%; border-radius: 3px; transition: width .4s ease; }
.fin-cf-pos { background: #4ba99a; }
.fin-cf-neg { background: #e05252; }
.fin-cf-val { font-size: 11px; font-weight: 700; text-align: right; white-space: nowrap; }

/* 多期趋势表 */
.fin-trend-wrap {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}
.fin-trend-title {
  font-size: 11px; font-weight: 700;
  color: var(--text-muted);
  padding: 8px 12px;
  background: var(--bg-card2);
  border-bottom: 1px solid var(--border);
}
.fin-trend-table { padding: 4px 0; }
.fin-trend-head, .fin-trend-row {
  display: grid;
  grid-template-columns: 52px repeat(6, 1fr);
  padding: 6px 12px;
  gap: 4px;
}
.fin-trend-head {
  font-size: 10px; font-weight: 700;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border);
  padding-bottom: 6px;
}
.fin-trend-row {
  font-size: 11px;
  border-bottom: 1px solid rgba(0,0,0,0.04);
}
.fin-trend-row:last-child { border-bottom: none; }
.fin-trend-metric {
  font-weight: 600; color: var(--text-secondary);
  white-space: nowrap;
}
.fin-trend-period, .fin-trend-cell {
  text-align: right;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.fin-trend-cell { color: var(--text-primary); }

/* ── 研报预览弹窗 ── */
.preview-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(4px);
}
.preview-modal {
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: 14px;
  width: min(680px, 92vw);
  max-height: 85vh;
  display: flex; flex-direction: column;
  box-shadow: 0 24px 60px rgba(0,0,0,0.3);
  overflow: hidden;
}
.preview-header {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.preview-title {
  flex: 1; font-size: 13px; font-weight: 600; color: var(--text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.preview-close {
  background: none; border: none; cursor: pointer;
  color: var(--text-muted); font-size: 16px; padding: 2px 6px;
  border-radius: 6px; transition: background .2s, color .2s;
}
.preview-link-btn {
  font-size: 12px; font-weight: 500; color: var(--accent);
  text-decoration: none; padding: 3px 10px;
  border: 1px solid var(--accent); border-radius: 6px;
  transition: background .2s;
  white-space: nowrap; flex-shrink: 0;
}
.preview-link-btn:hover { background: rgba(75,169,154,0.12); }
.preview-close:hover { background: var(--bg-card2); color: var(--text-primary); }
.preview-body { flex: 1; overflow-y: auto; padding: 16px; }
.preview-loading {
  display: flex; flex-direction: column; align-items: center;
  gap: 12px; padding: 48px; color: var(--text-muted); font-size: 13px;
}
.spinner {
  width: 28px; height: 28px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.preview-error { text-align: center; padding: 48px; color: var(--text-muted); font-size: 13px; }
.preview-pages { display: flex; flex-direction: column; gap: 20px; }
.preview-page {
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}
.preview-page-label {
  font-size: 11px; font-weight: 700; color: var(--accent2);
  background: rgba(75,169,154,0.08);
  padding: 6px 14px;
  border-bottom: 1px solid var(--border);
}
.preview-text {
  font-size: 13px; line-height: 1.9; color: var(--text-primary);
  white-space: pre-wrap; word-break: break-word;
  padding: 16px 18px;
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
}
</style>
