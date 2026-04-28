<template>
  <div ref="chartRef" style="height: 360px; width: 100%;"></div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  kline: {
    type: Array,
    default: () => []
  }
})

const chartRef = ref(null)
let chartInstance = null

function renderChart() {
  if (!chartRef.value) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  const dates = props.kline.map(item => item.date)
  const values = props.kline.map(item => item.close)

  chartInstance.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: dates
    },
    yAxis: {
      type: 'value',
      scale: true
    },
    series: [
      {
        name: '收盘价',
        type: 'line',
        smooth: true,
        data: values
      }
    ]
  })
}

watch(() => props.kline, renderChart, { deep: true })

onMounted(() => {
  renderChart()
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chartInstance?.dispose()
  chartInstance = null
})

function resize() {
  chartInstance?.resize()
}
</script>
