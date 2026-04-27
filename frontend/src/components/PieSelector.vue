<template>
  <div class="pie-panel">
    <div class="pie-title">选择分析维度</div>

    <svg
      ref="svgRef"
      :width="svgSize"
      :height="svgSize"
      :viewBox="`0 0 ${svgSize} ${svgSize}`"
      style="overflow: visible; cursor: pointer;"
    >
      <defs>
        <!-- 扇形渐变 -->
        <radialGradient id="g0" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#7dd3c8" stop-opacity="0.95" />
          <stop offset="100%" stop-color="#4ba99a" stop-opacity="0.75" />
        </radialGradient>
        <radialGradient id="g1" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#86efac" stop-opacity="0.95" />
          <stop offset="100%" stop-color="#2db87a" stop-opacity="0.75" />
        </radialGradient>
        <radialGradient id="g2" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#fde68a" stop-opacity="0.95" />
          <stop offset="100%" stop-color="#e8a020" stop-opacity="0.75" />
        </radialGradient>
        <!-- 发光滤镜 -->
        <filter id="glow">
          <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
          <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>

      <!-- 背景圆 -->
      <circle
        :cx="cx" :cy="cy" :r="bgR"
        fill="rgba(248,250,252,0.9)"
        stroke="rgba(0,0,0,0.06)"
        stroke-width="1"
      />

      <!-- 三个扇形 -->
      <g
        v-for="(seg, i) in segments"
        :key="i"
        style="transition: transform 0.3s cubic-bezier(0.34,1.56,0.64,1);"
        :style="{ transform: hovered===i ? `translate(${seg.pushX}px,${seg.pushY}px)` : 'translate(0,0)' }"
        @mouseenter="hovered = i"
        @mouseleave="hovered = -1"
        @click="$emit('select', seg.key)"
      >
        <!-- 扇形路径 -->
        <path
          :d="seg.path"
          :fill="`url(#g${i})`"
          :stroke="activeKey===seg.key ? '#1e293b' : 'rgba(0,0,0,0.06)'"
          :stroke-width="activeKey===seg.key ? 2 : 1"
          :filter="hovered===i || activeKey===seg.key ? 'url(#glow)' : ''"
          :opacity="activeKey && activeKey!==seg.key ? 0.55 : 1"
          style="transition: all 0.25s;"
        />
        <!-- 分割线 -->
        <line
          :x1="cx" :y1="cy"
          :x2="seg.lineEnd[0]" :y2="seg.lineEnd[1]"
          stroke="rgba(0,0,0,0.08)" stroke-width="1.5"
        />
        <!-- 图标+文字 -->
        <text
          :x="seg.labelX" :y="seg.labelY - 10"
          text-anchor="middle" dominant-baseline="middle"
          font-size="22" fill="#334155"
          style="pointer-events:none; user-select:none;"
        >{{ seg.icon }}</text>
        <text
          :x="seg.labelX" :y="seg.labelY + 14"
          text-anchor="middle" dominant-baseline="middle"
          font-size="13" font-weight="700" fill="#1e293b"
          style="pointer-events:none; user-select:none; letter-spacing:0.05em;"
        >{{ seg.label }}</text>
        <text
          :x="seg.labelX" :y="seg.labelY + 30"
          text-anchor="middle" dominant-baseline="middle"
          font-size="10" fill="rgba(30,41,59,0.5)"
          style="pointer-events:none; user-select:none;"
        >{{ seg.sub }}</text>
      </g>

      <!-- 中心 logo -->
      <circle :cx="cx" :cy="cy" r="28"
        fill="#ffffff"
        stroke="rgba(0,0,0,0.08)"
        stroke-width="1.5"
      />
      <text :x="cx" :y="cy-6" text-anchor="middle" font-size="14" fill="#4ba99a">⚕</text>
      <text :x="cx" :y="cy+10" text-anchor="middle" font-size="9" fill="rgba(30,41,59,0.4)">投研</text>
    </svg>

    <!-- 图例 -->
    <div class="pie-legend">
      <div
        v-for="(seg, i) in segments"
        :key="i"
        class="pie-legend-item"
        :class="{ active: activeKey === seg.key }"
        @click="$emit('select', seg.key)"
      >
        <span class="legend-dot" :style="{ background: seg.color }"></span>
        {{ seg.label }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  activeKey: { type: String, default: '' }
})
defineEmits(['select'])

const svgSize = 260
const cx = svgSize / 2
const cy = svgSize / 2
const bgR = 110
const r   = 105
const innerR = 30

const hovered = ref(-1)
const svgRef  = ref(null)

// 三个扇形：均分 120°，从 -90° 开始（顶部）
const SEGS_DEF = [
  { key: 'stock',    label: '个股',   sub: '医药上市公司',  icon: '📈', color: '#4ba99a', startDeg: -90, endDeg: 30  },
  { key: 'industry', label: '行业',   sub: '子板块行情',    icon: '🏭', color: '#2db87a', startDeg: 30,  endDeg: 150 },
  { key: 'macro',    label: '宏观',   sub: '经济指标',      icon: '🌐', color: '#e8a020', startDeg: 150, endDeg: 270 },
]

function toRad(deg) { return deg * Math.PI / 180 }

function arcPath(cx, cy, r, innerR, startDeg, endDeg) {
  const s = toRad(startDeg + 1)
  const e = toRad(endDeg - 1)
  const x1 = cx + r * Math.cos(s), y1 = cy + r * Math.sin(s)
  const x2 = cx + r * Math.cos(e), y2 = cy + r * Math.sin(e)
  const ix1 = cx + innerR * Math.cos(e), iy1 = cy + innerR * Math.sin(e)
  const ix2 = cx + innerR * Math.cos(s), iy2 = cy + innerR * Math.sin(s)
  return `M ${ix2} ${iy2} L ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2} L ${ix1} ${iy1} A ${innerR} ${innerR} 0 0 0 ${ix2} ${iy2} Z`
}

const segments = computed(() => SEGS_DEF.map(seg => {
  const midDeg = (seg.startDeg + seg.endDeg) / 2
  const midRad = toRad(midDeg)
  const labelDist = (r + innerR) / 2
  const pushDist = 10
  return {
    ...seg,
    path: arcPath(cx, cy, r, innerR, seg.startDeg, seg.endDeg),
    labelX: cx + labelDist * Math.cos(midRad),
    labelY: cy + labelDist * Math.sin(midRad),
    lineEnd: [
      cx + r * Math.cos(toRad(seg.endDeg)),
      cy + r * Math.sin(toRad(seg.endDeg)),
    ],
    pushX: pushDist * Math.cos(midRad),
    pushY: pushDist * Math.sin(midRad),
  }
}))
</script>

<style scoped>
.pie-legend {
  display: flex; gap: 12px;
  margin-top: 24px; flex-wrap: wrap; justify-content: center;
}
.pie-legend-item {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; color: var(--text-secondary);
  cursor: pointer; padding: 5px 12px;
  border-radius: 20px; border: 1px solid transparent;
  transition: all .2s;
}
.pie-legend-item:hover,
.pie-legend-item.active {
  color: var(--text-primary);
  border-color: var(--border-hl);
  background: rgba(75,169,154,0.08);
}
.legend-dot {
  width: 8px; height: 8px; border-radius: 50%;
  display: inline-block;
}
</style>
