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

    <!-- 已拖入的新闻标签 -->
    <div v-if="droppedNews.length" class="dragged-news-tags">
      <div v-for="n in droppedNews" :key="n.id" class="dragged-news-tag">
        <span class="dragged-news-icon">📰</span>
        <span class="dragged-news-title">{{ n.title }}</span>
        <span class="rm" @click="removeNews(n.id)">×</span>
      </div>
    </div>

    <!-- 已上传的文件标签 -->
    <div v-if="uploadedFiles.length" class="dragged-tags">
      <span v-for="f in uploadedFiles" :key="f.name" class="dragged-tag dragged-tag--file">
        {{ f.icon }} {{ f.name }}
        <span class="rm" @click="removeFile(f.name)">×</span>
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
      <span class="upload-icon">{{ uploadState.icon }}</span>
      <span class="upload-name">{{ uploadState.fileName }}</span>
      <div class="upload-bar-wrap">
        <div class="upload-bar-fill" :style="{ width: uploadState.percent + '%' }"></div>
      </div>
      <span class="upload-pct">{{ uploadState.percent }}%</span>
      <span v-if="uploadState.done" class="upload-done">✓ {{ uploadState.doneMsg }}</span>
    </div>

    <!-- 行业对比使用引导 -->
    <div v-if="activeFeature === 'industry_compare' && guideVisible" class="compare-guide">
      <span class="compare-guide-icon">💡</span>
      <div class="compare-guide-text">
        <strong>行业对比使用方式：</strong>
        <span>① 直接发送 → 对比库内所有公司</span>
        <span>② 从左侧拖入多个个股 → 只对比拖入的公司</span>
        <span>③ 拖入一家公司 → 以该公司为主与同行对比</span>
      </div>
      <button class="compare-guide-close" @click.stop="guideVisible = false">×</button>
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
        <!-- 上传文档按钮 -->
        <label class="upload-btn" title="上传文档到知识库（支持 PDF / Word / TXT / Excel）">
          <input
            ref="fileInputRef"
            type="file"
            accept=".pdf,.docx,.txt,.xlsx,.xls"
            style="display:none"
            @change="handleFileChange"
          />
          📎 上传文档
        </label>
      </div>
      <button
        class="send-btn"
        :disabled="loading || (!text.trim() && !droppedItems.length && !droppedNews.length && !activeFeature)"
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
import { uploadDoc } from '../api/chat'
import { useChatStore } from '../store/chatStore'

const props = defineProps({
  loading: { type: Boolean, default: false }
})
const emit = defineEmits(['submit'])
const chatStore = useChatStore()

const featureButtons = [
  { key: 'company_analysis', label: '企业运营评估', icon: '🧠' },
  { key: 'financial_analysis', label: '财务分析', icon: '💹' },
  { key: 'pipeline_analysis', label: '管线分析', icon: '🧪' },
  { key: 'butterfly_analysis', label: '蝴蝶效应', icon: '🦋' },
  { key: 'risk_warning', label: '风险预警', icon: '⚠️' },
  { key: 'industry_compare', label: '行业对比', icon: '🏭' },
  { key: 'report_generation', label: '生成报告', icon: '📄' },
  { key: 'attribution_analysis', label: '归因分析', icon: '🔍' },
]

const FEATURE_PROMPTS = {
  company_analysis:      '请对[公司名]进行企业运营评估，包括主营业务、竞争优势、管理层、近期经营动态。',
  financial_analysis:    '请分析[公司名]的财务状况，包括营收趋势、利润率、现金流、负债结构。',
  pipeline_analysis:     '请分析[公司名]的研发管线，包括在研品种、临床阶段、获批情况、商业化前景。',
  butterfly_analysis:    '请分析以下宏观事件的蝴蝶效应传导链路，从宏观→行业→公司逐层推演影响，并给出风险提示和投资机会：',
  risk_warning:          '请对[公司名]进行风险预警分析，包括集采风险、监管风险、研发失败风险、财务风险。',
  industry_compare:      '请对[公司名]与同行业主要竞争对手进行对比分析，包括市场份额、财务指标、研发投入。',
  report_generation:     '请为[公司名]生成一份完整的投研报告，包括公司概况、财务分析、管线分析、风险提示、投资建议。',
  attribution_analysis:  '请对[公司名]进行归因分析，拆解近期业绩/股价变动的内外部驱动因素。',
}

const text = ref('')
const isDragOver = ref(false)
const droppedItems = ref([])
const droppedNews = ref([])
const fileInputRef = ref(null)
const activeFeature = ref('')
const guideVisible = ref(true)

const uploadState = ref({ active: false, fileName: '', percent: 0, done: false, icon: '📄', doneMsg: '已入库' })
const uploadedFiles = ref([])

const FILE_ICONS = { pdf: '📕', docx: '📝', txt: '📄', xlsx: '📊', xls: '📊' }

function getFileIcon(name) {
  const ext = (name || '').split('.').pop().toLowerCase()
  return FILE_ICONS[ext] || '📄'
}

const placeholder = computed(() => {
  if (droppedNews.value.length && droppedItems.value.length)
    return `已选中新闻和 ${droppedItems.value.map(i=>i.name).join('、')}，输入分析问题…`
  if (droppedNews.value.length)
    return `已选中 ${droppedNews.value.length} 条新闻，输入问题或直接发送让 AI 解读…`
  if (droppedItems.value.length)
    return `已选中 ${droppedItems.value.map(i=>i.name).join('、')}，输入分析问题…`
  return '请输入问题，或将个股/行业/新闻卡片拖入此处进行分析…'
})

function onDrop(evt) {
  isDragOver.value = false
  try {
    const item = JSON.parse(evt.dataTransfer.getData('application/json'))
    if (item.type === 'news') {
      if (!droppedNews.value.find(x => x.id === item.id)) {
        droppedNews.value.push(item)
        if (!text.value.trim()) {
          text.value = '请分析这条新闻对相关公司/行业的影响。'
        }
      }
    } else {
      if (!droppedItems.value.find(x => x.symbol === item.symbol)) {
        droppedItems.value.push(item)
        if (activeFeature.value) {
          text.value = resolvePrompt(activeFeature.value)
        }
      }
    }
  } catch {}
}

function removeFile(name) {
  uploadedFiles.value = uploadedFiles.value.filter(f => f.name !== name)
}

function removeNews(id) {
  droppedNews.value = droppedNews.value.filter(x => x.id !== id)
}

function removeItem(symbol) {
  droppedItems.value = droppedItems.value.filter(x => x.symbol !== symbol)
  if (activeFeature.value) {
    text.value = resolvePrompt(activeFeature.value)
  }
}

function resolvePrompt(key) {
  const names = droppedItems.value.map(i => i.name)

  // industry_compare 根据拖入公司数量生成不同句式
  if (key === 'industry_compare') {
    if (names.length === 0) {
      return '请对医药行业主要公司进行对比分析，包括市场份额、财务指标、研发投入。'
    } else if (names.length === 1) {
      return `请对${names[0]}与同行业主要竞争对手进行对比分析，包括市场份额、财务指标、研发投入。`
    } else {
      return `请对${names.join('、')}进行行业对比分析，包括市场份额、财务指标、研发投入。`
    }
  }

  const raw = FEATURE_PROMPTS[key] || ''
  if (!names.length) return raw
  return raw.replace(/\[公司名\]/g, names.join('、'))
}

function selectFeature(key) {
  const wasActive = activeFeature.value === key
  const oldPrompt = resolvePrompt(activeFeature.value)
  activeFeature.value = wasActive ? '' : key
  if (!wasActive && key === 'industry_compare') guideVisible.value = true

  if (wasActive) {
    if (!text.value.trim() || text.value === oldPrompt) {
      text.value = ''
    }
  } else {
    if (!text.value.trim() || text.value === oldPrompt) {
      text.value = resolvePrompt(key)
    }
  }
}

function handleSubmit() {
  const targets = droppedItems.value
  const names = targets.map(t => t.name)
  const rawMsg = text.value.trim()
  const msg = names.length ? rawMsg.replace(/\[公司名\]/g, names.join('、')) : rawMsg

  // 把拖入的新闻内容拼到消息前面
  let finalMsg = msg
  if (droppedNews.value.length) {
    const newsBlock = droppedNews.value.map(n => {
      const lines = [`【新闻】${n.title}`]
      if (n.source) lines.push(`来源：${n.source}  时间：${n.time}`)
      if (n.summary) lines.push(n.summary)
      return lines.join('\n')
    }).join('\n\n')
    finalMsg = newsBlock + (msg ? '\n\n' + msg : '\n\n请分析这条新闻对相关公司/行业的影响。')
  }

  if (!finalMsg && !targets.length && !activeFeature.value) return

  const payload = {
    message: finalMsg,
    targets: targets.map(t => ({ symbol: t.symbol, name: t.name, type: t.type || 'stock' })),
    selected_mode: activeFeature.value || null,
  }
  emit('submit', payload)
  text.value = ''
  droppedItems.value = []
  droppedNews.value = []
  uploadedFiles.value = []
  activeFeature.value = ''
}

async function handleFileChange(evt) {
  const file = evt.target.files?.[0]
  if (!file) return

  uploadState.value = {
    active: true,
    fileName: file.name,
    percent: 0,
    done: false,
    icon: getFileIcon(file.name),
    doneMsg: '已入库',
  }

  try {
    const res = await uploadDoc(file, pct => {
      uploadState.value.percent = pct
    }, chatStore.activeSessionId)
    uploadState.value.percent = 100
    uploadState.value.done = true
    uploadState.value.doneMsg = res?.message || '已入库'
    uploadedFiles.value.push({ name: file.name, icon: getFileIcon(file.name) })
    setTimeout(() => { uploadState.value.active = false }, 2000)
  } catch (err) {
    uploadState.value.active = false
    alert('上传失败：' + (err?.response?.data?.detail || err.message))
  } finally {
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
}
</script>

<style scoped>
.feature-buttons {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
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

/* 行业对比引导条 */
.compare-guide {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 0 12px 8px;
  padding: 10px 12px;
  background: linear-gradient(135deg, rgba(75,169,154,0.08), rgba(99,102,241,0.06));
  border: 1px solid rgba(75,169,154,0.25);
  border-radius: 10px;
  font-size: 12px;
  color: var(--text-secondary);
  animation: guideIn .2s ease;
}
@keyframes guideIn {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}
.compare-guide-icon {
  font-size: 15px;
  flex-shrink: 0;
  margin-top: 1px;
}
.compare-guide-text {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  line-height: 1.6;
}
.compare-guide-text strong {
  width: 100%;
  color: var(--text-primary);
  font-size: 12px;
}
.compare-guide-text span {
  color: var(--text-secondary);
  white-space: nowrap;
}
.compare-guide-close {
  flex-shrink: 0;
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
  padding: 0 2px;
  margin-top: -1px;
  transition: color .15s;
}
.compare-guide-close:hover { color: var(--text-primary); }

/* 拖入的新闻标签 */
.dragged-news-tags {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 12px 0;
}
.dragged-news-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  background: rgba(99,102,241,0.08);
  border: 1px solid rgba(99,102,241,0.2);
  border-radius: 8px;
  font-size: 12px;
  color: #4f46e5;
  animation: guideIn .15s ease;
}
.dragged-news-icon { font-size: 13px; flex-shrink: 0; }
.dragged-news-title {
  flex: 1;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-weight: 500;
}
.dragged-news-tag .rm {
  cursor: pointer;
  opacity: .6;
  font-size: 14px;
  line-height: 1;
  flex-shrink: 0;
}
.dragged-news-tag .rm:hover { opacity: 1; }

/* 已上传文件标签 */
.dragged-tag--file {
  background: rgba(245,158,11,0.08);
  border-color: rgba(245,158,11,0.35);
  color: #b45309;
}
</style>
