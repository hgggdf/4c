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

    <!-- PDF 上传进度 -->
    <div v-if="uploadState.active" class="upload-progress">
      <span class="upload-icon">📄</span>
      <span class="upload-name">{{ uploadState.fileName }}</span>
      <div class="upload-bar-wrap">
        <div class="upload-bar-fill" :style="{ width: uploadState.percent + '%' }"></div>
      </div>
      <span class="upload-pct">{{ uploadState.percent }}%</span>
      <span v-if="uploadState.done" class="upload-done">✓ 已入库</span>
    </div>

    <textarea
      v-model="text"
      class="chat-textarea"
      :placeholder="placeholder"
      rows="3"
      @keydown.enter.exact.prevent="handleSubmit"
    />

    <div class="chat-toolbar">
      <div class="toolbar-left">
        <span class="chat-hint">
          <template v-if="droppedItems.length">
            已添加 {{ droppedItems.length }} 个标的 ·
          </template>
          Enter 发送 · Shift+Enter 换行
        </span>
        <!-- PDF 上传按钮 -->
        <label class="upload-btn" title="上传 PDF 到知识库">
          <input
            ref="fileInputRef"
            type="file"
            accept=".pdf"
            style="display:none"
            @change="handleFileChange"
          />
          📎 上传研报
        </label>
      </div>
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
import { uploadPDF } from '../api/chat'

const props = defineProps({
  loading: { type: Boolean, default: false }
})
const emit = defineEmits(['submit'])

const text = ref('')
const isDragOver = ref(false)
const droppedItems = ref([])
const fileInputRef = ref(null)

const uploadState = ref({ active: false, fileName: '', percent: 0, done: false })

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

async function handleFileChange(evt) {
  const file = evt.target.files?.[0]
  if (!file) return

  uploadState.value = { active: true, fileName: file.name, percent: 0, done: false }

  try {
    await uploadPDF(file, pct => {
      uploadState.value.percent = pct
    })
    uploadState.value.percent = 100
    uploadState.value.done = true
    setTimeout(() => { uploadState.value.active = false }, 3000)
  } catch (err) {
    uploadState.value.active = false
    alert('上传失败：' + err.message)
  } finally {
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
}
</script>

<style scoped>
.toolbar-left {
  display: flex; align-items: center; gap: 10px;
}

.upload-btn {
  font-size: 12px; color: var(--text-secondary);
  cursor: pointer; padding: 3px 8px;
  border: 1px solid var(--border); border-radius: 6px;
  transition: all .2s; user-select: none;
  white-space: nowrap;
}
.upload-btn:hover { color: var(--accent); border-color: var(--border-hl); }

.upload-progress {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 14px 0;
  font-size: 12px; color: var(--text-secondary);
}
.upload-icon { font-size: 14px; }
.upload-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 160px; }
.upload-bar-wrap {
  width: 80px; height: 4px; background: var(--bg-card2);
  border-radius: 2px; overflow: hidden; flex-shrink: 0;
}
.upload-bar-fill {
  height: 100%; background: var(--accent);
  border-radius: 2px; transition: width .3s ease;
}
.upload-pct { flex-shrink: 0; }
.upload-done { color: var(--green); font-weight: 600; flex-shrink: 0; }
</style>
