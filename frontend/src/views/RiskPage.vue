<template>
  <div class="risk-page">
    <div class="page-header">
      <h2>风险与机会洞察</h2>
      <button class="refresh-btn" @click="loadData" :disabled="loading">
        {{ loading ? '刷新中...' : '刷新' }}
      </button>
    </div>

    <div v-if="loading" class="loading">扫描中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <template v-else>
      <!-- 总览卡片 -->
      <div class="overview-row">
        <div class="overview-card" v-for="item in data" :key="item.stock_code"
             :class="'card-' + item.risk_level">
          <div class="ov-name">{{ item.stock_name }}</div>
          <div class="ov-code">{{ item.stock_code }}</div>
          <div class="ov-badge" :class="'badge-' + item.risk_level">
            {{ levelLabel(item.risk_level) }}
          </div>
          <div class="ov-counts">
            <span class="cnt-risk">⚠ {{ item.risks.length }} 风险</span>
            <span class="cnt-opp">✦ {{ item.opportunities.length }} 机会</span>
          </div>
        </div>
      </div>

      <!-- 详细信号列表 -->
      <div class="signal-section" v-for="item in data" :key="'detail-' + item.stock_code">
        <div class="section-title">
          <span class="dot" :class="'dot-' + item.risk_level"></span>
          {{ item.stock_name }}（{{ item.stock_code }}）
        </div>

        <div class="signal-list">
          <div v-for="r in item.risks" :key="r.signal"
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

          <div v-for="o in item.opportunities" :key="o.signal"
               class="signal-item signal-green">
            <span class="signal-icon">🟢</span>
            <div class="signal-body">
              <div class="signal-name">{{ o.signal }}</div>
              <div class="signal-detail">{{ o.detail }}</div>
            </div>
            <span class="signal-tag tag-green">机会</span>
          </div>

          <div v-if="!item.risks.length && !item.opportunities.length"
               class="signal-empty">暂无明显风险或机会信号</div>
        </div>
      </div>

      <!-- 横向对比图 -->
      <div class="compare-section">
        <div class="section-title">
          <span class="dot dot-blue"></span>
          三家公司关键指标对比
        </div>
        <div class="metric-tabs">
          <button v-for="m in metrics" :key="m"
                  :class="['tab-btn', { active: activeMetric === m }]"
                  @click="switchMetric(m)">{{ m }}</button>
        </div>
        <div ref="barRef" class="bar-chart"></div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getRisks, getCompare } from '../api/analysis'

const data = ref([])
const loading = ref(false)
const error = ref('')
const barRef = ref(null)
let barChart = null

const metrics = ['毛利率', 'ROE', '资产负债率', '净利润', '营业总收入']
const activeMetric = ref('毛利率')

function levelLabel(level) {
  return { red: '高风险', yellow: '需关注', green: '健康' }[level] || level
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const res = await getRisks()
    data.value = res.data.data
    await nextTick()
    renderBar(activeMetric.value)
  } catch (e) {
    error.value = '加载失败：' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

async function switchMetric(m) {
  activeMetric.value = m
  await renderBar(m)
}

async function renderBar(metric) {
  if (!barRef.value) return
  if (!barChart) barChart = echarts.init(barRef.value)

  try {
    const res = await getCompare(metric)
    const items = res.data.data
    const names = items.map(i => i.stock_name)
    const values = items.map(i => i.value ?? 0)
    const unit = items[0]?.unit || ''

    barChart.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', formatter: p => `${p[0].name}<br/>${metric}: ${p[0].value}${unit}` },
      xAxis: { type: 'category', data: names, axisLabel: { color: '#94a3b8' }, axisLine: { lineStyle: { color: '#334155' } } },
      yAxis: { type: 'value', axisLabel: { color: '#94a3b8', formatter: v => v + unit }, splitLine: { lineStyle: { color: '#1e293b' } } },
      series: [{
        type: 'bar', data: values, barMaxWidth: 60,
        itemStyle: {
          color: p => ['#6366f1', '#22c55e', '#f59e0b'][p.dataIndex % 3],
          borderRadius: [6, 6, 0, 0]
        },
        label: { show: true, position: 'top', color: '#e2e8f0', formatter: p => p.value + unit }
      }],
      grid: { left: 40, right: 20, top: 30, bottom: 40 }
    })
  } catch {}
}

onMounted(loadData)
</script>

<style scoped>
.risk-page { padding: 24px; max-width: 960px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-header h2 { color: #e2e8f0; font-size: 20px; margin: 0; }
.refresh-btn {
  background: #1e293b; color: #94a3b8; border: 1px solid #334155;
  padding: 6px 16px; border-radius: 8px; cursor: pointer;
}
.refresh-btn:hover { color: #e2e8f0; }
.loading, .error { text-align: center; padding: 40px; color: #94a3b8; }
.error { color: #f87171; }

.overview-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 28px; }
.overview-card {
  background: #1e293b; border-radius: 14px; padding: 20px;
  border-top: 4px solid #334155; transition: transform .2s;
}
.overview-card:hover { transform: translateY(-2px); }
.card-red    { border-top-color: #ef4444; }
.card-yellow { border-top-color: #f59e0b; }
.card-green  { border-top-color: #22c55e; }
.ov-name { color: #e2e8f0; font-weight: 600; font-size: 16px; }
.ov-code { color: #64748b; font-size: 13px; margin-bottom: 12px; }
.ov-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-bottom: 12px; }
.badge-red    { background: rgba(239,68,68,.15);  color: #ef4444; }
.badge-yellow { background: rgba(245,158,11,.15); color: #f59e0b; }
.badge-green  { background: rgba(34,197,94,.15);  color: #22c55e; }
.ov-counts { display: flex; gap: 12px; font-size: 13px; }
.cnt-risk { color: #f87171; }
.cnt-opp  { color: #4ade80; }

.signal-section { background: #1e293b; border-radius: 14px; padding: 20px; margin-bottom: 20px; }
.section-title { display: flex; align-items: center; gap: 10px; color: #e2e8f0; font-weight: 600; font-size: 15px; margin-bottom: 16px; }
.dot { width: 10px; height: 10px; border-radius: 50%; }
.dot-red    { background: #ef4444; }
.dot-yellow { background: #f59e0b; }
.dot-green  { background: #22c55e; }
.dot-blue   { background: #6366f1; }

.signal-list { display: flex; flex-direction: column; gap: 10px; }
.signal-item {
  display: flex; align-items: center; gap: 12px;
  background: #0f172a; border-radius: 10px; padding: 12px 16px;
  border-left: 3px solid transparent;
}
.signal-red    { border-left-color: #ef4444; }
.signal-yellow { border-left-color: #f59e0b; }
.signal-green  { border-left-color: #22c55e; }
.signal-icon { font-size: 16px; flex-shrink: 0; }
.signal-body { flex: 1; }
.signal-name   { color: #e2e8f0; font-size: 14px; font-weight: 500; }
.signal-detail { color: #64748b; font-size: 12px; margin-top: 2px; }
.signal-tag { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; flex-shrink: 0; }
.tag-red    { background: rgba(239,68,68,.15);  color: #ef4444; }
.tag-yellow { background: rgba(245,158,11,.15); color: #f59e0b; }
.tag-green  { background: rgba(34,197,94,.15);  color: #22c55e; }
.signal-empty { color: #64748b; font-size: 13px; text-align: center; padding: 16px; }

.compare-section { background: #1e293b; border-radius: 14px; padding: 20px; margin-top: 8px; }
.metric-tabs { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.tab-btn {
  background: #0f172a; color: #94a3b8; border: 1px solid #334155;
  padding: 5px 14px; border-radius: 20px; cursor: pointer; font-size: 13px;
}
.tab-btn.active { background: #6366f1; color: #fff; border-color: #6366f1; }
.bar-chart { width: 100%; height: 260px; }
</style>
