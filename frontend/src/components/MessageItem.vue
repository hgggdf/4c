<template>
  <div
    class="message-item"
    :class="message.role === 'user' ? 'message-user' : 'message-assistant'"
  >
    <div class="message-meta">
      {{ message.role === 'user' ? '我' : '智能体' }} · {{ formatDateTime(message.createdAt) }}
    </div>
    <div>{{ message.content }}</div>

    <div v-if="message.extra" class="quote-grid" style="margin-top: 12px;">
      <div class="quote-box">
        <div class="quote-label">股票</div>
        <div class="quote-value">{{ message.extra.name }} ({{ message.extra.symbol }})</div>
      </div>
      <div class="quote-box">
        <div class="quote-label">最新价</div>
        <div class="quote-value" :class="getChangeClass(message.extra.change)">
          {{ message.extra.price }}
        </div>
      </div>
      <div class="quote-box">
        <div class="quote-label">涨跌额</div>
        <div class="quote-value" :class="getChangeClass(message.extra.change)">
          {{ message.extra.change }}
        </div>
      </div>
      <div class="quote-box">
        <div class="quote-label">涨跌幅</div>
        <div class="quote-value" :class="getChangeClass(message.extra.change)">
          {{ message.extra.change_percent }}%
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatDateTime, getChangeClass } from '../utils/format'

defineProps({
  message: {
    type: Object,
    required: true
  }
})
</script>
