<template>
  <div class="main-wrap" ref="wrapRef">

    <!-- ══════════════════════════════════════════
         左侧：探索区（从左边缘向右滑出）
    ═══════════════════════════════════════════ -->
    <div class="explore-side" :style="exploreSideStyle">
      <!-- 顶部三 Tab -->
      <div class="explore-tabs">
        <button
          v-for="tab in TABS"
          :key="tab.key"
          class="explore-tab-btn"
          :class="{ active: activeSection === tab.key }"
          @click="onSectionSelect(tab.key)"
        >
          <span class="tab-icon">{{ tab.icon }}</span>
          {{ tab.label }}
        </button>
      </div>

      <!-- 内容区 -->
      <div class="content-area">
        <div class="content-area-inner">

          <template v-if="activeSection === 'stock'">
            <Transition name="detail-slide" mode="out-in">
              <StockDetailPanel
                v-if="selectedStock"
                :key="selectedStock.symbol"
                :stock="selectedStock"
                @back="selectedStock = null"
              />
              <StockGrid
                v-else
                mode="stock"
                :stocks="stocks"
                @open-detail="selectedStock = $event"
              />
            </Transition>
          </template>

          <template v-else-if="activeSection === 'industry'">
            <StockGrid
              mode="industry"
              :industries="industries"
              @open-industry="onIndustryClick"
            />
          </template>

          <template v-else-if="activeSection === 'macro'">
            <MacroPanel />
          </template>

        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════
         把手 — 贴在探索区右边界
    ═══════════════════════════════════════════ -->
    <div
      class="edge-handle"
      :class="{
        'handle-hover': isHovering,
        'handle-drag':  isDragging,
      }"
      :style="handleStyle"
      @mousedown.prevent="onDragStart"
      @mouseenter="isHovering = true"
      @mouseleave="isHovering = false"
    >
      <div class="handle-ripple ripple-1"></div>
      <div class="handle-ripple ripple-2"></div>
      <div class="handle-ripple ripple-3"></div>
      <div class="handle-arrow">{{ panelOpen ? '‹' : '›' }}</div>
    </div>

    <!-- ══════════════════════════════════════════
         右侧：对话区
    ═══════════════════════════════════════════ -->
    <div class="chat-side" :style="chatSideStyle">
      <div class="chat-panel">
        <div ref="msgListRef" class="message-list">
          <MessageItem
            v-for="(msg, i) in chatStore.messages"
            :key="`${msg.createdAt}-${i}`"
            :message="msg"
          />
          <div v-if="chatStore.loading" class="message-item message-assistant thinking">
            <span class="dot"/><span class="dot"/><span class="dot"/>
          </div>
        </div>
        <ChatBox :loading="chatStore.loading" @submit="handleSubmit" />
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onBeforeUnmount, watch, computed } from 'vue'
import { useChatStore } from '../store/chatStore'
import ChatBox from '../components/ChatBox.vue'
import MessageItem from '../components/MessageItem.vue'
import StockGrid from '../components/StockGrid.vue'
import StockDetailPanel from '../components/StockDetailPanel.vue'
import MacroPanel from '../components/MacroPanel.vue'
import { getStockList, getIndustryList } from '../api/stock'

const chatStore = useChatStore()
const msgListRef = ref(null)
const wrapRef = ref(null)

// ── Tab 定义 ──────────────────────────────────────
const TABS = [
  { key: 'stock',    label: '个股', icon: '📈' },
  { key: 'industry', label: '行业', icon: '🏭' },
  { key: 'macro',    label: '宏观', icon: '🌐' },
]

// ── 面板状态 ──────────────────────────────────────
const panelWidth = ref(0)
const panelOpen = computed(() => panelWidth.value > 0)
const isDragging = ref(false)
const isHovering = ref(false)
let dragStartX = 0
let dragStartWidth = 0
const isAnimating = ref(false)

// 把手跟随面板右边界，收起时贴左边缘内侧
const handleStyle = computed(() => {
  const left = panelWidth.value === 0 ? 0 : panelWidth.value
  return {
    left: `${left}px`,
    transform: panelWidth.value === 0 ? 'translateX(0)' : 'translateX(-50%)',
    transition: isDragging.value
      ? 'none'
      : 'left 0.6s cubic-bezier(0.34, 1.4, 0.64, 1), transform 0.6s cubic-bezier(0.34, 1.4, 0.64, 1)',
  }
})

// 探索区宽度动画
const exploreSideStyle = computed(() => ({
  width: `${panelWidth.value}px`,
  transition: isDragging.value ? 'none' : 'width 0.6s cubic-bezier(0.34, 1.4, 0.64, 1)',
}))

// 对话区占满剩余
const chatSideStyle = computed(() => ({
  width: `calc(100% - ${panelWidth.value}px)`,
  transition: isDragging.value ? 'none' : 'width 0.6s cubic-bezier(0.34, 1.4, 0.64, 1)',
}))

// ── 拖拽逻辑（从左边缘向右拖出）─────────────────
function onDragStart(e) {
  if (isAnimating.value) return
  isDragging.value = true
  dragStartX = e.clientX
  dragStartWidth = panelWidth.value

  if (panelWidth.value === 0 && !activeSection.value) {
    activeSection.value = 'stock'
  }

  document.addEventListener('mousemove', onDragMove, { passive: false })
  document.addEventListener('mouseup', onDragEnd)
  document.body.style.userSelect = 'none'
  document.body.style.cursor = 'col-resize'
}

function onDragMove(e) {
  if (!isDragging.value) return
  e.preventDefault()
  const total = wrapRef.value?.clientWidth || window.innerWidth
  const maxW = Math.floor(total * 0.6)
  // 鼠标 X 坐标直接就是面板宽度
  let newW = Math.max(0, Math.min(e.clientX, maxW))
  panelWidth.value = newW
}

function onDragEnd() {
  isDragging.value = false
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
  document.body.style.userSelect = ''
  document.body.style.cursor = ''

  const total = wrapRef.value?.clientWidth || window.innerWidth
  const snapW = Math.floor(total * 0.42)
  const threshold = 80

  isAnimating.value = true

  if (panelWidth.value >= threshold) {
    panelWidth.value = snapW
  } else {
    panelWidth.value = 0
  }

  setTimeout(() => { isAnimating.value = false }, 700)
}

// ── Tab 选择 ─────────────────────────────────────
const activeSection = ref('stock')
function onSectionSelect(key) {
  if (!panelOpen.value) {
    const total = wrapRef.value?.clientWidth || window.innerWidth
    panelWidth.value = Math.floor(total * 0.42)
  }
  if (activeSection.value === key) {
    panelWidth.value = 0
    return
  }
  activeSection.value = key
  selectedStock.value = null
}

// ── 数据 ─────────────────────────────────────────
const stocks     = ref([])
const industries = ref([])
const selectedStock = ref(null)

async function loadData() {
  const [s, ind] = await Promise.all([getStockList(), getIndustryList()])
  stocks.value     = s
  industries.value = ind
}

function onIndustryClick(industry) {
  chatStore.ask({
    message: `请分析 ${industry.name} 板块的整体情况，包括龙头公司、近期表现和投资机会`,
    targets: [{ symbol: industry.code, name: industry.name, type: 'industry' }],
  })
}

// ── 发送消息 ─────────────────────────────────────
async function handleSubmit(payload) {
  await chatStore.ask(payload)
  await nextTick()
  if (msgListRef.value) {
    msgListRef.value.scrollTop = msgListRef.value.scrollHeight
  }
}

watch(
  () => chatStore.messages.length,
  async () => {
    await nextTick()
    if (msgListRef.value) {
      msgListRef.value.scrollTop = msgListRef.value.scrollHeight
    }
  }
)

onMounted(loadData)
onBeforeUnmount(() => {
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
})
</script>

<style scoped>
/* ═══════════════════════════════════════════════
   主布局
   ═══════════════════════════════════════════════ */
.main-wrap {
  display: flex;
  width: 100%; height: 100%;
  overflow: hidden;
  position: relative;
}

.explore-side {
  flex-shrink: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--bg-panel);
  border-right: 1px solid var(--border);
}

.chat-side {
  flex-shrink: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
}

/* ═══════════════════════════════════════════════
   顶部 Tab 栏
   ═══════════════════════════════════════════════ */
.explore-tabs {
  display: flex;
  flex-shrink: 0;
  border-bottom: 1px solid var(--border);
  background: rgba(248, 250, 252, 0.9);
  padding: 0 8px;
}

.explore-tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 12px 0;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
  white-space: nowrap;
  margin-bottom: -1px;
}

.explore-tab-btn:hover { color: var(--text-primary); }

.explore-tab-btn.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.tab-icon { font-size: 15px; line-height: 1; }

/* ═══════════════════════════════════════════════
   把手 — 绝对定位，跟随面板右边界
   ═══════════════════════════════════════════════ */
.edge-handle {
  position: absolute;
  top: 0; bottom: 0;
  width: 20px;
  /* left 和 transform 由 handleStyle 动态控制 */
  cursor: col-resize;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 三层波纹 — 向右扩散 */
.handle-ripple {
  position: absolute;
  top: 0; bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  border-radius: 50% / 40%;
  pointer-events: none;
  transition:
    width 0.45s cubic-bezier(0.34, 1.4, 0.64, 1),
    opacity 0.45s ease,
    background 0.3s;
}

.ripple-1 {
  width: 4px;
  background: rgba(56, 189, 248, 0.18);
  box-shadow: 0 0 8px 1px rgba(56, 189, 248, 0.10);
  animation: rb 3.2s ease-in-out infinite;
}
.ripple-2 {
  width: 8px;
  background: rgba(56, 189, 248, 0.08);
  box-shadow: 0 0 14px 2px rgba(56, 189, 248, 0.06);
  animation: rb 3.2s ease-in-out 0.55s infinite;
}
.ripple-3 {
  width: 14px;
  background: rgba(56, 189, 248, 0.04);
  box-shadow: 0 0 22px 4px rgba(56, 189, 248, 0.03);
  animation: rb 3.2s ease-in-out 1.1s infinite;
}

@keyframes rb {
  0%, 100% { opacity: 0.45; }
  50%       { opacity: 1; }
}

/* hover */
.handle-hover .ripple-1 {
  width: 6px;
  background: rgba(56, 189, 248, 0.32);
  box-shadow: 0 0 12px 2px rgba(56, 189, 248, 0.18);
  animation: none; opacity: 1;
}
.handle-hover .ripple-2 {
  width: 14px;
  background: rgba(56, 189, 248, 0.14);
  box-shadow: 0 0 22px 4px rgba(56, 189, 248, 0.10);
  animation: none; opacity: 1;
}
.handle-hover .ripple-3 {
  width: 24px;
  background: rgba(56, 189, 248, 0.06);
  box-shadow: 0 0 32px 6px rgba(56, 189, 248, 0.05);
  animation: none; opacity: 1;
}

/* 拖拽中 */
.handle-drag .ripple-1 {
  width: 8px;
  background: rgba(14, 165, 233, 0.45);
  box-shadow: 0 0 16px 3px rgba(14, 165, 233, 0.25);
  animation: none; opacity: 1;
}
.handle-drag .ripple-2 {
  width: 18px;
  background: rgba(14, 165, 233, 0.18);
  box-shadow: 0 0 28px 5px rgba(14, 165, 233, 0.13);
  animation: none; opacity: 1;
}
.handle-drag .ripple-3 {
  width: 30px;
  background: rgba(14, 165, 233, 0.07);
  box-shadow: 0 0 40px 8px rgba(14, 165, 233, 0.06);
  animation: none; opacity: 1;
}

/* 箭头 */
.handle-arrow {
  position: relative;
  z-index: 1;
  font-size: 13px;
  font-weight: 400;
  color: rgba(56, 189, 248, 0.22);
  user-select: none;
  pointer-events: none;
  transition: color 0.3s, transform 0.35s cubic-bezier(0.34, 1.4, 0.64, 1);
}
.handle-hover .handle-arrow {
  color: rgba(56, 189, 248, 0.6);
  transform: translateX(1px);
}
.handle-drag .handle-arrow {
  color: rgba(14, 165, 233, 0.85);
  transform: translateX(2px);
}

/* ═══════════════════════════════════════════════
   详情滑入
   ═══════════════════════════════════════════════ */
.detail-slide-enter-active {
  transition: opacity .38s cubic-bezier(0.34, 1.4, 0.64, 1), transform .38s cubic-bezier(0.34, 1.4, 0.64, 1);
}
.detail-slide-leave-active {
  transition: opacity .22s ease, transform .22s ease;
}
.detail-slide-enter-from { opacity: 0; transform: translateX(-20px); }
.detail-slide-leave-to   { opacity: 0; transform: translateX(12px); }

/* ═══════════════════════════════════════════════
   思考动画
   ═══════════════════════════════════════════════ */
.thinking {
  display: flex; gap: 5px; align-items: center;
  padding: 14px 18px;
}
.dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #38bdf8;
  animation: bounce 1.2s infinite ease-in-out;
  display: inline-block;
}
.dot:nth-child(2) { animation-delay: .2s; }
.dot:nth-child(3) { animation-delay: .4s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.7); opacity: 0.4; }
  40%            { transform: scale(1.1); opacity: 1; }
}
</style>
