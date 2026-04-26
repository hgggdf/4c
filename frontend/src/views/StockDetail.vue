<template>
  <div class="stock-detail-page">
    <div v-if="loading" class="empty-state">加载中...</div>

    <template v-else-if="quote">
      <!-- 股票基本信息 -->
      <div class="card">
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
      </div>

      <!-- 风险评估 -->
      <div class="card risk-section">
        <h3 class="section-title">
          <span class="dot dot-red"></span>
          风险与机会
        </h3>

        <div v-if="riskLoading" class="loading-text">加载中...</div>
        <template v-else-if="riskData">
          <div class="risk-overview" :class="'risk-' + riskData.risk_level">
            <div class="risk-badge" :class="'badge-' + riskData.risk_level">
              {{ levelLabel(riskData.risk_level) }}
            </div>
            <div class="risk-counts">
              <span class="cnt-risk">⚠ {{ riskData.risks.length }} 风险</span>
              <span class="cnt-opp">✦ {{ riskData.opportunities.length }} 机会</span>
            </div>
          </div>

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
                 class="signal-empty">暂无明显风险或机会信号</div>
          </div>
        </template>
      </div>

      <!-- 企业诊断 -->
      <div class="card diagnose-section">
        <h3 class="section-title">
          <span class="dot dot-purple"></span>
          企业运营诊断
        </h3>

        <div v-if="diagnoseLoading" class="loading-text">加载中...</div>
        <template v-else-if="diagnoseData">
          <div class="score-card" :class="levelClass">
            <div class="score-main">
              <span class="score-num">{{ diagnoseData.total_score.toFixed(0) }}</span>
              <span class="score-unit">分</span>
            </div>
            <div class="score-info">
              <div class="score-level">{{ diagnoseData.level }}</div>
              <div class="score-year">{{ diagnoseData.year }}年度</div>
            </div>
          </div>

          <div ref="radarRef" class="radar-chart"></div>

          <div class="dimensions">
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

          <div class="insight-row">
            <div class="insight-box strength" v-if="diagnoseData.strengths.length">
              <div class="insight-title">优势</div>
              <ul><li v-for="s in diagnoseData.strengths" :key="s">{{ s }}</li></ul>
            </div>
            <div class="insight-box weakness" v-if="diagnoseData.weaknesses.length">
              <div class="insight-title">劣势</div>
              <ul><li v-for="w in diagnoseData.weaknesses" :key="w">{{ w }}</li></ul>
            </div>
            <div class="insight-box suggestion">
              <div class="insight-title">建议</div>
              <p>{{ diagnoseData.suggestion }}</p>
            </div>
          </div>
        </template>
      </div>
    </template>

    <div v-else class="empty-state">暂无数据</div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { getQuote, getKline } from '../api/stock'
import { getRisks, getDiagnose } from '../api/analysis'
import { getChangeClass } from '../utils/format'
import StockChart from '../components/StockChart.vue'
import * as echarts from 'echarts'

const route = useRoute()
const quote = ref(null)
const kline = ref([])
const loading = ref(false)
const days = 30

const riskData = ref(null)
const riskLoading = ref(false)
const diagnoseData = ref(null)
const diagnoseLoading = ref(false)
const radarRef = ref(null)
let radarChart = null

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

async function loadData() {
  loading.value = true
  try {
    quote.value = await getQuote(route.params.symbol)
    kline.value = await getKline(route.params.symbol, days)
    await Promise.all([loadRiskData(), loadDiagnoseData()])
  } finally {
    loading.value = false
  }
}

async function loadRiskData() {
  riskLoading.value = true
  try {
    const res = await getRisks([route.params.symbol])
    const list = Array.isArray(res) ? res : res?.data || []
    const stockData = list.find(item => item.stock_code === route.params.symbol)
    riskData.value = stockData || list[0] || null
  } catch (e) {
    console.error('风险数据加载失败:', e)
  } finally {
    riskLoading.value = false
  }
}

async function loadDiagnoseData() {
  diagnoseLoading.value = true
  try {
    const res = await getDiagnose(route.params.symbol, '2024')
    diagnoseData.value = res
    await nextTick()
    renderRadar()
  } catch (e) {
    console.error('诊断数据加载失败:', e)
  } finally {
    diagnoseLoading.value = false
  }
}

function renderRadar() {
  if (!radarRef.value || !diagnoseData.value) return
  if (!radarChart) radarChart = echarts.init(radarRef.value)

  const dims = diagnoseData.value.dimensions
  const indicator = dims.map(d => ({ name: d.name, max: 100 }))
  const values = dims.map(d => d.score)

  radarChart.setOption({
    backgroundColor: 'transparent',
    radar: {
      indicator,
      shape: 'polygon',
      splitNumber: 4,
      axisName: { color: '#64748b', fontSize: 13 },
      splitLine: { lineStyle: { color: '#e2e8f0' } },
      splitArea: { areaStyle: { color: ['rgba(248,250,252,0.8)', 'rgba(241,245,249,0.5)'] } },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: values,
        name: diagnoseData.value.stock_name,
        areaStyle: { color: 'rgba(75,169,154,0.2)' },
        lineStyle: { color: '#4ba99a', width: 2 },
        itemStyle: { color: '#4ba99a' },
        label: { show: true, color: '#1e293b', fontSize: 11,
                  formatter: p => p.value.toFixed(0) }
      }]
    }],
    tooltip: { trigger: 'item' }
  })
}

watch(() => route.params.symbol, loadData)
onMounted(loadData)
</script>

<style scoped>
.stock-detail-page { padding: 24px; max-width: 1000px; margin: 0 auto; }
.card { background: var(--bg-panel); border-radius: 16px; padding: 24px; margin-bottom: 24px; border: 1px solid var(--border); box-shadow: 0 2px 12px rgba(0,0,0,0.04); }
.empty-state { text-align: center; padding: 40px; color: var(--text-muted); }
.loading-text { text-align: center; padding: 20px; color: var(--text-muted); }

.section-title { display: flex; align-items: center; gap: 10px; color: var(--text-primary); font-weight: 600; font-size: 18px; margin-bottom: 20px; }
.dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.dot-red { background: var(--red); }
.dot-purple { background: var(--accent2); }

/* 风险评估样式 */
.risk-section { border-left: 4px solid var(--border); }
.risk-overview { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; padding: 16px; background: var(--bg-card); border-radius: 12px; }
.risk-red { border-left-color: var(--red) !important; }
.risk-yellow { border-left-color: var(--gold) !important; }
.risk-green { border-left-color: var(--green) !important; }
.risk-badge { display: inline-block; padding: 6px 16px; border-radius: 20px; font-size: 14px; font-weight: 600; }
.badge-red { background: rgba(239,68,68,.15); color: var(--red); }
.badge-yellow { background: rgba(245,158,11,.15); color: var(--gold); }
.badge-green { background: rgba(34,197,94,.15); color: var(--green); }
.risk-counts { display: flex; gap: 16px; font-size: 14px; font-weight: 500; }
.cnt-risk { color: var(--red); }
.cnt-opp { color: var(--green); }

.signal-list { display: flex; flex-direction: column; gap: 10px; }
.signal-item { display: flex; align-items: center; gap: 12px; background: var(--bg-card); border-radius: 10px; padding: 12px 16px; border-left: 3px solid transparent; border: 1px solid var(--border); border-left-width: 3px; }
.signal-red { border-left-color: var(--red); }
.signal-yellow { border-left-color: var(--gold); }
.signal-green { border-left-color: var(--green); }
.signal-icon { font-size: 16px; flex-shrink: 0; }
.signal-body { flex: 1; }
.signal-name { color: var(--text-primary); font-size: 14px; font-weight: 500; }
.signal-detail { color: var(--text-secondary); font-size: 12px; margin-top: 2px; }
.signal-tag { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; flex-shrink: 0; }
.tag-red { background: rgba(239,68,68,.1); color: var(--red); }
.tag-yellow { background: rgba(245,158,11,.1); color: var(--gold); }
.tag-green { background: rgba(34,197,94,.1); color: var(--green); }
.signal-empty { color: var(--text-muted); font-size: 13px; text-align: center; padding: 16px; }

/* 诊断样式 */
.diagnose-section { border-left: 4px solid var(--accent2); }
.score-card { display: flex; align-items: center; gap: 24px; background: var(--bg-card); border-radius: 12px; padding: 20px 24px; margin-bottom: 20px; }
.level-excellent { border-left-color: var(--green) !important; }
.level-good { border-left-color: var(--accent2) !important; }
.level-fair { border-left-color: var(--gold) !important; }
.level-poor { border-left-color: var(--red) !important; }
.score-num { font-size: 48px; font-weight: 700; color: var(--text-primary); line-height: 1; }
.score-unit { font-size: 18px; color: var(--text-muted); margin-left: 4px; }
.score-level { font-size: 16px; color: var(--text-primary); font-weight: 600; }
.score-year { font-size: 13px; color: var(--text-muted); margin-top: 4px; }

.radar-chart { width: 100%; height: 300px; margin-bottom: 20px; }

.dimensions { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; margin-bottom: 20px; }
.dim-card { background: var(--bg-card); border-radius: 10px; padding: 14px; border: 1px solid var(--border); }
.dim-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
.dim-name { color: var(--text-primary); font-weight: 600; font-size: 14px; }
.dim-score { font-weight: 700; font-size: 14px; }
.score-excellent { color: var(--green); }
.score-good { color: var(--accent2); }
.score-fair { color: var(--gold); }
.score-poor { color: var(--red); }
.dim-bar { height: 6px; background: var(--bg-card2); border-radius: 3px; margin-bottom: 8px; overflow: hidden; }
.dim-bar-fill { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
.dim-bar-fill.score-excellent { background: var(--green); }
.dim-bar-fill.score-good { background: var(--accent2); }
.dim-bar-fill.score-fair { background: var(--gold); }
.dim-bar-fill.score-poor { background: var(--red); }
.dim-metrics { display: flex; flex-wrap: wrap; gap: 6px; }
.metric-tag { background: var(--bg-card2); color: var(--text-secondary); font-size: 11px; padding: 2px 6px; border-radius: 4px; }

.insight-row { display: grid; grid-template-columns: 1fr 1fr 2fr; gap: 14px; }
.insight-box { background: var(--bg-card); border-radius: 10px; padding: 14px; border: 1px solid var(--border); }
.insight-title { font-weight: 600; margin-bottom: 8px; font-size: 13px; }
.strength .insight-title { color: var(--green); }
.weakness .insight-title { color: var(--red); }
.suggestion .insight-title { color: var(--accent2); }
.insight-box ul { margin: 0; padding-left: 16px; }
.insight-box li { color: var(--text-secondary); font-size: 12px; margin-bottom: 4px; }
.insight-box p { color: var(--text-secondary); font-size: 12px; margin: 0; line-height: 1.6; }
</style>
