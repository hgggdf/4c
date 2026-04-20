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
        <div class="content-area-inner" :class="{ 'no-padding': selectedStock }">

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
        'handle-closed': !panelOpen,
      }"
      :style="handleStyle"
      @mousedown.prevent="onDragStart"
      @mouseenter="isHovering = true"
      @mouseleave="isHovering = false"
    >
      <!-- 弧形阴影背景（收起时可见） -->
      <div class="handle-shadow-arc"></div>
      <!-- 中央胶囊指示条 -->
      <div class="handle-pill">
        <div class="handle-arrow">{{ panelOpen ? '‹' : '›' }}</div>
      </div>
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
// 默认展开，初始宽度设为两列个股（约 360px）
const getInitialWidth = () => {
  const screenWidth = window.innerWidth
  // 两列个股：每列约 160px + gap + padding = 360px
  return Math.max(360, Math.min(400, Math.floor(screenWidth * 0.25)))
}
const panelWidth = ref(getInitialWidth())
const panelOpen = computed(() => panelWidth.value > 0)
const isDragging = ref(false)
const isHovering = ref(false)
let dragStartX = 0
let dragStartWidth = 0
const isAnimating = ref(false)

// 把手跟随面板右边界
// 收起时：left=0, translateX(0) → 把手左边缘贴屏幕左侧，弧形阴影向右散开
// 展开时：left=panelWidth, translateX(-50%) → 把手中心线对齐面板右边界
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
  // 最大宽度：四列个股（约 720px）
  const maxW = Math.min(720, Math.floor(total * 0.5))
  // 用相对位移，避免面板跳动
  const delta = e.clientX - dragStartX
  let newW = Math.max(0, Math.min(dragStartWidth + delta, maxW))
  panelWidth.value = newW
}

function onDragEnd() {
  isDragging.value = false
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
  document.body.style.userSelect = ''
  document.body.style.cursor = ''

  const total = wrapRef.value?.clientWidth || window.innerWidth
  const twoCol  = Math.max(360, Math.min(400, Math.floor(total * 0.25)))
  const fourCol = Math.min(720, Math.floor(total * 0.5))
  const threshold = 80
  const w = panelWidth.value

  isAnimating.value = true

  if (w < threshold) {
    panelWidth.value = 0
  } else if (w < (twoCol + fourCol) / 2) {
    panelWidth.value = twoCol
  } else {
    panelWidth.value = fourCol
  }

  setTimeout(() => { isAnimating.value = false }, 700)
}

// ── Tab 选择 ─────────────────────────────────────
const activeSection = ref('stock')
function onSectionSelect(key) {
  if (!panelOpen.value) {
    const total = wrapRef.value?.clientWidth || window.innerWidth
    panelWidth.value = Math.max(360, Math.min(400, Math.floor(total * 0.25)))
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
  width: 48px;
  /* left 和 transform 由 handleStyle 动态控制 */
  cursor: col-resize;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 弧形阴影背景 — 收起时显示 */
.handle-shadow-arc {
  position: absolute;
  top: 0; bottom: 0;
  left: 0; right: 0;
  background: radial-gradient(
    ellipse 160% 100% at 0% 50%,
    rgba(75, 169, 154, 0.10) 0%,
    rgba(75, 169, 154, 0.05) 35%,
    transparent 65%
  );
  opacity: 0;
  transition: opacity 0.4s ease, background 0.3s ease;
  pointer-events: none;
}

.handle-closed .handle-shadow-arc {
  opacity: 1;
}

.handle-hover.handle-closed .handle-shadow-arc {
  background: radial-gradient(
    ellipse 160% 100% at 0% 50%,
    rgba(75, 169, 154, 0.18) 0%,
    rgba(75, 169, 154, 0.09) 35%,
    transparent 65%
  );
  opacity: 1;
}

/* 中央胶囊指示条 */
.handle-pill {
  position: relative;
  width: 4px;
  height: 48px;
  background: rgba(75, 169, 154, 0.2);
  border-radius: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s cubic-bezier(0.34, 1.4, 0.64, 1);
  box-shadow: 0 0 8px rgba(75, 169, 154, 0.1);
}

.handle-closed .handle-pill {
  width: 3px;
  height: 40px;
  background: rgba(75, 169, 154, 0.15);
  box-shadow: 0 0 6px rgba(75, 169, 154, 0.08);
}

.handle-hover .handle-pill {
  width: 6px;
  height: 56px;
  background: rgba(75, 169, 154, 0.35);
  box-shadow: 0 0 16px rgba(75, 169, 154, 0.2);
}

.handle-drag .handle-pill {
  width: 8px;
  height: 64px;
  background: rgba(61, 150, 136, 0.5);
  box-shadow: 0 0 24px rgba(61, 150, 136, 0.3);
}

/* 箭头 */
.handle-arrow {
  position: absolute;
  font-size: 14px;
  font-weight: 600;
  color: rgba(75, 169, 154, 0.4);
  user-select: none;
  pointer-events: none;
  transition: color 0.3s, transform 0.35s cubic-bezier(0.34, 1.4, 0.64, 1);
}

.handle-closed .handle-arrow {
  color: rgba(75, 169, 154, 0.3);
}

.handle-hover .handle-arrow {
  color: rgba(75, 169, 154, 0.75);
  transform: translateX(1px);
}

.handle-drag .handle-arrow {
  color: rgba(61, 150, 136, 0.9);
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
  background: #4ba99a;
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
