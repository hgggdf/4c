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
        <div class="content-area-inner" :class="{ 'no-padding': selectedStock || selectedIndustry }">

          <template v-if="activeSection === 'stock'">
            <Transition name="detail-slide" mode="out-in">
              <StockDetailPanel
                v-if="selectedStock"
                :key="selectedStock.symbol"
                :stock="selectedStock"
                :panel-width="panelWidth"
                @back="selectedStock = null"
              />
              <StockGrid
                v-else
                mode="stock"
                :stocks="stocks"
                :panel-width="panelWidth"
                @open-detail="selectedStock = $event"
              />
            </Transition>
          </template>

          <template v-else-if="activeSection === 'industry'">
            <Transition name="detail-slide" mode="out-in">
              <IndustryDetailPanel
                v-if="selectedIndustry"
                :key="selectedIndustry.code"
                :industry="selectedIndustry"
                :stocks="stocks"
                :panel-width="panelWidth"
                @back="selectedIndustry = null"
              />
              <StockGrid
                v-else
                mode="industry"
                :industries="industries"
                :panel-width="panelWidth"
                @open-industry="selectedIndustry = $event"
              />
            </Transition>
          </template>

          <template v-else-if="activeSection === 'macro'">
            <MacroPanel />
          </template>

          <template v-else-if="activeSection === 'news'">
            <NewsPanel />
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
      <ChatPanel />
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, computed } from 'vue'
import { useChatStore } from '../store/chatStore'
import StockGrid from '../components/StockGrid.vue'
import StockDetailPanel from '../components/StockDetailPanel.vue'
import IndustryDetailPanel from '../components/IndustryDetailPanel.vue'
import MacroPanel from '../components/MacroPanel.vue'
import NewsPanel from '../components/NewsPanel.vue'
import ChatPanel from '../components/ChatPanel.vue'
import { getStockList, getIndustryList } from '../api/stock'

const chatStore = useChatStore()
const wrapRef = ref(null)

// ── Tab 定义 ──────────────────────────────────────
const TABS = [
  { key: 'stock',    label: '个股', icon: '📈' },
  { key: 'industry', label: '行业', icon: '🏭' },
  { key: 'macro',    label: '宏观', icon: '🌐' },
  { key: 'news',     label: '新闻', icon: '📰' },
]

// ── 面板状态 ──────────────────────────────────────
// 三档：关闭(0) / 两列(~320px) / 五列(~600px)
const SNAP_TWO  = 320   // 两列
const SNAP_FIVE = 600   // 五列

const panelWidth = ref(SNAP_TWO)
const panelOpen = computed(() => panelWidth.value > 0)
const isDragging = ref(false)
const isHovering = ref(false)
let dragStartX = 0
let dragStartWidth = 0
const isAnimating = ref(false)

// 把手跟随面板右边界
// 收起时：left=0, translateX(0) → 把手左边缘贴屏幕左侧，弧形阴影向右散开
// 展开时：left=panelWidth, translateX(-50%) → 把手中心线对齐面板右边界
// 把手贴在面板右边缘，向右侧伸出（left = panelWidth，不偏移）
const handleStyle = computed(() => ({
  left: `${panelWidth.value}px`,
  transform: 'translateX(0)',
  transition: isDragging.value
    ? 'none'
    : 'left 0.6s cubic-bezier(0.34, 1.4, 0.64, 1)',
}))

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
  const delta = e.clientX - dragStartX
  let newW = Math.max(0, Math.min(dragStartWidth + delta, SNAP_FIVE))
  panelWidth.value = newW
}

function onDragEnd() {
  isDragging.value = false
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
  document.body.style.userSelect = ''
  document.body.style.cursor = ''

  const w = panelWidth.value
  const threshold = 80
  const midpoint = (SNAP_TWO + SNAP_FIVE) / 2

  isAnimating.value = true

  if (w < threshold) {
    panelWidth.value = 0
  } else if (w < midpoint) {
    panelWidth.value = SNAP_TWO
  } else {
    panelWidth.value = SNAP_FIVE
  }

  setTimeout(() => { isAnimating.value = false }, 700)
}

// ── Tab 选择 ─────────────────────────────────────
const activeSection = ref('stock')
function onSectionSelect(key) {
  if (!panelOpen.value) {
    panelWidth.value = SNAP_TWO
  }
  if (activeSection.value === key) {
    panelWidth.value = 0
    return
  }
  activeSection.value = key
  selectedStock.value = null
  selectedIndustry.value = null
}

// ── 数据 ─────────────────────────────────────────
const stocks     = ref([])
const industries = ref([])
const selectedStock    = ref(null)
const selectedIndustry = ref(null)

async function loadData() {
  const [s, ind] = await Promise.all([getStockList(), getIndustryList()])
  stocks.value     = s
  industries.value = ind
}

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
  align-items: stretch;
  width: 100%; height: 100%;
  overflow: hidden;
  position: relative;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

.explore-side  { animation: fadeUp .5s ease both; }
.edge-handle   { animation: fadeUp .5s ease .1s both; }
.chat-side     { animation: fadeUp .5s ease .18s both; }

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
  flex-direction: row;
  align-items: stretch;
  position: relative;
}

/* ═══════════════════════════════════════════════
   顶部 Tab 栏
   ═══════════════════════════════════════════════ */
.explore-tabs {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.92));
  padding: 10px 10px 8px;
  height: 60px;
}

.explore-tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 0;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  box-shadow: 0 1px 0 rgba(255,255,255,0.8) inset;
}

.explore-tab-btn:hover {
  color: var(--accent2);
  border-color: rgba(75,169,154,0.28);
  background: #fff;
  box-shadow: 0 4px 12px rgba(75,169,154,0.08);
  transform: translateY(-1px);
}

.explore-tab-btn.active {
  color: #fff;
  background: linear-gradient(180deg, var(--accent), var(--accent2));
  border-color: var(--accent2);
  box-shadow: 0 6px 16px rgba(75,169,154,0.22);
}

.tab-icon { font-size: 16px; line-height: 1; }

/* ═══════════════════════════════════════════════
   把手 — 实体圆角矩形，向右侧伸出
   ═══════════════════════════════════════════════ */
.edge-handle {
  position: absolute;
  top: 0; bottom: 0;
  width: 14px;
  cursor: col-resize;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

/* 弧形阴影背景 — 不再需要，隐藏 */
.handle-shadow-arc { display: none; }

/* 实体把手矩形 */
.handle-pill {
  width: 12px;
  height: 44px;
  background: linear-gradient(180deg, var(--bg-card), #fff);
  border: 1px solid var(--border);
  border-left: none;
  border-radius: 0 10px 10px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background .2s, box-shadow .2s, width .15s, border-color .2s;
  box-shadow: 2px 0 10px rgba(0,0,0,0.08);
  flex-shrink: 0;
  margin-left: -1px;
}

.handle-hover .handle-pill {
  background: #fff;
  border-color: var(--border-hl);
  box-shadow: 2px 0 12px rgba(75,169,154,0.16);
  width: 14px;
}

.handle-drag .handle-pill {
  background: rgba(75,169,154,0.12);
  border-color: var(--accent);
  box-shadow: 2px 0 14px rgba(75,169,154,0.22);
  width: 14px;
}

/* 箭头 */
.handle-arrow {
  font-size: 12px;
  color: var(--text-secondary);
  user-select: none;
  pointer-events: none;
  transition: color .2s;
  line-height: 1;
  font-weight: 800;
}

.handle-hover .handle-arrow { color: var(--accent2); }
.handle-drag  .handle-arrow { color: var(--accent2); }

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
