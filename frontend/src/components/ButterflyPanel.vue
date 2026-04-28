<template>
  <div class="bp-root">

    <!-- 输入区 -->
    <div class="bp-input-area">
      <div class="bp-input-row">
        <input
          v-model="eventText"
          class="bp-input"
          placeholder="输入宏观事件，如「伊朗和美国开战」「美联储大幅加息」"
          :disabled="loading"
          @keydown.enter="run"
        />
        <button class="bp-run-btn" :disabled="loading || !eventText.trim()" @click="run">
          {{ loading ? '分析中…' : '分析' }}
        </button>
      </div>
      <div v-if="statusText" class="bp-status">{{ statusText }}</div>
      <!-- Tab 切换 -->
      <div class="bp-tabs">
        <button class="bp-tab" :class="{ active: activeTab === 'analyze' }" @click="activeTab = 'analyze'">实时分析</button>
        <button class="bp-tab" :class="{ active: activeTab === 'history' }" @click="switchToHistory">历史记录</button>
      </div>
    </div>

    <!-- ═══ 实时分析 Tab ═══ -->
    <template v-if="activeTab === 'analyze'">

    <!-- 空态 -->
    <div v-if="!hasData && !loading" class="bp-empty">
      <div class="bp-empty-icon">🦋</div>
      <div class="bp-empty-title">蝴蝶效应分析</div>
      <div class="bp-empty-desc">输入一个宏观事件，系统将沿「事件 → 行业 → 公司」三层路径推演传导链，识别风险与机会</div>
    </div>

    <!-- 结果区 -->
    <div v-else-if="hasData" class="bp-result">

      <!-- 事件摘要卡 -->
      <div class="bp-event-card">
        <div class="bp-event-header">
          <span class="bp-event-badge" :class="`bp-severity--${eventParsed.severity}`">
            {{ severityLabel(eventParsed.severity) }}
          </span>
          <span class="bp-event-type">{{ eventTypeLabel(eventParsed.event_type) }}</span>
          <span class="bp-event-horizon">{{ horizonLabel(eventParsed.time_horizon) }}</span>
        </div>
        <div class="bp-event-summary">{{ eventParsed.event_summary || eventText }}</div>
        <div v-if="eventParsed.primary_shocks?.length" class="bp-shock-tags">
          <span v-for="s in eventParsed.primary_shocks" :key="s" class="bp-shock-tag">{{ s }}</span>
        </div>
      </div>

      <!-- 传导链流程图 -->
      <div class="bp-section-title">传导链</div>
      <div class="bp-chain">
        <!-- 宏观层 -->
        <div class="bp-chain-level">
          <div class="bp-chain-level-label">宏观冲击</div>
          <div class="bp-chain-nodes">
            <div
              v-for="s in eventParsed.primary_shocks || []"
              :key="s"
              class="bp-chain-node bp-chain-node--macro"
            >{{ s }}</div>
          </div>
        </div>

        <div class="bp-chain-arrow">↓</div>

        <!-- 行业层 -->
        <div class="bp-chain-level">
          <div class="bp-chain-level-label">行业影响</div>
          <div class="bp-chain-nodes">
            <div
              v-for="node in industryNodes"
              :key="node.industry"
              class="bp-chain-node"
              :class="`bp-chain-node--${node.direction}`"
              :title="node.transmission_path"
            >
              <div class="bp-node-name">{{ node.industry }}</div>
              <div class="bp-node-strength">
                <div class="bp-strength-bar">
                  <div class="bp-strength-fill" :style="{ width: `${(node.strength || 0) * 100}%`, background: directionColor(node.direction) }"></div>
                </div>
                <span class="bp-strength-val">{{ Math.round((node.strength || 0) * 100) }}%</span>
              </div>
              <div class="bp-node-dir-badge" :class="`bp-dir--${node.direction}`">{{ directionLabel(node.direction) }}</div>
            </div>
          </div>
        </div>

        <div v-if="companyNodes.length" class="bp-chain-arrow">↓</div>

        <!-- 公司层 -->
        <div v-if="companyNodes.length" class="bp-chain-level">
          <div class="bp-chain-level-label">公司暴露</div>
          <div class="bp-chain-nodes bp-chain-nodes--company">
            <div
              v-for="node in companyNodes.slice(0, 8)"
              :key="node.stock_code"
              class="bp-chain-node bp-chain-node--company"
              :class="`bp-chain-node--${node.direction}`"
            >
              <div class="bp-node-name">{{ node.stock_name }}</div>
              <div class="bp-node-code">{{ node.stock_code }}</div>
              <div class="bp-node-industry-tag">{{ node.industry_level2 }}</div>
              <div class="bp-node-strength">
                <div class="bp-strength-bar">
                  <div class="bp-strength-fill" :style="{ width: `${(node.exposure_score || 0) * 100}%`, background: directionColor(node.direction) }"></div>
                </div>
                <span class="bp-strength-val">{{ Math.round((node.exposure_score || 0) * 100) }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ECharts 行业影响图 -->
      <div v-if="industryNodes.length" class="bp-section-title">行业影响强度</div>
      <div v-if="industryNodes.length" ref="chartRef" class="bp-chart"></div>

      <!-- 风险预警 -->
      <div v-if="riskAlerts.length" class="bp-section-title bp-section-title--risk">⚠ 风险预警</div>
      <div v-if="riskAlerts.length" class="bp-alert-list">
        <div v-for="a in riskAlerts" :key="a.stock_code" class="bp-alert-item bp-alert-item--risk">
          <div class="bp-alert-head">
            <span class="bp-alert-name">{{ a.stock_name }}</span>
            <span class="bp-alert-code">{{ a.stock_code }}</span>
            <span class="bp-alert-score bp-alert-score--risk">暴露度 {{ Math.round((a.exposure_score || 0) * 100) }}%</span>
          </div>
          <div class="bp-alert-industry">{{ a.industry_level2 }}</div>
          <div v-if="a.reason" class="bp-alert-reason">{{ a.reason }}</div>
          <div v-if="a.financial_flags?.length" class="bp-alert-flags">
            <span v-for="f in a.financial_flags" :key="f" class="bp-flag-tag">{{ f }}</span>
          </div>
        </div>
      </div>

      <!-- 机会提示 -->
      <div v-if="opportunities.length" class="bp-section-title bp-section-title--opp">✦ 潜在受益</div>
      <div v-if="opportunities.length" class="bp-alert-list">
        <div v-for="a in opportunities" :key="a.stock_code" class="bp-alert-item bp-alert-item--opp">
          <div class="bp-alert-head">
            <span class="bp-alert-name">{{ a.stock_name }}</span>
            <span class="bp-alert-code">{{ a.stock_code }}</span>
            <span class="bp-alert-score bp-alert-score--opp">受益度 {{ Math.round((a.exposure_score || 0) * 100) }}%</span>
          </div>
          <div class="bp-alert-industry">{{ a.industry_level2 }}</div>
          <div v-if="a.reason" class="bp-alert-reason">{{ a.reason }}</div>
        </div>
      </div>

      <!-- 叙述性报告 -->
      <div v-if="narrative" class="bp-section-title">分析报告</div>
      <div v-if="narrative || loading" class="bp-narrative md-body" v-html="renderedNarrative">
      </div>
      <div v-if="loading && !narrative" class="bp-narrative-loading">
        <span class="bp-dot"></span><span class="bp-dot"></span><span class="bp-dot"></span>
      </div>

    </div>
    </template>

    <!-- ═══ 历史记录 Tab ═══ -->
    <template v-if="activeTab === 'history'">
      <div v-if="historyLoading" class="bp-empty">
        <span class="bp-dot"></span><span class="bp-dot"></span><span class="bp-dot"></span>
      </div>
      <div v-else-if="!historyList.length" class="bp-empty">
        <div class="bp-empty-icon">📋</div>
        <div class="bp-empty-desc">暂无历史分析记录</div>
      </div>
      <div v-else class="bp-result">
        <!-- 筛选栏 -->
        <div class="bp-filter-row">
          <select v-model="historyFilter.severity" class="bp-filter-select" @change="loadHistory">
            <option value="">全部严重程度</option>
            <option value="high">高风险</option>
            <option value="medium">中风险</option>
            <option value="low">低风险</option>
          </select>
          <select v-model="historyFilter.event_type" class="bp-filter-select" @change="loadHistory">
            <option value="">全部类型</option>
            <option value="geopolitical">地缘政治</option>
            <option value="economic">经济</option>
            <option value="policy">政策</option>
            <option value="natural_disaster">自然灾害</option>
            <option value="other">其他</option>
          </select>
        </div>

        <!-- 历史列表 -->
        <div
          v-for="item in historyList"
          :key="item.id"
          class="bp-history-card"
          :class="{ 'bp-history-card--expanded': expandedId === item.id }"
          @click="toggleExpand(item.id)"
        >
          <div class="bp-history-head">
            <span class="bp-event-badge" :class="`bp-severity--${item.severity}`">
              {{ severityLabel(item.severity) }}
            </span>
            <span class="bp-history-title">{{ item.event_text }}</span>
            <span class="bp-history-time">{{ formatTime(item.analyzed_at) }}</span>
          </div>
          <div class="bp-history-shocks">
            <span v-for="s in item.primary_shocks" :key="s" class="bp-shock-tag">{{ s }}</span>
          </div>

          <!-- 展开详情 -->
          <div v-if="expandedId === item.id" class="bp-history-detail" @click.stop>
            <div v-if="item.risk_alerts?.length" class="bp-history-section">
              <div class="bp-section-title bp-section-title--risk">⚠ 风险预警</div>
              <div v-for="a in item.risk_alerts" :key="a.stock_code" class="bp-history-alert">
                {{ a.stock_name }}（{{ a.stock_code }}）暴露度 {{ Math.round((a.exposure_score || 0) * 100) }}%
                <span v-if="a.reason"> — {{ a.reason }}</span>
              </div>
            </div>
            <div v-if="item.opportunity_alerts?.length" class="bp-history-section">
              <div class="bp-section-title bp-section-title--opp">✦ 潜在受益</div>
              <div v-for="a in item.opportunity_alerts" :key="a.stock_code" class="bp-history-alert">
                {{ a.stock_name }}（{{ a.stock_code }}）受益度 {{ Math.round((a.exposure_score || 0) * 100) }}%
              </div>
            </div>
            <div v-if="item.narrative" class="bp-history-section">
              <div class="bp-section-title">分析报告</div>
              <div class="bp-narrative md-body" v-html="renderMd(item.narrative)"></div>
            </div>
          </div>
        </div>
      </div>
    </template>

  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { sendButterflyStream, getButterflyHistory } from '../api/butterfly'

// ── 状态 ──────────────────────────────────────────
const activeTab   = ref('analyze')
const eventText   = ref('')
const loading     = ref(false)
const statusText  = ref('')
const eventParsed = ref({})
const industryNodes  = ref([])
const companyNodes   = ref([])
const riskAlerts     = ref([])
const opportunities  = ref([])
const narrativeRaw   = ref('')

const chartRef = ref(null)
let chartInstance = null

const hasData = computed(() =>
  !!eventParsed.value.event_summary ||
  industryNodes.value.length > 0 ||
  narrativeRaw.value.length > 0
)

const narrative = computed(() => narrativeRaw.value)

const renderedNarrative = computed(() => {
  if (!narrativeRaw.value) return ''
  return DOMPurify.sanitize(marked.parse(narrativeRaw.value))
})

// ── 运行分析 ──────────────────────────────────────
async function run() {
  if (!eventText.value.trim() || loading.value) return

  // 重置
  loading.value     = true
  statusText.value  = ''
  eventParsed.value = {}
  industryNodes.value  = []
  companyNodes.value   = []
  riskAlerts.value     = []
  opportunities.value  = []
  narrativeRaw.value   = ''
  disposeChart()

  try {
    await sendButterflyStream(
      { event: eventText.value.trim() },
      (event) => {
        if (event.type === 'status') {
          statusText.value = event.content || ''
        } else if (event.type === 'event_parsed') {
          eventParsed.value = event.data || {}
        } else if (event.type === 'chain_node') {
          if (event.level === 'industry') {
            industryNodes.value.push(event.data)
            nextTick(renderChart)
          } else if (event.level === 'company') {
            companyNodes.value.push(event.data)
          }
        } else if (event.type === 'risk_alert') {
          riskAlerts.value.push(event.data)
        } else if (event.type === 'opportunity') {
          opportunities.value.push(event.data)
        } else if (event.type === 'narrative_chunk') {
          narrativeRaw.value += event.content || ''
        } else if (event.type === 'done') {
          statusText.value = ''
        } else if (event.type === 'error') {
          statusText.value = `错误：${event.message}`
        }
      }
    )
  } catch (err) {
    statusText.value = `请求失败：${err?.message || err}`
  } finally {
    loading.value = false
    statusText.value = ''
    nextTick(renderChart)
  }
}

// ── ECharts 行业影响图 ────────────────────────────
function renderChart() {
  if (!chartRef.value || !industryNodes.value.length) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  const sorted = [...industryNodes.value].sort((a, b) => (b.strength || 0) - (a.strength || 0))
  const names  = sorted.map(n => n.industry)
  const values = sorted.map(n => Math.round((n.strength || 0) * 100))
  const colors = sorted.map(n => directionColor(n.direction))

  chartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        const node = sorted[p.dataIndex]
        const path = node.transmission_path || ''
        return `<b>${p.name}</b><br/>影响强度：${p.value}%<br/>${path}`
      },
    },
    grid: { left: 80, right: 20, top: 10, bottom: 10, containLabel: false },
    xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%', fontSize: 11 }, splitLine: { lineStyle: { color: 'rgba(0,0,0,0.06)' } } },
    yAxis: { type: 'category', data: names, axisLabel: { fontSize: 12, color: '#555' } },
    series: [{
      type: 'bar',
      data: values.map((v, i) => ({ value: v, itemStyle: { color: colors[i], borderRadius: [0, 4, 4, 0] } })),
      label: { show: true, position: 'right', formatter: '{c}%', fontSize: 11, color: '#555' },
      barMaxWidth: 22,
    }],
  }, true)
}

function disposeChart() {
  chartInstance?.dispose()
  chartInstance = null
}

function resizeChart() { chartInstance?.resize() }

// ── 工具函数 ──────────────────────────────────────
function directionColor(dir) {
  if (dir === 'negative') return '#ef4444'
  if (dir === 'positive') return '#22c55e'
  return '#f59e0b'
}

function directionLabel(dir) {
  if (dir === 'negative') return '负面'
  if (dir === 'positive') return '正面'
  return '混合'
}

function severityLabel(s) {
  return { high: '高风险', medium: '中风险', low: '低风险' }[s] || s || '未知'
}

function eventTypeLabel(t) {
  return {
    geopolitical: '地缘政治', economic: '经济', policy: '政策',
    natural_disaster: '自然灾害', other: '其他',
  }[t] || t || ''
}

function horizonLabel(h) {
  return { short_term: '短期', mid_term: '中期', long_term: '长期' }[h] || h || ''
}

function renderMd(text) {
  if (!text) return ''
  return DOMPurify.sanitize(marked.parse(text))
}

function formatTime(iso) {
  if (!iso) return ''
  return iso.replace('T', ' ').slice(0, 16)
}

// ── 历史记录 ──────────────────────────────────────
const historyList    = ref([])
const historyLoading = ref(false)
const expandedId     = ref(null)
const historyFilter  = ref({ severity: '', event_type: '' })

async function loadHistory() {
  historyLoading.value = true
  try {
    const res = await getButterflyHistory({
      days: 90,
      severity: historyFilter.value.severity || null,
      event_type: historyFilter.value.event_type || null,
    })
    historyList.value = Array.isArray(res) ? res : []
  } catch (err) {
    console.error('[loadHistory]', err)
    historyList.value = []
  } finally {
    historyLoading.value = false
  }
}

function switchToHistory() {
  activeTab.value = 'history'
  if (!historyList.value.length) loadHistory()
}

function toggleExpand(id) {
  expandedId.value = expandedId.value === id ? null : id
}

// ── 生命周期 ──────────────────────────────────────
window.addEventListener('resize', resizeChart)
onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  disposeChart()
})
</script>

<style scoped>
.bp-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--bg-panel);
}

/* ── 输入区 ── */
.bp-input-area {
  flex-shrink: 0;
  padding: 12px 14px 8px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-card);
}
.bp-input-row {
  display: flex;
  gap: 8px;
}
.bp-input {
  flex: 1;
  height: 36px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-panel);
  outline: none;
  transition: border-color .2s;
}
.bp-input:focus { border-color: var(--accent); }
.bp-input:disabled { opacity: 0.6; }
.bp-run-btn {
  height: 36px;
  padding: 0 16px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity .2s;
}
.bp-run-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.bp-run-btn:not(:disabled):hover { opacity: 0.88; }
.bp-status {
  margin-top: 6px;
  font-size: 11px;
  color: var(--accent2);
  display: flex;
  align-items: center;
  gap: 6px;
}

/* ── 空态 ── */
.bp-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 32px 24px;
  text-align: center;
}
.bp-empty-icon { font-size: 40px; opacity: 0.5; }
.bp-empty-title { font-size: 15px; font-weight: 700; color: var(--text-primary); }
.bp-empty-desc { font-size: 12px; color: var(--text-muted); line-height: 1.6; max-width: 280px; }

/* ── 结果区 ── */
.bp-result {
  flex: 1;
  overflow-y: auto;
  padding: 12px 14px 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  scrollbar-width: thin;
  scrollbar-color: rgba(75,169,154,0.2) transparent;
}

/* ── 事件卡 ── */
.bp-event-card {
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg-card);
}
.bp-event-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.bp-event-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 20px;
}
.bp-severity--high   { background: rgba(239,68,68,0.12);  color: #dc2626; border: 1px solid rgba(239,68,68,0.25); }
.bp-severity--medium { background: rgba(245,158,11,0.12); color: #d97706; border: 1px solid rgba(245,158,11,0.25); }
.bp-severity--low    { background: rgba(34,197,94,0.12);  color: #16a34a; border: 1px solid rgba(34,197,94,0.25); }
.bp-event-type, .bp-event-horizon {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-card2);
  padding: 2px 8px;
  border-radius: 20px;
  border: 1px solid var(--border);
}
.bp-event-summary {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.5;
  margin-bottom: 8px;
}
.bp-shock-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.bp-shock-tag {
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 10px;
  background: rgba(75,169,154,0.1);
  color: var(--accent2);
  border: 1px solid rgba(75,169,154,0.2);
}

/* ── 传导链 ── */
.bp-section-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  letter-spacing: 0.04em;
  padding: 2px 0;
}
.bp-section-title--risk { color: #dc2626; }
.bp-section-title--opp  { color: #16a34a; }

.bp-chain {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.bp-chain-arrow {
  text-align: center;
  font-size: 16px;
  color: var(--text-muted);
  line-height: 1;
}
.bp-chain-level {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.bp-chain-level-label {
  font-size: 10px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.bp-chain-nodes {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.bp-chain-nodes--company {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
}

/* 节点卡片 */
.bp-chain-node {
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--bg-card);
  font-size: 12px;
  min-width: 90px;
}
.bp-chain-node--macro {
  background: rgba(99,102,241,0.07);
  border-color: rgba(99,102,241,0.2);
  color: #4f46e5;
  font-weight: 600;
  font-size: 11px;
  padding: 5px 10px;
}
.bp-chain-node--negative { border-left: 3px solid #ef4444; }
.bp-chain-node--positive { border-left: 3px solid #22c55e; }
.bp-chain-node--mixed    { border-left: 3px solid #f59e0b; }

.bp-node-name {
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
  font-size: 12px;
}
.bp-node-code {
  font-size: 10px;
  color: var(--text-muted);
  margin-bottom: 2px;
}
.bp-node-industry-tag {
  font-size: 10px;
  color: var(--accent2);
  margin-bottom: 4px;
}
.bp-node-strength {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 4px;
}
.bp-strength-bar {
  flex: 1;
  height: 4px;
  background: var(--bg-card2);
  border-radius: 2px;
  overflow: hidden;
}
.bp-strength-fill {
  height: 100%;
  border-radius: 2px;
  transition: width .4s ease;
}
.bp-strength-val {
  font-size: 10px;
  color: var(--text-muted);
  min-width: 28px;
  text-align: right;
}
.bp-node-dir-badge {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 8px;
  margin-top: 4px;
}
.bp-dir--negative { background: rgba(239,68,68,0.1);  color: #dc2626; }
.bp-dir--positive { background: rgba(34,197,94,0.1);  color: #16a34a; }
.bp-dir--mixed    { background: rgba(245,158,11,0.1); color: #d97706; }

/* ── ECharts ── */
.bp-chart {
  width: 100%;
  height: 220px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg-card);
  overflow: hidden;
}

/* ── 预警列表 ── */
.bp-alert-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.bp-alert-item {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--bg-card);
}
.bp-alert-item--risk { border-left: 3px solid #ef4444; }
.bp-alert-item--opp  { border-left: 3px solid #22c55e; }
.bp-alert-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}
.bp-alert-name { font-size: 13px; font-weight: 700; color: var(--text-primary); }
.bp-alert-code { font-size: 11px; color: var(--text-muted); }
.bp-alert-score {
  margin-left: auto;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 10px;
}
.bp-alert-score--risk { background: rgba(239,68,68,0.1);  color: #dc2626; }
.bp-alert-score--opp  { background: rgba(34,197,94,0.1);  color: #16a34a; }
.bp-alert-industry { font-size: 11px; color: var(--accent2); margin-bottom: 4px; }
.bp-alert-reason { font-size: 12px; color: var(--text-secondary); line-height: 1.5; }
.bp-alert-flags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 5px; }
.bp-flag-tag {
  font-size: 10px;
  padding: 1px 7px;
  border-radius: 8px;
  background: rgba(245,158,11,0.1);
  color: #d97706;
  border: 1px solid rgba(245,158,11,0.2);
}

/* ── 叙述报告 ── */
.bp-narrative {
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg-card);
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-primary);
}
.bp-narrative :deep(h1),
.bp-narrative :deep(h2),
.bp-narrative :deep(h3) { font-weight: 700; margin: 0.7em 0 0.3em; }
.bp-narrative :deep(h2) { font-size: 1.05em; }
.bp-narrative :deep(h3) { font-size: 1em; }
.bp-narrative :deep(p)  { margin: 0.4em 0; }
.bp-narrative :deep(ul),
.bp-narrative :deep(ol) { padding-left: 1.4em; margin: 0.4em 0; }
.bp-narrative :deep(li) { margin: 0.15em 0; }
.bp-narrative :deep(strong) { font-weight: 700; }
.bp-narrative :deep(blockquote) {
  border-left: 3px solid var(--accent2);
  margin: 0.5em 0;
  padding: 4px 12px;
  color: var(--text-secondary);
  background: rgba(75,169,154,0.05);
  border-radius: 0 6px 6px 0;
}

.bp-narrative-loading {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 12px 14px;
}
.bp-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--accent);
  display: inline-block;
  animation: bpDot 1.2s infinite ease-in-out;
}
.bp-dot:nth-child(2) { animation-delay: .2s; }
.bp-dot:nth-child(3) { animation-delay: .4s; }
@keyframes bpDot {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40%           { transform: scale(1);   opacity: 1; }
}

/* markdown body 复用 */
.md-body { white-space: normal; }

/* ── Tabs ── */
.bp-tabs {
  display: flex;
  gap: 0;
  margin-top: 8px;
  border-bottom: 1px solid var(--border);
}
.bp-tab {
  flex: 1;
  padding: 6px 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: color .2s, border-color .2s;
}
.bp-tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}
.bp-tab:hover:not(.active) { color: var(--text-primary); }

/* ── 筛选栏 ── */
.bp-filter-row {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
}
.bp-filter-select {
  flex: 1;
  height: 30px;
  padding: 0 8px;
  font-size: 11px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-primary);
  outline: none;
  cursor: pointer;
}

/* ── 历史卡片 ── */
.bp-history-card {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg-card);
  cursor: pointer;
  transition: border-color .2s, box-shadow .2s;
}
.bp-history-card:hover { border-color: var(--accent); }
.bp-history-card--expanded { border-color: var(--accent); box-shadow: 0 1px 6px rgba(75,169,154,0.1); }
.bp-history-head {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.bp-history-title {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bp-history-time {
  font-size: 10px;
  color: var(--text-muted);
  white-space: nowrap;
}
.bp-history-shocks {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}
.bp-history-detail {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
  cursor: default;
}
.bp-history-section { margin-bottom: 8px; }
.bp-history-alert {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  padding-left: 8px;
}
</style>
