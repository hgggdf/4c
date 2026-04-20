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
    data.value = res.data
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
    const items = res.data
    const names = items.map(i => i.stock_name)
    const values = items.map(i => i.value ?? 0)
    const unit = items[0]?.unit || ''

    barChart.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', formatter: p => `${p[0].name}<br/>${metric}: ${p[0].value}${unit}` },
      xAxis: { type: 'category', data: names, axisLabel: { color: '#64748b' }, axisLine: { lineStyle: { color: '#e2e8f0' } } },
      yAxis: { type: 'value', axisLabel: { color: '#64748b', formatter: v => v + unit }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
      series: [{
        type: 'bar', data: values, barMaxWidth: 60,
        itemStyle: {
          color: p => ['#4ba99a', '#3d9688', '#e8a020'][p.dataIndex % 3],
          borderRadius: [6, 6, 0, 0]
        },
        label: { show: true, position: 'top', color: '#1e293b', formatter: p => p.value + unit }
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
.page-header h2 { color: var(--text-primary); font-size: 20px; margin: 0; }
.refresh-btn {
  background: var(--bg-card); color: var(--text-secondary); border: 1px solid var(--border);
  padding: 6px 16px; border-radius: 8px; cursor: pointer; transition: all .2s;
}
.refresh-btn:hover { color: var(--text-primary); border-color: var(--border-hl); }
.loading, .error { text-align: center; padding: 40px; color: var(--text-muted); }
.error { color: var(--red); }

.overview-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 28px; }
.overview-card {
  background: var(--bg-panel); border-radius: 14px; padding: 20px;
  border: 1px solid var(--border); border-top: 4px solid var(--border);
  transition: transform .2s, box-shadow .2s;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.overview-card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.08); }
.card-red    { border-top-color: var(--red) !important; }
.card-yellow { border-top-color: var(--gold) !important; }
.card-green  { border-top-color: var(--green) !important; }
.ov-name { color: var(--text-primary); font-weight: 600; font-size: 16px; }
.ov-code { color: var(--text-muted); font-size: 13px; margin-bottom: 12px; }
.ov-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-bottom: 12px; }
.badge-red    { background: rgba(239,68,68,.1);  color: var(--red); }
.badge-yellow { background: rgba(245,158,11,.1); color: var(--gold); }
.badge-green  { background: rgba(34,197,94,.1);  color: var(--green); }
.ov-counts { display: flex; gap: 12px; font-size: 13px; }
.cnt-risk { color: var(--red); }
.cnt-opp  { color: var(--green); }

.signal-section {
  background: var(--bg-panel); border-radius: 14px; padding: 20px;
  margin-bottom: 20px; border: 1px solid var(--border);
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.section-title { display: flex; align-items: center; gap: 10px; color: var(--text-primary); font-weight: 600; font-size: 15px; margin-bottom: 16px; }
.dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.dot-red    { background: var(--red); }
.dot-yellow { background: var(--gold); }
.dot-green  { background: var(--green); }
.dot-blue   { background: var(--accent2); }

.signal-list { display: flex; flex-direction: column; gap: 10px; }
.signal-item {
  display: flex; align-items: center; gap: 12px;
  background: var(--bg-card); border-radius: 10px; padding: 12px 16px;
  border-left: 3px solid transparent; border: 1px solid var(--border);
  border-left-width: 3px;
}
.signal-red    { border-left-color: var(--red); }
.signal-yellow { border-left-color: var(--gold); }
.signal-green  { border-left-color: var(--green); }
.signal-icon { font-size: 16px; flex-shrink: 0; }
.signal-body { flex: 1; }
.signal-name   { color: var(--text-primary); font-size: 14px; font-weight: 500; }
.signal-detail { color: var(--text-secondary); font-size: 12px; margin-top: 2px; }
.signal-tag { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; flex-shrink: 0; }
.tag-red    { background: rgba(239,68,68,.1);  color: var(--red); }
.tag-yellow { background: rgba(245,158,11,.1); color: var(--gold); }
.tag-green  { background: rgba(34,197,94,.1);  color: var(--green); }
.signal-empty { color: var(--text-muted); font-size: 13px; text-align: center; padding: 16px; }

.compare-section {
  background: var(--bg-panel); border-radius: 14px; padding: 20px;
  margin-top: 8px; border: 1px solid var(--border);
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.metric-tabs { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.tab-btn {
  background: var(--bg-card); color: var(--text-secondary); border: 1px solid var(--border);
  padding: 5px 14px; border-radius: 20px; cursor: pointer; font-size: 13px; transition: all .2s;
}
.tab-btn.active { background: var(--accent2); color: #fff; border-color: var(--accent2); }
.tab-btn:hover:not(.active) { border-color: var(--border-hl); color: var(--text-primary); }
.bar-chart { width: 100%; height: 260px; }
</style>
