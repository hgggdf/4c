<template>
  <!-- 对话输入区 -->
  <div
    class="chat-box"
    :class="{ 'chat-box-drop': isDragOver }"
    @dragover.prevent="isDragOver = true"
    @dragleave="isDragOver = false"
    @drop.prevent="onDrop"
  >
    <!-- 已拖入的标的标签 -->
    <div v-if="droppedItems.length" class="dragged-tags">
      <span v-for="item in droppedItems" :key="item.symbol" class="dragged-tag">
        {{ item.type === 'industry' ? '🏭' : '📈' }} {{ item.name }}
        <span class="rm" @click="removeItem(item.symbol)">×</span>
      </span>
    </div>

    <textarea
      v-model="text"
      class="chat-textarea"
      :placeholder="placeholder"
      rows="3"
      @keydown.enter.exact.prevent="handleSubmit"
    />

    <div class="chat-toolbar">
      <span class="chat-hint">
        <template v-if="droppedItems.length">
          已添加 {{ droppedItems.length }} 个标的 · 
        </template>
        Enter 发送 · Shift+Enter 换行
      </span>
      <button
        class="send-btn"
        :disabled="loading || (!text.trim() && !droppedItems.length)"
        @click="handleSubmit"
      >
        <span v-if="loading">思考中…</span>
        <span v-else>发送</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  loading: { type: Boolean, default: false }
})
const emit = defineEmits(['submit'])

const text = ref('')
const isDragOver = ref(false)
const droppedItems = ref([])

const placeholder = computed(() =>
  droppedItems.value.length
    ? `已选中 ${droppedItems.value.map(i=>i.name).join('、')}，输入分析问题…`
    : '请输入问题，或将个股/行业卡片拖入此处进行多标的联合分析…'
)

function onDrop(evt) {
  isDragOver.value = false
  try {
    const item = JSON.parse(evt.dataTransfer.getData('application/json'))
    if (!droppedItems.value.find(x => x.symbol === item.symbol)) {
      droppedItems.value.push(item)
    }
  } catch {}
}

function removeItem(symbol) {
  droppedItems.value = droppedItems.value.filter(x => x.symbol !== symbol)
}

function handleSubmit() {
  const msg = text.value.trim()
  const targets = droppedItems.value
  if (!msg && !targets.length) return

  const payload = {
    message: msg,
    targets: targets.map(t => ({ symbol: t.symbol, name: t.name, type: t.type || 'stock' })),
  }
  emit('submit', payload)
  text.value = ''
  droppedItems.value = []
}
</script>
