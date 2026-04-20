<template>
  <div class="macro-panel">
    <div class="section-title">宏观经济指标</div>

    <!-- 指标 Tab -->
    <div class="macro-tabs">
      <button
        v-for="ind in indicators"
        :key="ind"
        class="macro-tab"
        :class="{ active: current === ind }"
        @click="current = ind"
      >{{ ind }}</button>
    </div>

    <!-- 图表 -->
    <div class="chart-container">
      <div v-if="hasData" ref="chartRef" style="width:100%;height:100%;"></div>
      <div v-else class="empty-state">暂无本地宏观数据</div>
    </div>

    <!-- 简要说明 -->
    <div class="macro-desc">
      <div class="macro-desc-title">{{ current }}</div>
      <div class="macro-desc-text">{{ hasData ? descriptions[current] : emptyDescription }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getMacroSeries } from '../api/stock'

const indicators = ['CPI', 'PPI', 'PMI', '社融', 'GDP', '医药研发投入']
const current = ref('CPI')
const chartRef = ref(null)
const hasData = ref(false)
let chartInst = null

const emptyDescription = '当前仓库未提供可直接展示的本地宏观指标数据，这里不再使用 mock 数据代替真实数据。'

const descriptions = {
  'CPI':    'CPI（居民消费价格指数）同比变化，反映通货膨胀水平，影响医药消费品定价空间。',
  'PPI':    'PPI（工业生产者出厂价格指数）同比，影响原料药及医疗耗材成本端压力。',
  'PMI':    'PMI 制造业采购经理指数，50 以上为扩张，反映工业景气度。',
  '社融':   '社会融资规模存量同比增速，衡量宏观流动性松紧，影响医药行业再融资环境。',
  'GDP':    'GDP 同比增速，宏观经济总量指标，与医疗支出规模正相关。',
  '医药研发投入': '医药行业全年研发投入增速（亿元），反映创新药研发景气度。',
}

async function loadAndRender() {
  const data = await getMacroSeries(current.value)
  if (!data) {
    hasData.value = false
    chartInst?.clear()
    return
  }

  hasData.value = true
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
        return `${p.name}<br/><b>${p.value}</b>`
      },
    },
    grid: { left: 60, right: 24, top: 32, bottom: 40 },
    xAxis: {
      type: 'category',
      data: data.dates,
      axisLabel: { color: '#94a3b8', fontSize: 10, rotate: data.dates.length > 8 ? 30 : 0 },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
    },
    yAxis: {
      type: 'value',
      scale: true,
      name: data.label,
      nameTextStyle: { color: '#94a3b8', fontSize: 10 },
      axisLabel: { color: '#94a3b8', fontSize: 10 },
      splitLine: { lineStyle: { color: '#f1f5f9' } },
    },
    series: [{
      name: data.label,
      type: isBar ? 'bar' : 'line',
      data: data.values,
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
}

watch(current, loadAndRender)
function onResize() {
  chartInst?.resize()
}

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
.macro-desc {
  margin-top: 14px;
  padding: 12px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}
.macro-desc-title {
  font-size: 13px; font-weight: 700; margin-bottom: 4px;
}
.macro-desc-text {
  font-size: 12px; color: var(--text-secondary); line-height: 1.7;
}
</style>
