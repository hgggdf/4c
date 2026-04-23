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
            <!-- 气泡 -->
            <div class="cp-bubble">{{ msg.content }}</div>
            <!-- 时间 -->
            <div class="cp-time">{{ formatTime(msg.createdAt) }}</div>
          </div>
        </div>

        <!-- 思考中 -->
        <div v-if="chatStore.loading" class="cp-msg-row cp-msg-row--assistant">
          <div class="cp-avatar">⚕</div>
          <div class="cp-bubble-wrap">
            <div class="cp-bubble cp-bubble--thinking">
              <span class="cp-dot"/><span class="cp-dot"/><span class="cp-dot"/>
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
import { ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '../store/chatStore'
import ChatBox from './ChatBox.vue'

const chatStore = useChatStore()
const router = useRouter()
const msgListRef = ref(null)
const currentUser = sessionStorage.getItem('user') || '我'

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

watch(() => chatStore.messages.length, scrollBottom)
watch(() => chatStore.activeSessionId, scrollBottom)

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`
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
  font-weight: 700;
  color: var(--text-secondary);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.cp-new-btn {
  width: 26px; height: 26px;
  display: flex; align-items: center; justify-content: center;
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-muted);
  font-size: 16px;
  cursor: pointer;
  transition: all .2s;
  line-height: 1;
}
.cp-new-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(75,169,154,0.08);
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
  align-items: flex-start;
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
  font-weight: 500;
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
  font-weight: 700;
  color: var(--accent2);
}
.cp-logout-btn {
  background: none;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 12px;
  padding: 4px 10px;
  cursor: pointer;
  transition: all .2s;
}
.cp-logout-btn:hover {
  border-color: var(--red);
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
</style>
