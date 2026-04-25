<template>
  <div class="macro-panel">
    <div class="content-scroll">

      <!-- 宏观经济指标 -->
      <div class="section-title">宏观经济指标</div>
      <div class="indicator-tabs">
        <button
          v-for="ind in indicators"
          :key="ind.key"
          class="ind-btn"
          :class="{ active: current === ind.key }"
          @click="current = ind.key"
        >{{ ind.label }}</button>
      </div>
      <div class="chart-wrap">
        <div v-if="loading" class="empty-state">加载中...</div>
        <div v-else-if="hasData" ref="chartRef" class="chart-el"></div>
        <div v-else class="empty-state">暂无数据</div>
      </div>
      <div class="desc-card">
        <div class="desc-title">{{ currentIndicator?.label }}</div>
        <div class="desc-text">{{ currentIndicator?.desc }}</div>
      </div>

      <!-- 关键数据一览 -->
      <div class="section-title" style="margin-top:16px;">关键数据一览</div>
      <div class="macro-grid">
        <div v-for="(m, i) in keyMetrics" :key="m.label" class="macro-card" :style="{ animationDelay: `${i * 50}ms` }">
          <div class="macro-label">{{ m.label }}</div>
          <div class="macro-value" :class="m.trend === 'up' ? 'red' : m.trend === 'down' ? 'green' : ''">{{ m.value }}</div>
          <div class="macro-sub">{{ m.sub }}</div>
        </div>
      </div>

      <!-- 政策动态 -->
      <div class="section-title" style="margin-top:16px;">医药行业政策动态</div>
      <div class="report-list">
        <div v-for="(p, i) in policies" :key="p.id" class="report-item" :style="{ animationDelay: `${i * 50}ms` }">
          <div class="report-title">{{ p.title }}</div>
          <div class="report-meta">{{ p.source }}<template v-if="p.date"> · {{ p.date }}</template></div>
          <span class="report-rating" :class="p.tagClass">{{ p.tag }}</span>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getMacroIndicator, getMacroSummary } from '../api/macro'
import { getNewsByIndustry } from '../api/news'

// ── 指标 ──────────────────────────────────────────
const indicators = [
  { key: 'CPI',    label: 'CPI',    desc: 'CPI（居民消费价格指数）同比变化，反映通货膨胀水平，影响医药消费品定价空间。' },
  { key: 'PPI',    label: 'PPI',    desc: 'PPI（工业生产者出厂价格指数）同比，影响原料药及医疗耗材成本端压力。' },
  { key: 'PMI',    label: 'PMI',    desc: 'PMI 制造业采购经理指数，50 以上为扩张，反映工业景气度。' },
  { key: '社融',   label: '社融',   desc: '社会融资规模存量同比增速，衡量宏观流动性松紧，影响医药行业再融资环境。' },
  { key: 'GDP',    label: 'GDP',    desc: 'GDP 同比增速，宏观经济总量指标，与医疗支出规模正相关。' },
  { key: '医药研发投入', label: '医药研发', desc: '医药行业全年研发投入增速，反映创新药研发景气度。' },
]

const current = ref('CPI')
const chartRef = ref(null)
const hasData = ref(false)
const loading = ref(false)
let chartInst = null

const currentIndicator = computed(() => indicators.find(i => i.key === current.value))

// ── 关键数据（从后端加载）──────────────────────────
const keyMetrics = ref([])

async function loadKeyMetrics() {
  try {
    const items = await getMacroSummary(['CPI', 'PPI', 'PMI', 'GDP', '社融', '医药研发投入'], 1)
    const list = Array.isArray(items) ? items : []
    keyMetrics.value = list.map(item => ({
      label: item.indicator_name || item.name || '',
      value: item.latest_value ?? item.value ?? '--',
      sub: item.latest_period ?? item.period ?? '',
      trend: (() => {
        if (item.trend) return item.trend
        const v = parseFloat(item.latest_value ?? item.value)
        if (isNaN(v)) return ''
        return v > 0 ? 'up' : v < 0 ? 'down' : ''
      })(),
    }))
  } catch (err) {
    console.error('[loadKeyMetrics]', err)
  }
}

// ── 政策动态（从后端加载）──────────────────────────
const policies = ref([])

async function loadPolicies() {
  try {
    const items = await getNewsByIndustry('医药生物', 30)
    const list = Array.isArray(items) ? items : []
    policies.value = list.slice(0, 10).map((item, i) => ({
      id: item.id || i,
      title: item.title || item.headline || item['新闻标题'] || '',
      source: item.source || item.publisher || item['新闻来源'] || '',
      date: (item.publish_date || item.date || item['发布时间'] || '').slice(0, 10),
      tag: item.category || item.tag || '政策',
      tagClass: (() => {
        const cat = item.category || item.sentiment || ''
        if (['利好', '买入', '增持', '医保', '审批', '财政'].some(k => cat.includes(k))) return 'rating-buy'
        if (['利空', '集采', '降价', '风险'].some(k => cat.includes(k))) return 'rating-sell'
        return 'rating-hold'
      })(),
    }))
  } catch (err) {
    console.error('[loadPolicies]', err)
  }
}

// ── 图表 ──────────────────────────────────────────
async function loadAndRender() {
  loading.value = true
  hasData.value = false
  chartInst?.clear()

  try {
    const res = await getMacroIndicator(current.value)
    const items = Array.isArray(res) ? res : (res?.data ?? [])
    if (!items.length) { loading.value = false; return }

    const dates  = items.map(d => d.period ?? d.date ?? '')
    const values = items.map(d => {
      const v = d.value ?? d.val
      return v !== null && v !== undefined ? Number(v) : null
    })

    hasData.value = true
    loading.value = false
    await nextTick()
    if (!chartRef.value) return
    if (!chartInst) chartInst = echarts.init(chartRef.value)

    const isBar = current.value === 'GDP' || current.value === '医药研发投入'
    chartInst.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', formatter: p => `${p[0].name}<br/><b>${p[0].value ?? '--'}</b>` },
      grid: { left: 52, right: 16, top: 24, bottom: 36 },
      xAxis: {
        type: 'category', data: dates,
        axisLabel: { color: '#94a3b8', fontSize: 10, rotate: dates.length > 8 ? 30 : 0 },
        axisLine: { lineStyle: { color: '#e2e8f0' } },
      },
      yAxis: {
        type: 'value', scale: true,
        axisLabel: { color: '#94a3b8', fontSize: 10 },
        splitLine: { lineStyle: { color: '#f1f5f9' } },
      },
      series: [{
        name: currentIndicator.value?.label,
        type: isBar ? 'bar' : 'line',
        data: values, smooth: !isBar,
        symbol: 'circle', symbolSize: 4,
        lineStyle: { color: '#4ba99a', width: 2 },
        itemStyle: { color: p => isBar ? (p.value >= 0 ? '#e05252' : '#2db87a') : '#4ba99a' },
        areaStyle: isBar ? undefined : {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(75,169,154,0.2)' },
            { offset: 1, color: 'rgba(75,169,154,0.01)' },
          ]),
        },
        markLine: {
          silent: true,
          lineStyle: { color: '#cbd5e1', type: 'dashed' },
          data: [{ type: 'average', name: '均值' }],
          label: { color: '#94a3b8', fontSize: 10 },
        },
      }],
    }, true)
  } catch {
    loading.value = false
  }
}

watch(current, loadAndRender)
function onResize() { chartInst?.resize() }

onMounted(() => { loadAndRender(); loadKeyMetrics(); loadPolicies(); window.addEventListener('resize', onResize) })
onBeforeUnmount(() => { window.removeEventListener('resize', onResize); chartInst?.dispose() })
</script>

<style scoped>
.macro-panel { background: var(--bg-panel); }
.content-scroll { overflow-y: auto; overflow-x: hidden; padding: 16px; }
.section-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 10px; }

/* ── 指标选择 ── */
.indicator-tabs { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.ind-btn {
  background: var(--bg-card); color: var(--text-secondary);
  border: 1px solid var(--border); padding: 4px 10px;
  border-radius: 16px; cursor: pointer; font-size: 12px; transition: all .2s;
  white-space: nowrap;
}
.ind-btn.active { background: var(--accent2); color: #fff; border-color: var(--accent2); }
.ind-btn:hover:not(.active) { border-color: var(--border-hl); color: var(--text-primary); }

/* ── 图表 ── */
.chart-wrap { height: 200px; margin-bottom: 12px; }
.chart-el   { width: 100%; height: 100%; }

/* ── 指标说明 ── */
.desc-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 10px; padding: 10px 14px; margin-bottom: 4px;
}
.desc-title { font-size: 12px; font-weight: 700; margin-bottom: 4px; color: var(--text-primary); }
.desc-text  { font-size: 11px; color: var(--text-secondary); line-height: 1.7; }

/* ── 关键数据格 ── */
.macro-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.macro-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 8px; padding: 10px 12px;
  animation: cardRise .4s ease both;
}
.macro-label { font-size: 11px; color: var(--text-muted); margin-bottom: 4px; }
.macro-value { font-size: 16px; font-weight: 700; color: var(--text-primary); }
.macro-sub   { font-size: 10px; color: var(--text-muted); margin-top: 2px; }
.red   { color: var(--red); }
.green { color: var(--green); }

/* ── 政策列表（与研报一致） ── */
.report-list { display: flex; flex-direction: column; gap: 10px; }
.report-item {
  background: var(--bg-card); border-radius: 10px;
  padding: 12px; border: 1px solid var(--border); position: relative;
  animation: cardRise .4s ease both;
}
.report-title { font-size: 13px; font-weight: 500; color: var(--text-primary); margin-bottom: 6px; padding-right: 52px; line-height: 1.5; }
.report-meta  { font-size: 11px; color: var(--text-muted); }
.report-rating {
  position: absolute; top: 12px; right: 12px;
  font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px;
  white-space: nowrap;
}
.rating-buy  { background: rgba(34,197,94,.12);  color: var(--green); }
.rating-hold { background: rgba(245,158,11,.12); color: var(--gold); }
.rating-sell { background: rgba(239,68,68,.12);  color: var(--red); }

.empty-state { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); font-size: 13px; }
</style>
