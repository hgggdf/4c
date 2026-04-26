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

      <div class="retrieval-box">
        <div class="retrieval-header">
          <div>
            <h3>混合检索结果</h3>
            <p>关键词 + 向量联合召回</p>
          </div>
          <button class="refresh-btn" @click="loadRetrieval" :disabled="retrievalLoading">
            {{ retrievalLoading ? '加载中...' : '刷新检索' }}
          </button>
        </div>
        <div v-if="retrievalError" class="error retrieval-error">{{ retrievalError }}</div>
        <div v-else-if="retrievalItems.length" class="retrieval-list">
          <div v-for="item in retrievalItems" :key="`${item.metadata?.doc_type}-${item.metadata?.source_pk}-${item.chunk_id}`" class="retrieval-item">
            <div class="retrieval-item-top">
              <span class="retrieval-type">{{ item.metadata?.doc_type || 'unknown' }}</span>
              <span class="retrieval-score">{{ Number(item.final_score || item.score || 0).toFixed(2) }}</span>
            </div>
            <div class="retrieval-title">{{ item.metadata?.title || item.source_record?.title || '未命名结果' }}</div>
            <div class="retrieval-meta">
              <span>来源：{{ item.match_source || 'vector' }}</span>
              <span v-if="item.keyword_score != null">关键词分：{{ Number(item.keyword_score).toFixed(2) }}</span>
              <span v-if="item.vector_score != null">向量分：{{ Number(item.vector_score).toFixed(2) }}</span>
            </div>
            <p class="retrieval-snippet">{{ item.text || item.source_record?.summary_text || item.source_record?.content || '暂无摘要' }}</p>
          </div>
        </div>
        <div v-else class="retrieval-empty">暂无检索结果</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getDiagnose } from '../api/analysis'
import { getStockList } from '../api/stock'
import { searchHybrid } from '../api/retrieval'

const selectedSymbol = ref('')
const selectedYear = ref('2024')
const companies = ref([])
const data = ref(null)
const loading = ref(false)
const error = ref('')
const radarRef = ref(null)
const retrievalItems = ref([])
const retrievalLoading = ref(false)
const retrievalError = ref('')
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
    data.value = res.data ?? res
    await nextTick()
    renderRadar()
    await loadRetrieval()
  } catch (e) {
    error.value = '加载失败：' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

async function loadRetrieval() {
  if (!selectedSymbol.value) return
  retrievalLoading.value = true
  retrievalError.value = ''
  try {
    const keyword = `${selectedSymbol.value} ${data.value?.stock_name || ''} 诊断 风险 公告 新闻`
    const res = await searchHybrid({ query: keyword, stock_code: selectedSymbol.value, top_k: 5 })
    retrievalItems.value = res.data?.items ?? res.items ?? []
  } catch (e) {
    retrievalError.value = '检索失败：' + (e.response?.data?.detail || e.message)
    retrievalItems.value = []
  } finally {
    retrievalLoading.value = false
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
      axisName: { color: '#64748b', fontSize: 13 },
      splitLine: { lineStyle: { color: '#e2e8f0' } },
      splitArea: { areaStyle: { color: ['rgba(248,250,252,0.8)', 'rgba(241,245,249,0.5)'] } },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: values,
        name: data.value.stock_name,
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

async function loadCompanies() {
  try {
    const stocks = await getStockList()
    companies.value = stocks
    if (stocks.length) {
      if (!selectedSymbol.value || !stocks.some(item => item.symbol === selectedSymbol.value)) {
        selectedSymbol.value = stocks[0].symbol
      }
    }
  } catch {
    companies.value = []
  }
}

onMounted(async () => {
  await loadCompanies()
  if (selectedSymbol.value) await loadData()
})
watch([selectedSymbol, selectedYear], () => {
  if (selectedSymbol.value) loadData()
})
</script>

<style scoped>
.diagnose-page { padding: 24px; max-width: 900px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-header h2 { color: var(--text-primary); font-size: 20px; margin: 0; }
.controls { display: flex; gap: 12px; }
.controls select {
  background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border);
  padding: 6px 12px; border-radius: 8px; cursor: pointer;
  transition: border-color .2s;
}
.controls select:focus { outline: none; border-color: var(--border-hl); }
.loading, .error { text-align: center; padding: 40px; color: var(--text-muted); }
.error { color: var(--red); }

.score-card {
  display: flex; align-items: center; gap: 24px;
  background: var(--bg-panel); border-radius: 16px; padding: 24px 32px;
  margin-bottom: 24px; border-left: 6px solid var(--accent2);
  border: 1px solid var(--border); border-left-width: 6px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.level-excellent { border-left-color: var(--green) !important; }
.level-good      { border-left-color: var(--accent2) !important; }
.level-fair      { border-left-color: var(--gold) !important; }
.level-poor      { border-left-color: var(--red) !important; }

.score-num { font-size: 56px; font-weight: 700; color: var(--text-primary); line-height: 1; }
.score-unit { font-size: 20px; color: var(--text-muted); margin-left: 4px; }
.company-name { font-size: 18px; color: var(--text-primary); font-weight: 600; }
.score-level { font-size: 15px; color: var(--text-secondary); margin-top: 4px; }
.score-year  { font-size: 13px; color: var(--text-muted); margin-top: 2px; }

.chart-section {
  background: var(--bg-panel); border-radius: 16px; padding: 16px;
  margin-bottom: 24px; border: 1px solid var(--border);
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.radar-chart { width: 100%; height: 340px; }

.dimensions { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; margin-bottom: 24px; }
.dim-card {
  background: var(--bg-panel); border-radius: 12px; padding: 16px;
  border: 1px solid var(--border);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}
.dim-header { display: flex; justify-content: space-between; margin-bottom: 10px; }
.dim-name { color: var(--text-primary); font-weight: 600; }
.dim-score { font-weight: 700; font-size: 15px; }
.score-excellent { color: var(--green); }
.score-good      { color: var(--accent2); }
.score-fair      { color: var(--gold); }
.score-poor      { color: var(--red); }

.dim-bar { height: 6px; background: var(--bg-card2); border-radius: 3px; margin-bottom: 10px; overflow: hidden; }
.dim-bar-fill { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
.dim-bar-fill.score-excellent { background: var(--green); }
.dim-bar-fill.score-good      { background: var(--accent2); }
.dim-bar-fill.score-fair      { background: var(--gold); }
.dim-bar-fill.score-poor      { background: var(--red); }

.dim-metrics { display: flex; flex-wrap: wrap; gap: 6px; }
.metric-tag { background: var(--bg-card2); color: var(--text-secondary); font-size: 12px; padding: 2px 8px; border-radius: 4px; }

.insight-row { display: grid; grid-template-columns: 1fr 1fr 2fr; gap: 16px; }
.insight-box {
  background: var(--bg-panel); border-radius: 12px; padding: 16px;
  border: 1px solid var(--border);
}
.insight-title { font-weight: 600; margin-bottom: 10px; font-size: 14px; }
.strength .insight-title { color: var(--green); }
.weakness .insight-title { color: var(--red); }
.suggestion .insight-title { color: var(--accent2); }
.insight-box ul { margin: 0; padding-left: 16px; }
.insight-box li { color: var(--text-secondary); font-size: 13px; margin-bottom: 4px; }
.insight-box p  { color: var(--text-secondary); font-size: 13px; margin: 0; line-height: 1.6; }
</style>
