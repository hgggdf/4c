<template>
  <div class="diagnose-page">
    <div class="page-header">
      <h2>企业运营诊断</h2>
      <div class="controls">
        <select v-model="selectedSymbol">
          <option v-for="company in companies" :key="company.symbol" :value="company.symbol">
            {{ company.name }} ({{ company.symbol }})
          </option>
        </select>
        <select v-model="selectedYear">
          <option value="2024">2024年</option>
          <option value="2023">2023年</option>
          <option value="2022">2022年</option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <template v-else-if="data">
      <!-- 总分卡片 -->
      <div class="score-card" :class="levelClass">
        <div class="score-main">
          <span class="score-num">{{ data.total_score.toFixed(0) }}</span>
          <span class="score-unit">分</span>
        </div>
        <div class="score-info">
          <div class="company-name">{{ data.stock_name }}（{{ data.stock_code }}）</div>
          <div class="score-level">{{ data.level }}</div>
          <div class="score-year">{{ data.year }}年度</div>
        </div>
      </div>

      <!-- 雷达图 -->
      <div class="chart-section">
        <div ref="radarRef" class="radar-chart"></div>
      </div>

      <!-- 维度详情 -->
      <div class="dimensions">
        <div v-for="dim in data.dimensions" :key="dim.name" class="dim-card">
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

      <!-- 优劣势 & 建议 -->
      <div class="insight-row">
        <div class="insight-box strength" v-if="data.strengths.length">
          <div class="insight-title">优势</div>
          <ul><li v-for="s in data.strengths" :key="s">{{ s }}</li></ul>
        </div>
        <div class="insight-box weakness" v-if="data.weaknesses.length">
          <div class="insight-title">劣势</div>
          <ul><li v-for="w in data.weaknesses" :key="w">{{ w }}</li></ul>
        </div>
        <div class="insight-box suggestion">
          <div class="insight-title">建议</div>
          <p>{{ data.suggestion }}</p>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getDiagnose } from '../api/analysis'
import { getStockList } from '../api/stock'

const selectedSymbol = ref('600276')
const selectedYear = ref('2024')
const companies = ref([])
const data = ref(null)
const loading = ref(false)
const error = ref('')
const radarRef = ref(null)
let chart = null

const levelClass = computed(() => {
  if (!data.value) return ''
  const map = { '优秀': 'level-excellent', '良好': 'level-good', '一般': 'level-fair', '较差': 'level-poor' }
  return map[data.value.level] || ''
})

function scoreClass(score) {
  if (score >= 80) return 'score-excellent'
  if (score >= 65) return 'score-good'
  if (score >= 45) return 'score-fair'
  return 'score-poor'
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const res = await getDiagnose(selectedSymbol.value, selectedYear.value)
    data.value = res
    await nextTick()
    renderRadar()
  } catch (e) {
    error.value = '加载失败：' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

function renderRadar() {
  if (!radarRef.value || !data.value) return
  if (!chart) chart = echarts.init(radarRef.value)

  const dims = data.value.dimensions
  const indicator = dims.map(d => ({ name: d.name, max: 100 }))
  const values = dims.map(d => d.score)

  chart.setOption({
    backgroundColor: 'transparent',
    radar: {
      indicator,
      shape: 'polygon',
      splitNumber: 4,
      axisName: { color: '#94a3b8', fontSize: 13 },
      splitLine: { lineStyle: { color: '#334155' } },
      splitArea: { areaStyle: { color: ['#1e293b', '#0f172a'] } },
      axisLine: { lineStyle: { color: '#334155' } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: values,
        name: data.value.stock_name,
        areaStyle: { color: 'rgba(99,102,241,0.25)' },
        lineStyle: { color: '#6366f1', width: 2 },
        itemStyle: { color: '#6366f1' },
        label: { show: true, color: '#e2e8f0', fontSize: 11,
                  formatter: p => p.value.toFixed(0) }
      }]
    }],
    tooltip: { trigger: 'item' }
  })
}

async function loadCompanies() {
  try {
    const stocks = await getStockList()
    companies.value = stocks
    if (stocks.length && !stocks.some(item => item.symbol === selectedSymbol.value)) {
      selectedSymbol.value = stocks[0].symbol
    }
  } catch {
    companies.value = [
      { symbol: '600276', name: '恒瑞医药' },
      { symbol: '603259', name: '药明康德' },
      { symbol: '300015', name: '爱尔眼科' },
    ]
  }
}

onMounted(async () => {
  await loadCompanies()
  await loadData()
})
watch([selectedSymbol, selectedYear], loadData)
</script>

<style scoped>
.diagnose-page { padding: 24px; max-width: 900px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-header h2 { color: #e2e8f0; font-size: 20px; margin: 0; }
.controls { display: flex; gap: 12px; }
.controls select {
  background: #1e293b; color: #e2e8f0; border: 1px solid #334155;
  padding: 6px 12px; border-radius: 8px; cursor: pointer;
}
.loading, .error { text-align: center; padding: 40px; color: #94a3b8; }
.error { color: #f87171; }

.score-card {
  display: flex; align-items: center; gap: 24px;
  background: #1e293b; border-radius: 16px; padding: 24px 32px;
  margin-bottom: 24px; border-left: 6px solid #6366f1;
}
.level-excellent { border-left-color: #22c55e; }
.level-good      { border-left-color: #6366f1; }
.level-fair      { border-left-color: #f59e0b; }
.level-poor      { border-left-color: #ef4444; }

.score-num { font-size: 56px; font-weight: 700; color: #e2e8f0; line-height: 1; }
.score-unit { font-size: 20px; color: #94a3b8; margin-left: 4px; }
.company-name { font-size: 18px; color: #e2e8f0; font-weight: 600; }
.score-level { font-size: 15px; color: #94a3b8; margin-top: 4px; }
.score-year  { font-size: 13px; color: #64748b; margin-top: 2px; }

.chart-section { background: #1e293b; border-radius: 16px; padding: 16px; margin-bottom: 24px; }
.radar-chart { width: 100%; height: 340px; }

.dimensions { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; margin-bottom: 24px; }
.dim-card { background: #1e293b; border-radius: 12px; padding: 16px; }
.dim-header { display: flex; justify-content: space-between; margin-bottom: 10px; }
.dim-name { color: #e2e8f0; font-weight: 600; }
.dim-score { font-weight: 700; font-size: 15px; }
.score-excellent { color: #22c55e; }
.score-good      { color: #6366f1; }
.score-fair      { color: #f59e0b; }
.score-poor      { color: #ef4444; }

.dim-bar { height: 6px; background: #0f172a; border-radius: 3px; margin-bottom: 10px; overflow: hidden; }
.dim-bar-fill { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
.dim-bar-fill.score-excellent { background: #22c55e; }
.dim-bar-fill.score-good      { background: #6366f1; }
.dim-bar-fill.score-fair      { background: #f59e0b; }
.dim-bar-fill.score-poor      { background: #ef4444; }

.dim-metrics { display: flex; flex-wrap: wrap; gap: 6px; }
.metric-tag { background: #0f172a; color: #94a3b8; font-size: 12px; padding: 2px 8px; border-radius: 4px; }

.insight-row { display: grid; grid-template-columns: 1fr 1fr 2fr; gap: 16px; }
.insight-box { background: #1e293b; border-radius: 12px; padding: 16px; }
.insight-title { font-weight: 600; margin-bottom: 10px; font-size: 14px; }
.strength .insight-title { color: #22c55e; }
.weakness .insight-title { color: #ef4444; }
.suggestion .insight-title { color: #6366f1; }
.insight-box ul { margin: 0; padding-left: 16px; }
.insight-box li { color: #94a3b8; font-size: 13px; margin-bottom: 4px; }
.insight-box p  { color: #94a3b8; font-size: 13px; margin: 0; line-height: 1.6; }
</style>
