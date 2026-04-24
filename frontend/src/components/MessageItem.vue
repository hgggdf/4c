<template>
  <div
    class="message-item"
    :class="message.role === 'user' ? 'message-user' : 'message-assistant'"
  >
    <div class="message-meta">
      {{ message.role === 'user' ? '我' : '⚕ 智能体' }} · {{ formatDateTime(message.createdAt) }}
    </div>

    <!-- 拖入的标的标签 -->
    <div v-if="message.targets?.length" class="msg-targets">
      <span v-for="t in message.targets" :key="t.symbol" class="msg-target-tag">
        {{ t.type === 'industry' ? '🏭' : '📈' }} {{ t.name }}
      </span>
    </div>

    <div class="msg-content">
      <template v-if="message.content">{{ message.content }}</template>
      <span v-else class="empty-hint">（等待回复…）</span>
    </div>

    <!-- 行情附带信息 -->
    <div v-if="message.extra" class="msg-quote-grid">
      <div class="msg-quote-item">
        <div class="mq-label">股票</div>
        <div class="mq-value">{{ message.extra.name }} ({{ message.extra.symbol }})</div>
      </div>
      <div class="msg-quote-item">
        <div class="mq-label">最新价</div>
        <div class="mq-value" :class="message.extra.change >= 0 ? 'red' : 'green'">
          {{ message.extra.price?.toFixed?.(2) ?? message.extra.price }}
        </div>
      </div>
      <div class="msg-quote-item">
        <div class="mq-label">涨跌幅</div>
        <div class="mq-value" :class="message.extra.change >= 0 ? 'red' : 'green'">
          {{ message.extra.change >= 0 ? '+' : '' }}{{ getChangePercent(message.extra).toFixed(2) }}%
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatDateTime } from '../utils/format'

defineProps({ message: { type: Object, required: true } })

function getChangePercent(extra = {}) {
  return Number(extra.change_pct ?? extra.change_percent ?? 0)
}
</script>

<style scoped>
.msg-targets {
  display: flex; flex-wrap: wrap; gap: 5px;
  margin-bottom: 7px;
}
.msg-target-tag {
  font-size: 11px;
  background: rgba(75,169,154,0.12);
  border: 1px solid rgba(75,169,154,0.3);
  border-radius: 20px;
  padding: 2px 8px; color: var(--accent);
}
.msg-content { white-space: pre-wrap; }

.empty-hint {
  color: var(--text-muted);
  font-style: italic;
}

.msg-quote-grid {
  display: flex; gap: 10px; flex-wrap: wrap;
  margin-top: 10px;
}
.msg-quote-item {
  background: rgba(241,245,249,0.8);
  border: 1px solid var(--border);
  border-radius: 8px; padding: 8px 12px;
  min-width: 80px;
}
.mq-label { font-size: 11px; color: var(--text-muted); }
.mq-value { font-size: 15px; font-weight: 700; margin-top: 3px; }
</style>
