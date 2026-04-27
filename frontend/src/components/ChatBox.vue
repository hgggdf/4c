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

    <div class="feature-buttons">
      <button
        v-for="item in featureButtons"
        :key="item.key"
        class="feature-btn"
        :class="{ active: activeFeature === item.key }"
        @click="selectFeature(item.key)"
      >
        <span class="feature-icon">{{ item.icon }}</span>
        <span class="feature-text">{{ item.label }}</span>
      </button>
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
          <template v-if="activeFeature">
            已选择 {{ featureButtons.find(item => item.key === activeFeature)?.label }} ·
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
        :disabled="loading || (!text.trim() && !droppedItems.length && !activeFeature)"
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

const featureButtons = [
  { key: 'company_analysis', label: '企业运营评估', icon: '🧠' },
  { key: 'financial_analysis', label: '财务分析', icon: '💹' },
  { key: 'pipeline_analysis', label: '管线分析', icon: '🧪' },
  { key: 'risk_warning', label: '风险预警', icon: '⚠️' },
  { key: 'industry_compare', label: '行业对比', icon: '🏭' },
  { key: 'report_generation', label: '生成报告', icon: '📄' },
]

const FEATURE_PROMPTS = {
  company_analysis:  '请对[公司名]进行企业运营评估，包括主营业务、竞争优势、管理层、近期经营动态。',
  financial_analysis:'请分析[公司名]的财务状况，包括营收趋势、利润率、现金流、负债结构。',
  pipeline_analysis: '请分析[公司名]的研发管线，包括在研品种、临床阶段、获批情况、商业化前景。',
  risk_warning:      '请对[公司名]进行风险预警分析，包括集采风险、监管风险、研发失败风险、财务风险。',
  industry_compare:  '请对[公司名]与同行业主要竞争对手进行对比分析，包括市场份额、财务指标、研发投入。',
  report_generation: '请为[公司名]生成一份完整的投研报告，包括公司概况、财务分析、管线分析、风险提示、投资建议。',
}

const text = ref('')
const isDragOver = ref(false)
const droppedItems = ref([])
const fileInputRef = ref(null)
const activeFeature = ref('')

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

function selectFeature(key) {
  const wasActive = activeFeature.value === key
  const oldPrompt = FEATURE_PROMPTS[activeFeature.value] || ''
  activeFeature.value = wasActive ? '' : key

  if (wasActive) {
    if (!text.value.trim() || text.value === oldPrompt) {
      text.value = ''
    }
  } else {
    if (!text.value.trim() || text.value === oldPrompt) {
      text.value = FEATURE_PROMPTS[key] || ''
    }
  }
}

function handleSubmit() {
  const msg = text.value.trim()
  const targets = droppedItems.value
  if (!msg && !targets.length && !activeFeature.value) return

  const payload = {
    message: msg,
    targets: targets.map(t => ({ symbol: t.symbol, name: t.name, type: t.type || 'stock' })),
    selected_mode: activeFeature.value || null,
  }
  emit('submit', payload)
  text.value = ''
  droppedItems.value = []
  activeFeature.value = ''
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
.feature-buttons {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  padding: 12px 12px 12px;
}
.feature-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  min-height: 42px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: linear-gradient(180deg, #fff, var(--bg-card));
  color: var(--text-primary);
  font-weight: 600;
  cursor: pointer;
  transition: all .2s ease;
  box-shadow: 0 1px 0 rgba(255,255,255,0.8) inset;
}
.feature-btn:hover {
  border-color: var(--border-hl);
  color: var(--accent2);
  background: #fff;
  box-shadow: 0 4px 12px rgba(75,169,154,0.08);
  transform: translateY(-1px);
}
.feature-btn.active {
  border-color: var(--accent2);
  background: rgba(75,169,154,0.12);
  color: var(--accent2);
  box-shadow: 0 4px 14px rgba(75,169,154,0.12);
}
.feature-icon { font-size: 15px; }
.feature-text { font-size: 13px; font-weight: 700; white-space: nowrap; }
.toolbar-left {
  display: flex; align-items: center; gap: 12px;
}

.upload-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-primary);
  font-weight: 600;
  cursor: pointer;
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-card);
  transition: all .2s;
  user-select: none;
  white-space: nowrap;
}
.upload-btn:hover {
  color: var(--accent2);
  border-color: var(--border-hl);
  background: #fff;
}

.chat-textarea {
  width: 100%; min-height: 72px; max-height: 160px;
  resize: none;
  background: transparent;
  border: none; outline: none;
  padding: 12px 14px 0;
  color: var(--text-primary);
  font-size: 14px; line-height: 1.6;
}

.chat-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 10px 8px;
}

.chat-hint {
  font-size: 12px; color: var(--text-muted);
}

.send-btn {
  border: none;
  background: var(--accent);
  color: #fff;
  border-radius: 10px;
  padding: 6px 20px;
  cursor: pointer;
  font-size: 14px; font-weight: 600;
  transition: background .2s, box-shadow .2s;
}
.send-btn:hover:not(:disabled) {
  background: #3d9688;
  box-shadow: 0 0 12px var(--accent-glow);
}
.send-btn:disabled { background: #cbd5e1; color: #94a3b8; cursor: not-allowed; }

.upload-progress {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 14px 2px;
  font-size: 12px; color: var(--text-secondary);
}
.upload-icon { font-size: 14px; }
.upload-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 160px; }
.upload-bar-wrap {
  width: 96px; height: 5px; background: var(--bg-card2);
  border-radius: 999px; overflow: hidden; flex-shrink: 0;
}
.upload-bar-fill {
  height: 100%; background: var(--accent);
  border-radius: 999px; transition: width .3s ease;
}
.upload-pct { flex-shrink: 0; }
.upload-done { color: var(--green); font-weight: 600; flex-shrink: 0; }
</style>
