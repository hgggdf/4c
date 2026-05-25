<template>
  <div class="rnpv-card">
    <div class="rnpv-header">
      <span class="rnpv-title">管线 rNPV 估值</span>
      <span class="rnpv-drug">{{ data.drug_name }} · {{ data.indication }}</span>
      <span class="rnpv-phase">{{ phaseLabel }}</span>
    </div>

    <div class="rnpv-scenarios">
      <div
        v-for="(key, i) in ['bear', 'base', 'bull']"
        :key="key"
        :class="['scenario-item', key, { active: key === 'base' }]"
      >
        <div class="scenario-label">{{ data.scenarios[key].label }}</div>
        <div class="scenario-value">
          {{ formatYi(data.scenarios[key].rnpv_yi) }}
          <span class="unit">亿元</span>
        </div>
        <div class="scenario-pos">PoS {{ data.scenarios[key].pos_pct }}%</div>
      </div>
    </div>

    <div class="rnpv-bar">
      <div class="bar-track">
        <div class="bar-range" :style="barStyle" />
        <div class="bar-base" :style="baseMarkerStyle" />
      </div>
      <div class="bar-labels">
        <span>悲观 {{ formatYi(data.scenarios.bear.rnpv_yi) }}亿</span>
        <span>乐观 {{ formatYi(data.scenarios.bull.rnpv_yi) }}亿</span>
      </div>
    </div>

    <div class="rnpv-assumptions">
      <div class="assumption-title">关键假设</div>
      <div class="assumption-grid">
        <div class="assumption-item">
          <span class="key">折现率</span>
          <span class="val">{{ data.assumptions.wacc_pct }}%</span>
        </div>
        <div class="assumption-item">
          <span class="key">净利润率</span>
          <span class="val">{{ data.assumptions.net_margin_pct }}%</span>
        </div>
        <div class="assumption-item">
          <span class="key">患者数</span>
          <span class="val">{{ data.scenarios.base.details.patients_wan }}万人</span>
        </div>
        <div class="assumption-item">
          <span class="key">峰值份额</span>
          <span class="val">{{ data.scenarios.base.details.peak_share_pct }}%</span>
        </div>
        <div class="assumption-item">
          <span class="key">年治疗费</span>
          <span class="val">{{ data.scenarios.base.details.price_wan }}万元/人</span>
        </div>
        <div class="assumption-item">
          <span class="key">数据来源</span>
          <span class="val source">{{ data.assumptions.data_source }}</span>
        </div>
      </div>
    </div>

    <div v-if="data.warnings && data.warnings.length" class="rnpv-warnings">
      <div v-for="w in data.warnings" :key="w" class="warning-item">⚠ {{ w }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Object, required: true },
})

const PHASE_LABELS = {
  phase1: 'Phase I',
  phase2: 'Phase II',
  phase3: 'Phase III',
  nda: 'NDA申报',
  approved: '已上市',
}

const phaseLabel = computed(() => PHASE_LABELS[props.data.trial_phase] || props.data.trial_phase)

function formatYi(val) {
  if (val === null || val === undefined) return '--'
  return val >= 0 ? `+${val.toFixed(1)}` : val.toFixed(1)
}

const barStyle = computed(() => {
  const bear = props.data.scenarios.bear.rnpv_yi
  const bull = props.data.scenarios.bull.rnpv_yi
  const min = Math.min(bear, 0) - 5
  const max = Math.max(bull, 0) + 5
  const range = max - min
  const left = ((bear - min) / range) * 100
  const right = ((bull - min) / range) * 100
  return { left: `${left}%`, width: `${right - left}%` }
})

const baseMarkerStyle = computed(() => {
  const bear = props.data.scenarios.bear.rnpv_yi
  const bull = props.data.scenarios.bull.rnpv_yi
  const base = props.data.scenarios.base.rnpv_yi
  const min = Math.min(bear, 0) - 5
  const max = Math.max(bull, 0) + 5
  const range = max - min
  const pos = ((base - min) / range) * 100
  return { left: `${pos}%` }
})
</script>

<style scoped>
.rnpv-card {
  background: var(--color-bg-card, #1a1f2e);
  border: 1px solid var(--color-border, #2d3548);
  border-radius: 10px;
  padding: 16px;
  margin: 8px 0;
  font-size: 13px;
}

.rnpv-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.rnpv-title {
  font-weight: 600;
  color: var(--color-accent, #7c9ff5);
  font-size: 14px;
}

.rnpv-drug {
  color: var(--color-text-primary, #e2e8f0);
  font-size: 13px;
}

.rnpv-phase {
  background: rgba(124, 159, 245, 0.15);
  color: var(--color-accent, #7c9ff5);
  border-radius: 4px;
  padding: 1px 7px;
  font-size: 11px;
  margin-left: auto;
}

.rnpv-scenarios {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}

.scenario-item {
  flex: 1;
  text-align: center;
  padding: 10px 6px;
  border-radius: 8px;
  border: 1px solid var(--color-border, #2d3548);
  background: rgba(255, 255, 255, 0.03);
}

.scenario-item.active {
  border-color: var(--color-accent, #7c9ff5);
  background: rgba(124, 159, 245, 0.08);
}

.scenario-label {
  font-size: 11px;
  color: var(--color-text-muted, #8892a4);
  margin-bottom: 4px;
}

.scenario-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary, #e2e8f0);
}

.scenario-item.bear .scenario-value { color: #ef4444; }
.scenario-item.bull .scenario-value { color: #22c55e; }

.unit {
  font-size: 11px;
  font-weight: 400;
  color: var(--color-text-muted, #8892a4);
  margin-left: 2px;
}

.scenario-pos {
  font-size: 11px;
  color: var(--color-text-muted, #8892a4);
  margin-top: 3px;
}

.rnpv-bar {
  margin-bottom: 14px;
}

.bar-track {
  position: relative;
  height: 6px;
  background: var(--color-border, #2d3548);
  border-radius: 3px;
  margin-bottom: 4px;
}

.bar-range {
  position: absolute;
  height: 100%;
  background: linear-gradient(90deg, #ef4444, #7c9ff5, #22c55e);
  border-radius: 3px;
  opacity: 0.6;
}

.bar-base {
  position: absolute;
  top: -3px;
  width: 3px;
  height: 12px;
  background: var(--color-accent, #7c9ff5);
  border-radius: 2px;
  transform: translateX(-50%);
}

.bar-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--color-text-muted, #8892a4);
}

.rnpv-assumptions {
  border-top: 1px solid var(--color-border, #2d3548);
  padding-top: 10px;
  margin-bottom: 8px;
}

.assumption-title {
  font-size: 11px;
  color: var(--color-text-muted, #8892a4);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.assumption-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}

.assumption-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.key {
  color: var(--color-text-muted, #8892a4);
  font-size: 11px;
}

.val {
  color: var(--color-text-primary, #e2e8f0);
  font-size: 11px;
  font-weight: 500;
}

.val.source {
  font-size: 10px;
  color: var(--color-text-muted, #8892a4);
}

.rnpv-warnings {
  border-top: 1px solid var(--color-border, #2d3548);
  padding-top: 8px;
}

.warning-item {
  font-size: 11px;
  color: #f59e0b;
  margin-bottom: 3px;
}
</style>
