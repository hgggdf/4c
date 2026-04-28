<template>
  <div class="report-chart-wrap">
    <div v-if="title" class="report-chart-title">{{ title }}</div>
    <div ref="chartEl" class="report-chart-canvas"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  config: { type: Object, required: true },
})

const chartEl = ref(null)
let instance = null

const title = props.config?.title?.text || props.config?._title || ''

function buildOption(cfg) {
  // 剥掉自定义字段，其余直接作为 echarts option
  const { _title, ...option } = cfg
  // 注入主题色
  const ACCENT = '#4ba99a'
  const COLORS = ['#4ba99a', '#6366f1', '#f59e0b', '#e05252', '#10b981', '#8b5cf6']
  if (!option.color) option.color = COLORS
  // 默认背景透明
  option.backgroundColor = option.backgroundColor ?? 'transparent'
  // tooltip 默认开启
  if (!option.tooltip) option.tooltip = { trigger: 'axis' }
  // grid 留边距
  if (!option.grid) option.grid = { left: '3%', right: '4%', bottom: '3%', containLabel: true }
  return option
}

function init() {
  if (!chartEl.value) return
  instance = echarts.init(chartEl.value, null, { renderer: 'canvas' })
  instance.setOption(buildOption(props.config))
}

function resize() {
  instance?.resize()
}

onMounted(() => {
  init()
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  instance?.dispose()
})

watch(() => props.config, (cfg) => {
  instance?.setOption(buildOption(cfg), true)
}, { deep: true })
</script>

<style scoped>
.report-chart-wrap {
  margin: 12px 0;
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  background: var(--bg-card);
}
.report-chart-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  padding: 8px 14px 0;
}
.report-chart-canvas {
  width: 100%;
  height: 300px;
}
</style>
