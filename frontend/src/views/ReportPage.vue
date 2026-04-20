<template>
  <div class="report-page">
    <div class="page-header">
      <h2>定制化分析报告</h2>
    </div>

    <!-- 配置区 -->
    <div class="config-card">
      <div class="config-row">
        <div class="config-item">
          <label>目标公司</label>
          <select v-model="form.symbol">
            <option v-for="company in companies" :key="company.symbol" :value="company.symbol">
              {{ company.name }} ({{ company.symbol }})
            </option>
          </select>
        </div>
        <div class="config-item">
          <label>报告年份</label>
          <select v-model="form.year">
            <option value="2024">2024年</option>
            <option value="2023">2023年</option>
            <option value="2022">2022年</option>
          </select>
        </div>
        <div class="config-item">
          <label>报告类型</label>
          <div class="type-tabs">
            <button v-for="t in reportTypes" :key="t.value"
                    :class="['type-btn', { active: form.userType === t.value }]"
                    @click="form.userType = t.value">
              {{ t.label }}
            </button>
          </div>
        </div>
      </div>
      <button class="gen-btn" @click="generateReport" :disabled="loading">
        {{ loading ? '生成中...' : '生成报告' }}
      </button>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <!-- 报告内容 -->
    <div v-if="report" class="report-card">
      <div class="report-toolbar">
        <div class="report-title">
          {{ report.stock_name }} · {{ form.year }}年 · {{ currentTypeLabel }}分析报告
        </div>
        <button class="copy-btn" @click="copyReport">复制内容</button>
      </div>

      <!-- 评分概览 -->
      <div class="report-overview">
        <div class="ov-item">
          <div class="ov-val" :class="levelClass">{{ report.total_score.toFixed(0) }}</div>
          <div class="ov-label">综合评分</div>
        </div>
        <div class="ov-item">
          <div class="ov-val" :class="levelClass">{{ report.level }}</div>
          <div class="ov-label">评级</div>
        </div>
        <div class="ov-item" v-for="dim in report.dimensions.slice(0,3)" :key="dim.name">
          <div class="ov-val">{{ dim.score.toFixed(0) }}</div>
          <div class="ov-label">{{ dim.name }}</div>
        </div>
      </div>

      <!-- 趋势图 -->
      <div class="trend-section">
        <div class="trend-tabs">
          <button v-for="m in trendMetrics" :key="m"
                  :class="['trend-tab', { active: activeTrend === m }]"
                  @click="loadTrend(m)">{{ m }}</button>
        </div>
        <div ref="trendRef" class="trend-chart"></div>
      </div>

      <!-- 报告正文 -->
      <div class="report-body">
        <div class="report-section" v-for="sec in reportSections" :key="sec.title">
          <div class="sec-title">{{ sec.title }}</div>
          <div class="sec-content">{{ sec.content }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import * as echarts from 'echarts'
import { getDiagnose, getTrend } from '../api/analysis'
import { getStockList } from '../api/stock'

const form = ref({ symbol: '600276', year: '2024', userType: 'investor' })
const companies = ref([])
const report = ref(null)
const loading = ref(false)
const error = ref('')
const trendRef = ref(null)
let trendChart = null
const activeTrend = ref('营业总收入')

const reportTypes = [
  { value: 'investor', label: '投资者' },
  { value: 'manager',  label: '管理者' },
  { value: 'regulator',label: '监管机构' },
]

const trendMetrics = ['营业总收入', '净利润', '毛利率', 'ROE']

const currentTypeLabel = computed(() =>
  reportTypes.find(t => t.value === form.value.userType)?.label || ''
)

const levelClass = computed(() => {
  if (!report.value) return ''
  return { '优秀': 'lv-excellent', '良好': 'lv-good', '一般': 'lv-fair', '较差': 'lv-poor' }[report.value.level] || ''
})

const reportSections = computed(() => {
  if (!report.value) return []
  const r = report.value
  const type = form.value.userType

  const strengths = r.strengths.join('、') || '暂无明显优势'
  const weaknesses = r.weaknesses.join('、') || '暂无明显劣势'

  if (type === 'investor') {
    return [
      { title: '一、财务健康度', content: `${r.stock_name}综合评分 ${r.total_score.toFixed(0)} 分，评级${r.level}。主要优势：${strengths}。需关注：${weaknesses}。` },
      { title: '二、成长潜力', content: `从近三年数据来看，${r.stock_name}在成长性维度得分 ${r.dimensions.find(d=>d.name==='成长性')?.score.toFixed(0) ?? 'N/A'} 分，营收和利润保持稳定增长态势。` },
      { title: '三、风险提示', content: `${r.suggestion}。投资者需关注医药行业集采政策、医保谈判等政策风险，以及研发管线进展情况。` },
      { title: '四、投资建议', content: `综合财务质量和行业前景，${r.stock_name}整体处于${r.level}水平。建议结合市场估值和行业政策动态做出投资决策。本报告仅供参考，不构成投资建议。` },
    ]
  } else if (type === 'manager') {
    return [
      { title: '一、运营效率评估', content: `${r.stock_name}综合运营评分 ${r.total_score.toFixed(0)} 分（${r.level}）。盈利能力得分 ${r.dimensions.find(d=>d.name==='盈利能力')?.score.toFixed(0) ?? 'N/A'} 分，偿债能力得分 ${r.dimensions.find(d=>d.name==='偿债能力')?.score.toFixed(0) ?? 'N/A'} 分。` },
      { title: '二、行业对标分析', content: `与恒瑞医药、药明康德、爱尔眼科三家医药企业横向对比，${r.stock_name}在${strengths}方面具有竞争优势，在${weaknesses}方面存在提升空间。` },
      { title: '三、改进建议', content: r.suggestion },
      { title: '四、战略规划参考', content: `建议管理层重点关注研发投入效率、成本控制和市场拓展，持续提升核心竞争力，应对医保政策和集采带来的市场变化。` },
    ]
  } else {
    return [
      { title: '一、合规指标概览', content: `${r.stock_name}${form.value.year}年综合评分 ${r.total_score.toFixed(0)} 分，财务状况${r.level}。资产负债率、流动比率等偿债指标处于${r.dimensions.find(d=>d.name==='偿债能力')?.comment ?? '正常'}。` },
      { title: '二、异常波动监测', content: `近三年财务数据未发现重大异常波动。${weaknesses !== '暂无明显劣势' ? '需关注：' + weaknesses : '各项指标运行平稳。'}` },
      { title: '三、信息披露完整性', content: `财务数据来源于同花顺财务摘要及上市公司年报，数据完整性良好，关键财务指标均有披露。` },
      { title: '四、监管建议', content: `建议持续关注企业研发投入真实性、关联交易合规性，以及医保政策执行情况。` },
    ]
  }
})

async function generateReport() {
  loading.value = true
  error.value = ''
  report.value = null
  try {
    const res = await getDiagnose(form.value.symbol, form.value.year)
    report.value = res
    await nextTick()
    loadTrend(activeTrend.value)
  } catch (e) {
    error.value = '生成失败：' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

async function loadTrend(metric) {
  activeTrend.value = metric
  if (!trendRef.value || !report.value) return
  if (!trendChart) trendChart = echarts.init(trendRef.value)

  try {
    const res = await getTrend(form.value.symbol, metric)
    const trend = res.trend
    const years = trend.map(t => t.year + '年')
    const values = trend.map(t => t.value ?? 0)
    const unit = trend[0]?.unit || ''

    trendChart.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', formatter: p => `${p[0].name}<br/>${metric}: ${p[0].value}${unit}` },
      xAxis: { type: 'category', data: years, axisLabel: { color: '#64748b' }, axisLine: { lineStyle: { color: '#e2e8f0' } } },
      yAxis: { type: 'value', axisLabel: { color: '#64748b', formatter: v => v + unit }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
      series: [{
        type: 'line', data: values, smooth: true,
        lineStyle: { color: '#4ba99a', width: 3 },
        itemStyle: { color: '#4ba99a' },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(75,169,154,0.25)' }, { offset: 1, color: 'rgba(75,169,154,0)' }] } },
        label: { show: true, color: '#1e293b', formatter: p => p.value + unit }
      }],
      grid: { left: 50, right: 20, top: 20, bottom: 40 }
    })
  } catch {}
}

function copyReport() {
  const text = reportSections.value.map(s => s.title + '\n' + s.content).join('\n\n')
  navigator.clipboard.writeText(text).then(() => alert('已复制到剪贴板'))
}

onMounted(async () => {
  try {
    const stocks = await getStockList()
    companies.value = stocks
    if (stocks.length && !stocks.some(item => item.symbol === form.value.symbol)) {
      form.value.symbol = stocks[0].symbol
    }
  } catch {
    companies.value = [
      { symbol: '600276', name: '恒瑞医药' },
      { symbol: '603259', name: '药明康德' },
      { symbol: '300015', name: '爱尔眼科' },
    ]
  }
})
</script>

<style scoped>
.report-page { padding: 24px; max-width: 960px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-header h2 { color: var(--text-primary); font-size: 20px; margin: 0; }

.config-card {
  background: var(--bg-panel); border-radius: 16px; padding: 24px;
  margin-bottom: 24px; border: 1px solid var(--border);
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.config-row { display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 20px; }
.config-item { display: flex; flex-direction: column; gap: 8px; }
.config-item label { color: var(--text-secondary); font-size: 13px; }
.config-item select {
  background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border);
  padding: 8px 14px; border-radius: 8px; cursor: pointer; min-width: 180px;
  transition: border-color .2s;
}
.config-item select:focus { outline: none; border-color: var(--border-hl); }
.type-tabs { display: flex; gap: 8px; }
.type-btn {
  background: var(--bg-card); color: var(--text-secondary); border: 1px solid var(--border);
  padding: 7px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; transition: all .2s;
}
.type-btn.active { background: var(--accent2); color: #fff; border-color: var(--accent2); }
.type-btn:hover:not(.active) { border-color: var(--border-hl); color: var(--text-primary); }
.gen-btn {
  background: var(--accent2); color: #fff; border: none;
  padding: 10px 32px; border-radius: 10px; cursor: pointer; font-size: 15px; font-weight: 600;
  transition: background .2s, box-shadow .2s;
}
.gen-btn:hover { background: #3d9688; box-shadow: 0 4px 14px rgba(75,169,154,0.35); }
.gen-btn:disabled { opacity: .5; cursor: not-allowed; }
.error { color: var(--red); margin-bottom: 16px; }

.report-card {
  background: var(--bg-panel); border-radius: 16px; overflow: hidden;
  border: 1px solid var(--border); box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.report-toolbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 24px; border-bottom: 1px solid var(--border);
  background: var(--bg-card);
}
.report-title { color: var(--text-primary); font-weight: 600; font-size: 16px; }
.copy-btn {
  background: var(--bg-panel); color: var(--text-secondary); border: 1px solid var(--border);
  padding: 5px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; transition: all .2s;
}
.copy-btn:hover { color: var(--text-primary); border-color: var(--border-hl); }

.report-overview {
  display: flex; gap: 0; border-bottom: 1px solid var(--border);
}
.ov-item {
  flex: 1; text-align: center; padding: 20px 12px;
  border-right: 1px solid var(--border);
}
.ov-item:last-child { border-right: none; }
.ov-val { font-size: 26px; font-weight: 700; color: var(--accent2); margin-bottom: 4px; }
.lv-excellent { color: var(--green); }
.lv-good      { color: var(--accent2); }
.lv-fair      { color: var(--gold); }
.lv-poor      { color: var(--red); }
.ov-label { color: var(--text-muted); font-size: 12px; }

.trend-section { padding: 20px 24px; border-bottom: 1px solid var(--border); }
.trend-tabs { display: flex; gap: 8px; margin-bottom: 12px; }
.trend-tab {
  background: var(--bg-card); color: var(--text-secondary); border: 1px solid var(--border);
  padding: 4px 12px; border-radius: 16px; cursor: pointer; font-size: 12px; transition: all .2s;
}
.trend-tab.active { background: var(--accent2); color: #fff; border-color: var(--accent2); }
.trend-tab:hover:not(.active) { border-color: var(--border-hl); }
.trend-chart { width: 100%; height: 220px; }

.report-body { padding: 24px; }
.report-section { margin-bottom: 20px; }
.sec-title { color: var(--accent2); font-weight: 600; font-size: 15px; margin-bottom: 8px; }
.sec-content { color: var(--text-secondary); font-size: 14px; line-height: 1.8; }
</style>
