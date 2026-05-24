<template>
  <div class="at-root">
    <div class="at-header" @click="expanded = !expanded">
      <span class="at-icon">🔗</span>
      <span class="at-title">Agent 推理过程</span>
      <span class="at-badge">{{ steps.length }} 步</span>
      <span class="at-toggle">{{ expanded ? '▲' : '▼' }}</span>
    </div>

    <div v-if="expanded" class="at-body">
      <div v-for="(step, i) in steps" :key="i" class="at-step" :class="`at-step--${step.type}`">

        <template v-if="step.type === 'thinking'">
          <div class="at-step-icon">🧠</div>
          <div class="at-step-content">
            <div class="at-step-label">思考</div>
            <div class="at-step-text">{{ step.content }}</div>
          </div>
        </template>

        <template v-else-if="step.type === 'tool_call'">
          <div class="at-step-icon">🔧</div>
          <div class="at-step-content">
            <div class="at-step-label">调用工具 <span class="at-tool-name">{{ step.tool }}</span></div>
            <div class="at-step-args">
              <span v-for="(val, key) in step.args" :key="key" class="at-arg">
                <span class="at-arg-key">{{ key }}</span>
                <span class="at-arg-val">{{ formatVal(val) }}</span>
              </span>
            </div>
          </div>
        </template>

        <template v-else-if="step.type === 'tool_result'">
          <div class="at-step-icon">📄</div>
          <div class="at-step-content">
            <div class="at-step-label">结果来自 <span class="at-source-tag">{{ step.source }}</span></div>
            <div class="at-step-preview">{{ step.preview }}</div>
          </div>
        </template>

        <template v-else-if="step.type === 'status'">
          <div class="at-step-icon">⏳</div>
          <div class="at-step-content">
            <div class="at-step-text at-muted">{{ step.content }}</div>
          </div>
        </template>

      </div>

      <div v-if="loading" class="at-loading">
        <span class="at-dot"></span><span class="at-dot"></span><span class="at-dot"></span>
        <span class="at-loading-text">Agent 正在思考...</span>
      </div>
    </div>

    <div v-if="sources.length" class="at-sources">
      <span class="at-sources-label">📎 数据来源：</span>
      <span v-for="(src, i) in sources" :key="i" class="at-source-chip">{{ src }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  steps: { type: Array, default: () => [] },
  sources: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const expanded = ref(false)

function formatVal(val) {
  if (Array.isArray(val)) return val.join(', ')
  if (typeof val === 'object' && val !== null) return JSON.stringify(val)
  return String(val)
}
</script>

<style scoped>
.at-root {
  margin: 6px 0 4px;
  border: 1px solid rgba(75,169,154,0.25);
  border-radius: 10px;
  overflow: hidden;
  font-size: 12px;
  background: rgba(75,169,154,0.04);
}
.at-header {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px; cursor: pointer;
  background: rgba(75,169,154,0.08);
  user-select: none;
}
.at-header:hover { background: rgba(75,169,154,0.14); }
.at-title { font-weight: 700; color: var(--accent2, #4ba99a); flex: 1; }
.at-badge {
  font-size: 10px; background: rgba(75,169,154,0.18);
  color: var(--accent2, #4ba99a); border-radius: 20px; padding: 1px 7px; font-weight: 600;
}
.at-toggle { color: #999; font-size: 10px; }
.at-body {
  padding: 8px 10px; display: flex; flex-direction: column; gap: 6px;
  max-height: 360px; overflow-y: auto; scrollbar-width: thin;
}
.at-step {
  display: flex; gap: 8px; align-items: flex-start;
  padding: 6px 8px; border-radius: 7px; border: 1px solid transparent;
}
.at-step--thinking  { background: rgba(99,102,241,0.05); border-color: rgba(99,102,241,0.15); }
.at-step--tool_call { background: rgba(245,158,11,0.05); border-color: rgba(245,158,11,0.2); }
.at-step--tool_result { background: rgba(16,185,129,0.05); border-color: rgba(16,185,129,0.18); }
.at-step-icon { font-size: 14px; flex-shrink: 0; margin-top: 1px; }
.at-step-content { flex: 1; min-width: 0; }
.at-step-label {
  font-weight: 600; color: #666; margin-bottom: 3px;
  display: flex; align-items: center; gap: 5px; flex-wrap: wrap;
}
.at-tool-name {
  font-family: monospace; font-size: 11px;
  background: rgba(245,158,11,0.12); color: #b45309;
  border-radius: 4px; padding: 1px 5px;
}
.at-source-tag {
  font-size: 11px; background: rgba(16,185,129,0.1); color: #047857;
  border-radius: 4px; padding: 1px 5px;
}
.at-step-args { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 2px; }
.at-arg {
  display: flex; align-items: center; gap: 3px;
  background: rgba(0,0,0,0.04); border-radius: 4px; padding: 1px 6px;
}
.at-arg-key { color: #999; font-size: 10px; }
.at-arg-val { color: #333; font-size: 11px; font-weight: 500; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.at-step-text { color: #333; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }
.at-step-preview { color: #555; line-height: 1.5; white-space: pre-wrap; word-break: break-word; font-size: 11px; max-height: 80px; overflow: hidden; }
.at-muted { color: #999; font-style: italic; }
.at-loading { display: flex; align-items: center; gap: 4px; padding: 4px 8px; color: #999; }
.at-loading-text { font-size: 11px; margin-left: 4px; }
.at-dot {
  width: 5px; height: 5px; border-radius: 50%;
  background: var(--accent, #4ba99a); display: inline-block;
  animation: atDot 1.2s infinite ease-in-out;
}
.at-dot:nth-child(2) { animation-delay: .2s; }
.at-dot:nth-child(3) { animation-delay: .4s; }
@keyframes atDot {
  0%,80%,100% { transform: scale(0.6); opacity: 0.4; }
  40%          { transform: scale(1);   opacity: 1; }
}
.at-sources {
  display: flex; flex-wrap: wrap; align-items: center; gap: 5px;
  padding: 6px 12px 8px; border-top: 1px solid rgba(75,169,154,0.15);
}
.at-sources-label { font-size: 11px; color: #999; font-weight: 600; }
.at-source-chip {
  font-size: 10px; background: rgba(75,169,154,0.1);
  color: var(--accent2, #4ba99a); border: 1px solid rgba(75,169,154,0.2);
  border-radius: 20px; padding: 1px 8px;
}
</style>
