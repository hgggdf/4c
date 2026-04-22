<template>
  <div class="macro-panel">
    <div class="section-title">宏观经济指标</div>

    <!-- 指标 Tab -->
    <div class="macro-tabs">
      <button
        v-for="ind in indicators"
        :key="ind.key"
        class="macro-tab"
        :class="{ active: current === ind.key }"
        @click="current = ind.key"
      >{{ ind.label }}</button>
    </div>

    <!-- 图表 -->
    <div class="chart-container">
      <div v-if="loading" class="empty-state">加载中...</div>
      <div v-else-if="hasData" ref="chartRef" style="width:100%;height:100%;"></div>
      <div v-else class="empty-state">暂无真实数据</div>
    </div>

    <!-- 简要说明 -->
    <div class="macro-desc">
      <div class="macro-desc-title">{{ currentIndicator?.label }}</div>
      <div class="macro-desc-text">{{ currentIndicator?.desc }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getMacroIndicator } from '../api/macro'

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

async function loadAndRender() {
  loading.value = true
  hasData.value = false
  chartInst?.clear()

  try {
    const res = await getMacroIndicator(current.value)
    // 后端返回 { data: [...] } 或直接数组，data 项含 period/value 字段
    const items = Array.isArray(res) ? res : (res?.data ?? [])
    if (!items.length) {
      loading.value = false
      return
    }

    const dates = items.map(d => d.period ?? d.date ?? '')
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
      tooltip: {
        trigger: 'axis',
        formatter: (params) => {
          const p = params[0]
          return `${p.name}<br/><b>${p.value ?? '--'}</b>`
        },
      },
      grid: { left: 60, right: 24, top: 32, bottom: 40 },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { color: '#94a3b8', fontSize: 10, rotate: dates.length > 8 ? 30 : 0 },
        axisLine: { lineStyle: { color: '#e2e8f0' } },
      },
      yAxis: {
        type: 'value',
        scale: true,
        axisLabel: { color: '#94a3b8', fontSize: 10 },
        splitLine: { lineStyle: { color: '#f1f5f9' } },
      },
      series: [{
        name: currentIndicator.value?.label,
        type: isBar ? 'bar' : 'line',
        data: values,
        smooth: !isBar,
        symbol: 'circle', symbolSize: 5,
        lineStyle: { color: '#4ba99a', width: 2 },
        itemStyle: {
          color: (params) => {
            const v = params.value
            if (isBar) return v >= 0 ? '#e05252' : '#2db87a'
            return '#4ba99a'
          },
        },
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
    hasData.value = false
  }
}

watch(current, loadAndRender)
function onResize() { chartInst?.resize() }

onMounted(() => {
  loadAndRender()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chartInst?.dispose()
})
</script>

<style scoped>
.macro-panel { padding: 16px; display: flex; flex-direction: column; height: 100%; }
.section-title { font-size: 13px; font-weight: 700; color: var(--text-secondary); margin-bottom: 12px; }
.macro-tabs { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.macro-tab {
  background: var(--bg-card); color: var(--text-secondary);
  border: 1px solid var(--border); padding: 4px 12px;
  border-radius: 16px; cursor: pointer; font-size: 12px; transition: all .2s;
}
.macro-tab.active { background: var(--accent2); color: #fff; border-color: var(--accent2); }
.macro-tab:hover:not(.active) { border-color: var(--border-hl); color: var(--text-primary); }
.chart-container { flex: 1; min-height: 200px; }
.empty-state { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); font-size: 13px; }
.macro-desc {
  margin-top: 14px; padding: 12px 16px;
  background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-md);
}
.macro-desc-title { font-size: 13px; font-weight: 700; margin-bottom: 4px; }
.macro-desc-text { font-size: 12px; color: var(--text-secondary); line-height: 1.7; }
</style>
