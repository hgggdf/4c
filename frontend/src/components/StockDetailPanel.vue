<template>
  <div class="detail-panel">
    <!-- Header -->
    <div class="detail-header">
      <button class="back-btn" @click="$emit('back')">
        <span class="back-arrow">‹</span>
        <span class="back-text">返回</span>
      </button>
      <div class="detail-title-row">
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
    <div class="content-scroll" style="position:relative;">

      <!-- 覆盖式过场遮罩（竖条绿色系） -->
      <div class="tab-cover" :class="coverClass">
        <div class="cover-bar" v-for="i in 8" :key="i"
             :style="{ animationDelay: `${(i - 1) * 0.048}s` }"></div>
      </div>

      <!-- 行情数据 Tab -->
      <div v-if="activeTab === 'data'" key="data">
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

      <!-- 风险评估 Tab -->
      <div v-else-if="activeTab === 'risk'" key="risk">
        <div v-if="riskLoading" class="empty-state">扫描中…</div>
        <div v-else-if="riskError" class="error-state">{{ riskError }}</div>
        <template v-else-if="riskData">
          <!-- 风险总览 -->
          <div class="risk-overview" :class="'risk-border-' + riskData.risk_level">
            <div class="risk-badge" :class="'badge-' + riskData.risk_level">
              {{ levelLabel(riskData.risk_level) }}
            </div>
            <div class="risk-counts">
              <span class="cnt-risk">⚠ {{ riskData.risks.length }} 风险</span>
              <span class="cnt-opp">✦ {{ riskData.opportunities.length }} 机会</span>
            </div>
          </div>

          <!-- 信号列表 -->
          <div class="signal-list">
            <div v-for="r in riskData.risks" :key="r.signal"
                 class="signal-item" :class="'signal-' + r.level">
              <span class="signal-icon">{{ r.level === 'red' ? '🔴' : '🟡' }}</span>
              <div class="signal-body">
                <div class="signal-name">{{ r.signal }}</div>
                <div class="signal-detail">{{ r.detail }}</div>
              </div>
              <span class="signal-tag" :class="'tag-' + r.level">
                {{ r.level === 'red' ? '高风险' : '关注' }}
              </span>
            </div>
            <div v-for="o in riskData.opportunities" :key="o.signal"
                 class="signal-item signal-green">
              <span class="signal-icon">🟢</span>
              <div class="signal-body">
                <div class="signal-name">{{ o.signal }}</div>
                <div class="signal-detail">{{ o.detail }}</div>
              </div>
              <span class="signal-tag tag-green">机会</span>
            </div>
            <div v-if="!riskData.risks.length && !riskData.opportunities.length"
                 class="empty-state">暂无明显风险或机会信号</div>
          </div>
        </template>
        <div v-else class="empty-state">暂无风险数据</div>
      </div>

      <!-- 企业诊断 Tab -->
      <div v-else-if="activeTab === 'diagnose'" key="diagnose">
        <div v-if="diagnoseLoading" class="empty-state">分析中…</div>
        <div v-else-if="diagnoseError" class="error-state">{{ diagnoseError }}</div>
        <template v-else-if="diagnoseData">
          <!-- 总分卡片 -->
          <div class="score-card" :class="levelClass">
            <div class="score-main">
              <span class="score-num">{{ diagnoseData.total_score.toFixed(0) }}</span>
              <span class="score-unit">分</span>
            </div>
            <div class="score-info">
              <div class="score-level-badge" :class="levelClass">{{ diagnoseData.level }}</div>
              <div class="score-year">{{ diagnoseData.year }}年度综合评分</div>
            </div>
          </div>

          <!-- 雷达图 -->
          <div ref="radarRef" class="radar-chart"></div>

          <!-- 维度卡片 -->
          <div class="section-title" style="margin-top:4px;">各维度评分</div>
          <div class="dim-list">
            <div v-for="dim in diagnoseData.dimensions" :key="dim.name" class="dim-card">
              <div class="dim-header">
                <span class="dim-name">{{ dim.name }}</span>
                <span class="dim-score" :class="scoreClass(dim.score)">{{ dim.score.toFixed(0) }}分</span>
              </div>
              <div class="dim-bar">
                <div class="dim-bar-fill" :style="{ width: dim.score + '%' }" :class="scoreClass(dim.score)"></div>
              </div>
              <div class="dim-metrics">
                <span v-for="(v, k) in dim.metrics" :key="k" class="metric-tag">
                  {{ k }}: {{ v.value }}{{ v.unit }}
                </span>
              </div>
            </div>
          </div>

          <!-- 优劣势建议 -->
          <div class="insight-row">
            <div class="insight-box strength" v-if="diagnoseData.strengths.length">
              <div class="insight-title">✅ 优势</div>
              <ul><li v-for="s in diagnoseData.strengths" :key="s">{{ s }}</li></ul>
            </div>
            <div class="insight-box weakness" v-if="diagnoseData.weaknesses.length">
              <div class="insight-title">⚠️ 劣势</div>
              <ul><li v-for="w in diagnoseData.weaknesses" :key="w">{{ w }}</li></ul>
            </div>
          </div>
          <div class="insight-box suggestion" v-if="diagnoseData.suggestion" style="margin-top:10px;">
            <div class="insight-title">💡 建议</div>
            <p>{{ diagnoseData.suggestion }}</p>
          </div>
        </template>
        <div v-else class="empty-state">暂无诊断数据</div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getKline, getStockMetrics, getReports } from '../api/stock'
import { getRisks, getDiagnose } from '../api/analysis'

const props = defineProps({
  stock: { type: Object, required: true }
})
defineEmits(['back'])

const activeTab = ref('data')
const tabs = [
  { key: 'data',     label: '数据', icon: '📊' },
  { key: 'risk',     label: '风险', icon: '⚠️' },
  { key: 'diagnose', label: '诊断', icon: '🔬' },
  { key: 'report',   label: '研报', icon: '📄' },
]

// ── 覆盖式过场动画 ────────────────────────────────
const coverClass = ref('')

function switchTab(key) {
  if (key === activeTab.value) return
  coverClass.value = 'cover-active'
  // 在竖条全部覆盖屏幕的中间时刻切换内容（40% 处 = 0.8s * 0.4 = 320ms，加上最后一根延迟 0.336s → 约 400ms）
  setTimeout(() => {
    activeTab.value = key
    if (key === 'risk') loadRiskData()
    if (key === 'diagnose') loadDiagnoseData()
  }, 400)
  // 整个动画结束后清除 class（0.8s + 最后一根延迟 0.336s ≈ 1040ms）
  setTimeout(() => { coverClass.value = '' }, 1040)
}

<<<<<<< Updated upstream
// ── 行情数据 ──────────────────────────────────────
const chartRef = ref(null)
let chartInst = null
const metrics = ref({})
const reports = ref([])
const loading = ref(false)

// ── 风险评估 ──────────────────────────────────────
const riskData = ref(null)
const riskLoading = ref(false)
const riskError = ref('')

// ── 企业诊断 ──────────────────────────────────────
const diagnoseData = ref(null)
const diagnoseLoading = ref(false)
const diagnoseError = ref('')
const radarRef = ref(null)
let radarChart = null

// ── 计算属性 ──────────────────────────────────────
const levelClass = computed(() => {
  if (!diagnoseData.value) return ''
  const map = { '优秀': 'level-excellent', '良好': 'level-good', '一般': 'level-fair', '较差': 'level-poor' }
  return map[diagnoseData.value.level] || ''
})

function levelLabel(level) {
  return { red: '高风险', yellow: '需关注', green: '健康' }[level] || level
}

function scoreClass(score) {
  if (score >= 80) return 'score-excellent'
  if (score >= 65) return 'score-good'
  if (score >= 45) return 'score-fair'
  return 'score-poor'
}
=======
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
const metrics  = ref({})
const reports  = ref([])
const concepts = ref({ aliases: [], industries: [] })
const events   = ref([])
const loading  = ref(false)
const companyProfile = ref(null)
const financialSummary = ref(null)
>>>>>>> Stashed changes

// ── 数据加载 ──────────────────────────────────────
async function loadMarketData() {
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
<<<<<<< Updated upstream
=======
    lastKline = kline
    loadCompanyProfile()
    loadFinancialSummary()
>>>>>>> Stashed changes
  } finally {
    loading.value = false
  }
}

async function loadRiskData() {
  if (riskData.value) return
  riskLoading.value = true
  riskError.value = ''
  try {
    const res = await getRisks(props.stock.symbol)
    const found = res.data.find(item => item.stock_code === props.stock.symbol)
    riskData.value = found || null
    if (!found) riskError.value = '未找到该股票的风险数据'
  } catch (e) {
    riskError.value = '加载失败：' + (e.response?.data?.detail || e.message)
  } finally {
    riskLoading.value = false
  }
}

async function loadDiagnoseData() {
  if (diagnoseData.value) return
  diagnoseLoading.value = true
  diagnoseError.value = ''
  try {
    const res = await getDiagnose(props.stock.symbol, '2024')
    diagnoseData.value = res
    await nextTick()
    renderRadar()
  } catch (e) {
    diagnoseError.value = '加载失败：' + (e.response?.data?.detail || e.message)
  } finally {
    diagnoseLoading.value = false
  }
}

// 切换 tab 时按需加载（由 switchTab 直接调用，此 watch 仅保留兜底）

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

function renderRadar() {
  if (!radarRef.value || !diagnoseData.value) return
  if (!radarChart) radarChart = echarts.init(radarRef.value)

  const dims = diagnoseData.value.dimensions
  radarChart.setOption({
    backgroundColor: 'transparent',
    radar: {
      indicator: dims.map(d => ({ name: d.name, max: 100 })),
      shape: 'polygon', splitNumber: 4,
      axisName: { color: '#64748b', fontSize: 11 },
      splitLine: { lineStyle: { color: '#e2e8f0' } },
      splitArea: { areaStyle: { color: ['rgba(248,250,252,0.8)', 'rgba(241,245,249,0.5)'] } },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: dims.map(d => d.score),
        name: diagnoseData.value.stock_name,
        areaStyle: { color: 'rgba(75,169,154,0.2)' },
        lineStyle: { color: '#4ba99a', width: 2 },
        itemStyle: { color: '#4ba99a' },
        label: { show: true, color: '#1e293b', fontSize: 10, formatter: p => p.value.toFixed(0) }
      }]
    }],
    tooltip: { trigger: 'item' }
  })
}

// ── 工具函数 ──────────────────────────────────────
function getChangePercent(stock) {
  return Number(stock?.change_pct ?? stock?.change_percent ?? 0)
}

function formatReportMeta(report) {
  return [report.broker, report.industry, report.date].filter(Boolean).join(' · ')
}

function onResize() {
  chartInst?.resize()
  radarChart?.resize()
}

watch(() => props.stock, () => {
  riskData.value = null
  diagnoseData.value = null
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
  radarChart?.dispose()
})
</script>

<style scoped>
.detail-panel {
  display: flex; flex-direction: column; height: 100%;
  background: var(--bg-panel);
}

.detail-header {
  padding: 12px 16px 10px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg-card2);
  border: 1px solid var(--border);
  border-radius: 24px;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 14px; font-weight: 500;
  padding: 7px 18px 7px 12px;
  margin-bottom: 12px;
  transition: background .2s, border-color .2s, color .2s, transform .15s;
}
.back-btn:hover {
  background: rgba(75,169,154,0.1);
  border-color: var(--accent);
  color: var(--accent);
  transform: translateX(-2px);
}
.back-arrow {
  font-size: 22px; line-height: 1;
  font-weight: 300; margin-top: -1px;
}
.back-text { font-size: 14px; }

.detail-title-row { display: flex; align-items: baseline; gap: 6px; }
.detail-name { font-size: 17px; font-weight: 700; color: var(--text-primary); }
.detail-code {
  font-size: 11px; color: var(--text-muted);
  background: var(--bg-card2);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1px 5px;
}
.detail-price-row { margin-top: 6px; display: flex; align-items: baseline; gap: 10px; }
.detail-price { font-size: 26px; font-weight: 800; }
.detail-change { font-size: 14px; font-weight: 500; }
.red   { color: var(--red); }
.green { color: var(--green); }

.tab-bar {
  display: flex;
  flex-shrink: 0;
  width: 100%;
  margin: 0;
  padding: 0;
  gap: 0;
  min-height: 120px;
  border-bottom: 2px solid var(--border);
  background: var(--bg-card);
}

.tab-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 20px;
  margin: 0;
  background: none;
  border: none;
  border-right: 1px solid var(--border);
  border-bottom: 3px solid transparent;
  color: var(--text-muted);
  font-weight: 500;
  font-size: 14px;
  cursor: pointer;
  transition: all .2s;
  outline: none;
}

.tab-btn:last-child {
  border-right: none;
}

.tab-btn:hover {
  color: var(--text-primary);
  background: rgba(75, 169, 154, 0.08);
}

.tab-btn.active {
  color: var(--accent);
  background: rgba(75, 169, 154, 0.12);
  border-bottom-color: var(--accent);
  font-weight: 600;
}

.tab-icon {
  font-size: 36px;
  line-height: 1;
  display: block;
}

.tab-label {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-align: center;
}

.content-scroll { flex: 1; overflow-y: auto; padding: 16px; }

/* 行情 */
.chart-container { height: 260px; margin-bottom: 16px; }
.section-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 10px; }
.metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 16px; }
.metric-card { background: var(--bg-card); border-radius: 8px; padding: 10px 12px; border: 1px solid var(--border); }
.metric-label { font-size: 11px; color: var(--text-muted); margin-bottom: 4px; }
.metric-value { font-size: 14px; font-weight: 600; color: var(--text-primary); }

/* 研报 */
.report-list { display: flex; flex-direction: column; gap: 10px; }
.report-item { background: var(--bg-card); border-radius: 10px; padding: 12px; border: 1px solid var(--border); position: relative; }
.report-title { font-size: 13px; font-weight: 500; color: var(--text-primary); margin-bottom: 6px; padding-right: 60px; }
.report-meta { font-size: 11px; color: var(--text-muted); }
.report-rating { position: absolute; top: 12px; right: 12px; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
.rating-buy  { background: rgba(34,197,94,.12);  color: var(--green); }
.rating-hold { background: rgba(245,158,11,.12); color: var(--gold); }
.rating-sell { background: rgba(239,68,68,.12);  color: var(--red); }

/* 风险评估 */
.risk-overview {
  display: flex; align-items: center; gap: 14px;
  background: var(--bg-card); border-radius: 12px; padding: 14px 16px;
  margin-bottom: 14px; border-left: 4px solid var(--border);
}
.risk-border-red    { border-left-color: var(--red) !important; }
.risk-border-yellow { border-left-color: var(--gold) !important; }
.risk-border-green  { border-left-color: var(--green) !important; }
.risk-badge { padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; }
.badge-red    { background: rgba(239,68,68,.15);  color: var(--red); }
.badge-yellow { background: rgba(245,158,11,.15); color: var(--gold); }
.badge-green  { background: rgba(34,197,94,.15);  color: var(--green); }
.risk-counts { display: flex; gap: 14px; font-size: 13px; font-weight: 500; }
.cnt-risk { color: var(--red); }
.cnt-opp  { color: var(--green); }

.signal-list { display: flex; flex-direction: column; gap: 8px; }
.signal-item {
  display: flex; align-items: center; gap: 10px;
  background: var(--bg-card); border-radius: 8px; padding: 10px 12px;
  border: 1px solid var(--border); border-left: 3px solid transparent;
}
.signal-red    { border-left-color: var(--red); }
.signal-yellow { border-left-color: var(--gold); }
.signal-green  { border-left-color: var(--green); }
.signal-icon { font-size: 14px; flex-shrink: 0; }
.signal-body { flex: 1; min-width: 0; }
.signal-name   { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.signal-detail { font-size: 11px; color: var(--text-secondary); margin-top: 2px; }
.signal-tag { font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 4px; flex-shrink: 0; }
.tag-red    { background: rgba(239,68,68,.1);  color: var(--red); }
.tag-yellow { background: rgba(245,158,11,.1); color: var(--gold); }
.tag-green  { background: rgba(34,197,94,.1);  color: var(--green); }

/* 企业诊断 */
.score-card {
  display: flex; align-items: center; gap: 20px;
  background: var(--bg-card); border-radius: 12px; padding: 16px 20px;
  margin-bottom: 16px; border-left: 4px solid var(--accent2);
}
.level-excellent { border-left-color: var(--green) !important; }
.level-good      { border-left-color: var(--accent2) !important; }
.level-fair      { border-left-color: var(--gold) !important; }
.level-poor      { border-left-color: var(--red) !important; }
.score-num  { font-size: 44px; font-weight: 700; color: var(--text-primary); line-height: 1; }
.score-unit { font-size: 16px; color: var(--text-muted); margin-left: 3px; }
.score-level-badge {
  display: inline-block; padding: 3px 10px; border-radius: 20px;
  font-size: 13px; font-weight: 600; margin-bottom: 4px;
}
.level-excellent .score-level-badge { background: rgba(34,197,94,.15);  color: var(--green); }
.level-good      .score-level-badge { background: rgba(75,169,154,.15); color: var(--accent2); }
.level-fair      .score-level-badge { background: rgba(245,158,11,.15);  color: var(--gold); }
.level-poor      .score-level-badge { background: rgba(239,68,68,.15);   color: var(--red); }
.score-year { font-size: 12px; color: var(--text-muted); }

.radar-chart { width: 100%; height: 240px; margin-bottom: 8px; }

.dim-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 14px; }
.dim-card { background: var(--bg-card); border-radius: 8px; padding: 12px; border: 1px solid var(--border); }
.dim-header { display: flex; justify-content: space-between; margin-bottom: 6px; }
.dim-name  { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.dim-score { font-size: 13px; font-weight: 700; }
.score-excellent { color: var(--green); }
.score-good      { color: var(--accent2); }
.score-fair      { color: var(--gold); }
.score-poor      { color: var(--red); }
.dim-bar { height: 5px; background: var(--bg-card2); border-radius: 3px; margin-bottom: 8px; overflow: hidden; }
.dim-bar-fill { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
.dim-bar-fill.score-excellent { background: var(--green); }
.dim-bar-fill.score-good      { background: var(--accent2); }
.dim-bar-fill.score-fair      { background: var(--gold); }
.dim-bar-fill.score-poor      { background: var(--red); }
.dim-metrics { display: flex; flex-wrap: wrap; gap: 4px; }
.metric-tag { background: var(--bg-card2); color: var(--text-secondary); font-size: 10px; padding: 2px 6px; border-radius: 4px; }

.insight-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.insight-box { background: var(--bg-card); border-radius: 8px; padding: 12px; border: 1px solid var(--border); }
.insight-title { font-weight: 600; margin-bottom: 8px; font-size: 12px; }
.strength .insight-title { color: var(--green); }
.weakness .insight-title { color: var(--red); }
.suggestion .insight-title { color: var(--accent2); }
.insight-box ul { margin: 0; padding-left: 14px; }
.insight-box li { color: var(--text-secondary); font-size: 11px; margin-bottom: 3px; }
.insight-box p  { color: var(--text-secondary); font-size: 11px; margin: 0; line-height: 1.6; }

.empty-state { text-align: center; padding: 32px; color: var(--text-muted); font-size: 13px; }
.error-state { text-align: center; padding: 20px; color: var(--red); font-size: 13px; }

/* 覆盖式过场遮罩 — 竖条版 */
.tab-cover {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 100%;
  z-index: 10;
  pointer-events: none;
  display: none;
  flex-direction: row;
  overflow: hidden;
}
.tab-cover.cover-active { 
  display: flex;
  pointer-events: all;
}

/* 8 根竖条，绿色系从深到浅 */
.cover-bar {
  flex: 1;
  transform: translateY(110%);
}
.tab-cover.cover-active .cover-bar {
  animation: barFull 0.8s cubic-bezier(0.76, 0, 0.24, 1) forwards;
}

/* 每根竖条独立颜色 */
.cover-bar:nth-child(1) { background: #2d6e63; }
.cover-bar:nth-child(2) { background: #357a6e; }
.cover-bar:nth-child(3) { background: #3d8878; }
.cover-bar:nth-child(4) { background: #4ba99a; }
.cover-bar:nth-child(5) { background: #5bbcad; }
.cover-bar:nth-child(6) { background: #6ecbbf; }
.cover-bar:nth-child(7) { background: #8dd8ce; }
.cover-bar:nth-child(8) { background: #aee6e0; }

/* 单根竖条完整生命周期：从下滑入 → 停住 → 向下滑出 */
@keyframes barFull {
  0%   { transform: translateY(110%); }
  40%  { transform: translateY(0%); }
  60%  { transform: translateY(0%); }
  100% { transform: translateY(110%); }
}
</style>
