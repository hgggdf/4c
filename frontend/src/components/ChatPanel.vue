<template>
  <div class="cp-root">

    <!-- 左侧：聊天记录栏 -->
    <div class="cp-sidebar">
      <div class="cp-sidebar-top">
        <span class="cp-sidebar-title">对话记录</span>
        <button class="cp-new-btn" @click="chatStore.newSession()" title="新建对话">
          <span>＋</span>
        </button>
      </div>
      <div class="cp-session-list">
        <div
          v-for="s in chatStore.sessions"
          :key="s.id"
          class="cp-session-item"
          :class="{ active: s.id === chatStore.activeSessionId }"
          @click="chatStore.switchSession(s.id)"
        >
          <div class="cp-session-icon">💬</div>
          <div class="cp-session-info">
            <div class="cp-session-title">{{ s.title }}</div>
            <div class="cp-session-meta">{{ s.updatedAt }}</div>
          </div>
          <button class="cp-delete-btn" title="删除对话" @click.stop="removeSession(s.id)">删除</button>
        </div>
      </div>
    </div>

    <!-- 右侧：聊天窗口 -->
    <div class="cp-main">

      <!-- 顶部标题栏 -->
      <div class="cp-topbar">
        <span class="cp-topbar-title">⚕ 医药投研智能体</span>
        <button class="cp-logout-btn" @click="logout" title="退出登录">退出</button>
      </div>

      <!-- 消息列表 -->
      <div class="cp-messages" ref="msgListRef">
        <div
          v-for="(msg, i) in chatStore.messages"
          :key="`${msg.createdAt}-${i}`"
          class="cp-msg-row"
          :class="msg.role === 'user' ? 'cp-msg-row--user' : 'cp-msg-row--assistant'"
        >
          <!-- 头像 -->
          <div class="cp-avatar">
            {{ msg.role === 'user' ? currentUser : '⚕' }}
          </div>

          <div class="cp-bubble-wrap">
            <!-- 标的标签 -->
            <div v-if="msg.targets?.length" class="cp-targets">
              <span v-for="t in msg.targets" :key="t.symbol" class="cp-target-tag">
                {{ t.type === 'industry' ? '🏭' : '📈' }} {{ t.name }}
              </span>
            </div>
            <!-- 模式与上下文 -->
            <div v-if="msg.role === 'assistant' && (getModeTitle(msg) || getEvidenceSummary(msg))" class="cp-context-card">
              <div v-if="getModeTitle(msg)" class="cp-context-row">
                <span class="cp-context-label">模式</span>
                <span class="cp-context-value">{{ getModeTitle(msg) }}</span>
              </div>
              <div v-if="getEvidenceSummary(msg)" class="cp-context-row">
                <span class="cp-context-label">本地证据</span>
                <span class="cp-context-value">{{ getEvidenceSummary(msg) }}</span>
              </div>
            </div>

            <!-- 气泡 -->
            <div
              v-if="shouldShowBubble(msg, i)"
              class="cp-bubble"
              :class="{ 'cp-bubble--clarification': msg.isClarification }"
            >{{ formatContent(msg) }}</div>
            <div
              v-else-if="isStreamingAssistant(msg, i)"
              class="cp-bubble cp-bubble--thinking"
            >
              <span class="cp-dot"></span><span class="cp-dot"></span><span class="cp-dot"></span>
            </div>

            <div v-if="hasToolEvents(msg)" class="cp-tool-events">
              <div v-for="(event, idx) in getToolEvents(msg)" :key="`${i}-tool-${idx}`" class="cp-tool-event">
                <template v-if="event.type === 'tool_call'">
                  <div class="cp-tool-event-head">
                    <span class="cp-tool-event-type">工具调用</span>
                    <span class="cp-tool-event-name">{{ event.tool }}</span>
                  </div>
                  <div class="cp-tool-event-body">{{ formatToolArgs(event.args) }}</div>
                </template>
                <template v-else-if="event.type === 'tool_result'">
                  <div class="cp-tool-event-head">
                    <span class="cp-tool-event-type">工具结果</span>
                    <span class="cp-tool-event-name">{{ event.tool }}</span>
                  </div>
                  <div class="cp-tool-event-body">{{ event.preview }}</div>
                </template>
                <template v-else-if="event.type === 'status'">
                  <div class="cp-tool-event-head">
                    <span class="cp-tool-event-type">状态</span>
                  </div>
                  <div class="cp-tool-event-body">{{ event.content }}</div>
                </template>
                <template v-else-if="event.type === 'clarification'">
                  <div class="cp-tool-event-head">
                    <span class="cp-tool-event-type">澄清追问</span>
                  </div>
                  <div class="cp-tool-event-body">{{ event.question }}</div>
                </template>
              </div>
            </div>

            <div v-if="msg.role === 'assistant' && (getRetrievalTrace(msg).length || getDataSources(msg).length)" class="cp-retrieval-card">
              <button class="cp-retrieval-toggle" @click="toggleRetrieval(i)">
                <span>检索与数据来源</span>
                <span>{{ expandedRetrievals.has(i) ? '收起' : '展开' }}</span>
              </button>
              <div v-if="expandedRetrievals.has(i)" class="cp-retrieval-list">
                <div v-if="getSourceNotice(msg)" class="cp-source-notice">{{ getSourceNotice(msg) }}</div>
                <div v-for="(item, idx) in getDataSources(msg)" :key="`${i}-source-${idx}`" class="cp-source-item">
                  <div class="cp-retrieval-head">
                    <span class="cp-retrieval-type">{{ item.data_type || 'data' }}</span>
                    <span class="cp-retrieval-score">{{ item.source }}</span>
                  </div>
                  <div class="cp-retrieval-title">{{ item.title || '未命名来源' }}</div>
                  <div class="cp-retrieval-snippet">置信度：{{ Number(item.confidence || 0).toFixed(2) }}</div>
                </div>
                <div v-for="(item, idx) in getRetrievalTrace(msg)" :key="`${i}-${idx}`" class="cp-retrieval-item">
                  <div class="cp-retrieval-head">
                    <span class="cp-retrieval-type">{{ item.doc_type || item.metadata?.doc_type || 'result' }}</span>
                    <span class="cp-retrieval-score">{{ Number(item.final_score ?? item.vector_score ?? item.keyword_score ?? 0).toFixed(2) }}</span>
                  </div>
                  <div class="cp-retrieval-title">{{ item.title || item.metadata?.title || '未命名结果' }}</div>
                  <div class="cp-retrieval-snippet">{{ item.snippet || item.text || item.source_record?.summary_text || item.source_record?.content || '' }}</div>
                </div>
              </div>
            </div>

            <!-- 时间 -->
            <div class="cp-time">{{ formatTime(msg.createdAt) }}</div>
          </div>
        </div>

        <!-- 思考中兜底（消息列表里最后一条 assistant 消息无内容时显示） -->
        <div v-if="(isGenerating || chatStore.loading) && !hasRenderableAssistantMessage" class="cp-msg-row cp-msg-row--assistant">
          <div class="cp-avatar">⚕</div>
          <div class="cp-bubble-wrap">
            <div class="cp-bubble cp-bubble--thinking">
              <span class="cp-dot"></span><span class="cp-dot"></span><span class="cp-dot"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="cp-input-area">
        <ChatBox :loading="chatStore.loading" @submit="handleSubmit" />
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, computed } from 'vue'
import { formatAssistantContent } from '../utils/format'
import { useRouter } from 'vue-router'
import { useChatStore } from '../store/chatStore'
import ChatBox from './ChatBox.vue'

const chatStore = useChatStore()
const router = useRouter()
const msgListRef = ref(null)
const currentUser = sessionStorage.getItem('user') || '我'
const isGenerating = computed(() => chatStore.isSessionLoading(chatStore.activeSessionId))
const expandedRetrievals = ref(new Set())
const hasRenderableAssistantMessage = computed(() =>
  chatStore.messages.some((msg, idx) => msg.role === 'assistant' && shouldShowBubble(msg, idx))
)

function scrollBottom() {
  nextTick(() => {
    if (msgListRef.value) msgListRef.value.scrollTop = msgListRef.value.scrollHeight
  })
}

function logout() {
  sessionStorage.removeItem('user')
  router.push('/login')
}

async function handleSubmit(payload) {
  await chatStore.ask(payload)
  scrollBottom()
}

async function removeSession(sessionId) {
  await chatStore.deleteSession(sessionId)
}

watch(() => chatStore.messages.map(m => `${m.role}:${m.content}`).join('|'), scrollBottom)
watch(() => chatStore.activeSessionId, scrollBottom)
watch(() => chatStore.isSessionLoading(chatStore.activeSessionId), scrollBottom)

onMounted(() => {
  chatStore.loadSessions()
})

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`
}

function isStreamingAssistant(msg) {
  return msg.role === 'assistant' && chatStore.loading && !msg.content
}

function shouldShowBubble(msg, index) {
  if (msg.role !== 'assistant') return true
  if (msg.isClarification) return true
  if (!msg.content) return false
  return true
}

function formatContent(msg) {
  if (msg.role === 'assistant') return formatAssistantContent(msg.content)
  return msg.content
}

function getRetrievalTrace(msg) {
  if (!msg || msg.role !== 'assistant') return []
  return msg.retrievalTrace || msg.toolCalls?.retrieval_trace || (Array.isArray(msg.toolCalls) ? msg.toolCalls : []) || []
}

function getModeTitle(msg) {
  if (!msg || msg.role !== 'assistant') return ''
  const mode = msg.selectedMode || msg.selected_mode || ''
  const map = {
    company_analysis: '企业运营评估',
    financial_analysis: '财务分析',
    pipeline_analysis: '管线分析',
    risk_warning: '风险预警',
    industry_compare: '行业对比',
    report_generation: '生成报告',
  }
  return map[mode] || mode
}

function getEvidenceSummary(msg) {
  if (!msg || msg.role !== 'assistant') return ''
  const items = getRetrievalTrace(msg)
  if (!items.length) return ''
  return items.slice(0, 3).map((item) => item.title || item.metadata?.title || '未命名结果').join('、')
}

function getToolEvents(msg) {
  if (!msg || msg.role !== 'assistant') return []
  return msg.toolEvents || []
}

function hasToolEvents(msg) {
  return getToolEvents(msg).length > 0
}

function formatToolArgs(args) {
  if (!args) return ''
  try {
    return typeof args === 'string' ? args : JSON.stringify(args, null, 2)
  } catch {
    return String(args)
  }
}

function getDataSources(msg) {
  if (!msg || msg.role !== 'assistant') return []
  return msg.dataSources || msg.toolCalls?.data_sources || []
}

function getSourceNotice(msg) {
  if (!msg || msg.role !== 'assistant') return ''
  return msg.sourceNotice || msg.toolCalls?.source_notice || ''
}

function toggleRetrieval(index) {
  const next = new Set(expandedRetrievals.value)
  if (next.has(index)) next.delete(index)
  else next.add(index)
  expandedRetrievals.value = next
}
</script>

<style scoped>
/* ── 根容器：撑满父级，横向分栏 ── */
.cp-root {
  display: flex;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: var(--bg-panel);
}

/* ══════════════════════════════════════
   左侧聊天记录栏
══════════════════════════════════════ */
.cp-sidebar {
  width: 200px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border-right: 1px solid var(--border);
  overflow: hidden;
}

.cp-sidebar-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  height: 44px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.cp-sidebar-title {
  font-size: 12px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.cp-new-btn {
  width: 30px; height: 30px;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  transition: all .2s ease;
  line-height: 1;
}
.cp-new-btn:hover {
  border-color: var(--border-hl);
  color: var(--accent2);
  background: #fff;
  box-shadow: 0 3px 10px rgba(75,169,154,0.08);
}

.cp-session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.cp-session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background .15s;
}
.cp-session-item:hover { background: var(--bg-card2); }
.cp-session-item.active { background: rgba(75,169,154,0.12); }

.cp-session-icon {
  font-size: 14px;
  flex-shrink: 0;
  margin-top: 1px;
  opacity: 0.6;
}
.cp-session-item.active .cp-session-icon { opacity: 1; }

.cp-session-info { min-width: 0; }
.cp-session-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  line-height: 1.4;
}
.cp-session-item.active .cp-session-title {
  color: var(--accent2);
  font-weight: 600;
}
.cp-session-meta {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 2px;
}

.cp-delete-btn {
  margin-left: auto;
  border: 1px solid var(--border);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: all .2s ease;
}
.cp-delete-btn:hover {
  color: var(--red);
  border-color: rgba(224,82,82,0.28);
  background: rgba(224,82,82,0.06);
}

/* ══════════════════════════════════════
   右侧聊天窗口
══════════════════════════════════════ */
.cp-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-panel);
}

/* 顶部标题栏 */
.cp-topbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 44px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-card);
}
.cp-topbar-title {
  font-size: 14px;
  font-weight: 800;
  color: var(--text-primary);
}
.cp-logout-btn {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 700;
  padding: 6px 12px;
  cursor: pointer;
  transition: all .2s ease;
}
.cp-logout-btn:hover {
  border-color: rgba(224,82,82,0.28);
  color: var(--red);
  background: rgba(224,82,82,0.06);
}

/* 消息列表 */
.cp-messages {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 20px 20px 8px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  scrollbar-width: thin;
  scrollbar-color: rgba(75,169,154,0.2) transparent;
}

/* 消息行 */
.cp-msg-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.cp-msg-row--user {
  flex-direction: row-reverse;
}

/* 头像 */
.cp-avatar {
  width: 32px; height: 32px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700;
  flex-shrink: 0;
  background: var(--bg-card2);
  border: 1px solid var(--border);
  color: var(--text-secondary);
}
.cp-msg-row--assistant .cp-avatar {
  background: rgba(75,169,154,0.12);
  border-color: rgba(75,169,154,0.25);
  color: var(--accent2);
}

/* 气泡包裹 */
.cp-bubble-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 78%;
}
.cp-msg-row--user .cp-bubble-wrap {
  align-items: flex-end;
}

/* 标的标签 */
.cp-targets {
  display: flex; flex-wrap: wrap; gap: 4px;
  margin-bottom: 2px;
}
.cp-target-tag {
  font-size: 11px;
  background: rgba(75,169,154,0.1);
  border: 1px solid rgba(75,169,154,0.25);
  border-radius: 20px;
  padding: 2px 8px;
  color: var(--accent2);
}

/* 气泡 */
.cp-bubble {
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-primary);
}
.cp-msg-row--user .cp-bubble {
  background: var(--accent2);
  border-color: var(--accent2);
  color: #fff;
  border-radius: 16px 4px 16px 16px;
}
.cp-msg-row--assistant .cp-bubble {
  border-radius: 4px 16px 16px 16px;
}

/* 思考中动画 */
.cp-bubble--thinking {
  display: flex; align-items: center; gap: 5px;
  padding: 12px 16px;
}
.cp-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--accent);
  display: inline-block;
  animation: cpDot 1.2s infinite ease-in-out;
}
.cp-dot:nth-child(2) { animation-delay: .2s; }
.cp-dot:nth-child(3) { animation-delay: .4s; }
@keyframes cpDot {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40%           { transform: scale(1);   opacity: 1; }
}

/* 时间 */
.cp-time {
  font-size: 10px;
  color: var(--text-muted);
  padding: 0 4px;
}

/* 输入区 */
.cp-input-area {
  flex-shrink: 0;
  padding: 12px 16px 16px;
  border-top: 1px solid var(--border);
  background: var(--bg-panel);
}

/* 模式切换 Tab */
.cp-mode-tabs {
  display: flex;
  gap: 4px;
  background: var(--bg-card2);
  border-radius: 8px;
  padding: 3px;
}
.cp-mode-tab {
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  background: none;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all .2s;
}
.cp-mode-tab:hover {
  color: var(--text-primary);
  background: rgba(75,169,154,0.08);
}
.cp-mode-tab.active {
  color: var(--accent2);
  background: var(--bg-card);
  font-weight: 600;
}

/* 澄清气泡 */
.cp-bubble--clarification {
  border-color: #f59e0b;
  background: rgba(245,158,11,0.08);
}

.cp-context-card {
  margin-top: 4px;
  padding: 8px 12px;
  border: 1px solid rgba(15,23,42,0.08);
  border-radius: 12px;
  background: rgba(248,250,252,0.95);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.cp-context-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.cp-context-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  min-width: 52px;
  flex-shrink: 0;
}
.cp-context-value {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.cp-tool-events {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.cp-tool-event {
  border: 1px solid rgba(99,102,241,0.16);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.96));
  overflow: hidden;
}
.cp-tool-event-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(99,102,241,0.08);
}
.cp-tool-event-type {
  font-size: 11px;
  font-weight: 700;
  color: #4f46e5;
}
.cp-tool-event-name {
  font-size: 11px;
  color: var(--text-muted);
}
.cp-tool-event-body {
  padding: 8px 12px 10px;
  font-size: 11px;
  line-height: 1.5;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
}
.cp-retrieval-card {
  margin-top: 6px;
  border: 1px solid rgba(75,169,154,0.16);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.96));
  overflow: hidden;
}
.cp-retrieval-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border: none;
  background: rgba(75,169,154,0.08);
  color: var(--accent2);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}
.cp-retrieval-list {
  padding: 8px 10px 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cp-retrieval-item, .cp-source-item {
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: #fff;
}
.cp-retrieval-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}
.cp-retrieval-type {
  font-size: 11px;
  color: var(--accent2);
  font-weight: 700;
}
.cp-retrieval-score {
  font-size: 11px;
  color: var(--text-muted);
}
.cp-retrieval-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}
.cp-retrieval-snippet {
  font-size: 11px;
  line-height: 1.5;
  color: var(--text-secondary);
  margin: 0;
}
.cp-source-notice {
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(59,130,246,0.08);
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
  border: 1px solid rgba(59,130,246,0.12);
}
</style>
