<template>
  <div>
    <div class="section-title">
      {{ mode === 'stock' ? '医药个股' : '行业板块' }}
      <span style="font-size:12px;color:var(--text-muted);font-weight:400;margin-left:4px;">
        （拖入对话框进行多标的分析）
      </span>
    </div>

    <!-- 搜索框 -->
    <div class="sg-search-wrap">
      <input
        v-model="query"
        class="sg-search"
        :placeholder="mode==='stock' ? '搜索股票名称或代码…' : '搜索行业…'"
      />
    </div>

    <!-- 个股网格 -->
<<<<<<< Updated upstream
    <div v-if="mode === 'stock'" class="stock-grid">
=======
    <div v-if="mode === 'stock'" class="stock-grid stock-grid-5col" :style="gridStyle">

      <!-- 自选股区域 -->
      <template v-if="watchlistStocks.length">
        <div
          v-for="(item, idx) in watchlistStocks"
          :key="'wl-' + item.symbol"
          class="card-scene"
          :style="{ animationDelay: `${idx * 40}ms` }"
        >
          <div
            class="stock-card tilt-card"
            :class="{ dragging: draggingSymbol === item.symbol }"
            draggable="true"
            @dragstart="onDragStart($event, item)"
            @dragend="onDragEnd($event)"
            @click="$emit('open-detail', item)"
            @mousemove="onTiltMove($event)"
            @mouseleave="onTiltLeave($event)"
            @mouseenter="onTiltEnter($event)"
          >
            <div class="card-face">
              <div class="sc-header">
                <div class="sc-name">{{ item.name }}</div>
                <button
                  class="watchlist-btn active"
                  @click.stop="toggleWatchlist(item.symbol)"
                  title="取消自选"
                >★</button>
              </div>
              <div class="sc-code">{{ item.symbol }}</div>
              <div class="sc-price" :class="item.change >= 0 ? 'red' : 'green'">
                {{ item.price.toFixed(2) }}
              </div>
              <div class="sc-change" :class="item.change >= 0 ? 'red' : 'green'">
                {{ item.change >= 0 ? '+' : '' }}{{ item.change_pct.toFixed(2) }}%
              </div>
              <div class="sc-industry">{{ item.industry }}</div>
              <div class="drag-tip">⇠ 拖入对话</div>
            </div>
            <div class="card-shine"></div>
          </div>
        </div>

        <!-- 分隔线 -->
        <div class="watchlist-divider">
          <div class="divider-line"></div>
        </div>
      </template>

      <!-- 非自选股区域 -->
>>>>>>> Stashed changes
      <div
        v-for="(item, idx) in filteredStocks"
        :key="item.symbol"
        class="card-scene"
        :style="{ animationDelay: `${idx * 40}ms` }"
      >
        <div
          class="stock-card tilt-card"
          :class="{ dragging: draggingSymbol === item.symbol }"
          draggable="true"
          @dragstart="onDragStart($event, item)"
          @dragend="onDragEnd($event)"
          @click="$emit('open-detail', item)"
          @mousemove="onTiltMove($event)"
          @mouseleave="onTiltLeave($event)"
          @mouseenter="onTiltEnter($event)"
        >
          <div class="card-face">
            <div class="sc-header">
              <div class="sc-name">{{ item.name }}</div>
              <button
                class="watchlist-btn"
                :class="{ active: isInWatchlist(item.symbol) }"
                @click.stop="toggleWatchlist(item.symbol)"
                :title="isInWatchlist(item.symbol) ? '取消自选' : '加入自选'"
              >{{ isInWatchlist(item.symbol) ? '★' : '☆' }}</button>
            </div>
            <div class="sc-code">{{ item.symbol }}</div>
            <div class="sc-price" :class="item.change >= 0 ? 'red' : 'green'">
              {{ item.price.toFixed(2) }}
            </div>
            <div class="sc-change" :class="item.change >= 0 ? 'red' : 'green'">
              {{ item.change >= 0 ? '+' : '' }}{{ item.change_pct.toFixed(2) }}%
            </div>
            <div class="sc-industry">{{ item.industry }}</div>
            <div class="drag-tip">⇠ 拖入对话</div>
          </div>
          <div class="card-shine"></div>
        </div>
      </div>
    </div>

    <!-- 行业网格 -->
<<<<<<< Updated upstream
    <div v-else class="stock-grid">
=======
    <div v-else class="stock-grid stock-grid-5col" :style="gridStyle">
>>>>>>> Stashed changes
      <div
        v-for="(item, idx) in filteredIndustries"
        :key="item.code"
        class="card-scene"
        :style="{ animationDelay: `${idx * 40}ms` }"
      >
        <div
          class="industry-card tilt-card"
          draggable="true"
          @dragstart="onDragStart($event, { symbol: item.code, name: item.name, type: 'industry' })"
          @dragend="onDragEnd($event)"
          @click="$emit('open-industry', item)"
          @mousemove="onTiltMove($event)"
          @mouseleave="onTiltLeave($event)"
          @mouseenter="onTiltEnter($event)"
        >
          <div class="card-face">
            <div class="ic-name">{{ item.name }}</div>
            <div class="ic-count">{{ item.count }} 家上市公司</div>
            <div class="ic-change" :class="item.change_pct >= 0 ? 'red' : 'green'">
              {{ item.change_pct >= 0 ? '+' : '' }}{{ item.change_pct.toFixed(2) }}%
            </div>
            <div class="ic-bar">
              <div class="ic-bar-fill" :style="{
                width: `${item.heat * 100}%`,
                background: item.change_pct >= 0 ? 'var(--red)' : 'var(--green)'
              }"/>
            </div>
            <div class="ic-leader">龙头：{{ item.leader }}</div>
            <div class="drag-tip">⇠ 拖入对话</div>
          </div>
          <div class="card-shine"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const WATCHLIST_KEY = '4c_watchlist'

const props = defineProps({
  mode: { type: String, default: 'stock' }, // 'stock' | 'industry'
  stocks: { type: Array, default: () => [] },
  industries: { type: Array, default: () => [] },
  panelWidth: { type: Number, default: 320 },
})

// 展开档(>=480px)用4列，收缩档用2列
const gridCols = computed(() => props.panelWidth >= 480 ? 4 : 2)
const gridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${gridCols.value}, 1fr)`,
}))

defineEmits(['open-detail', 'open-industry', 'drag-item'])

const query = ref('')
const draggingSymbol = ref('')
const watchlist = ref(new Set())

const filteredStocks = computed(() =>
  props.stocks.filter(s =>
    !query.value ||
    s.name.includes(query.value) ||
    s.symbol.includes(query.value)
  )
)

const filteredIndustries = computed(() =>
  props.industries.filter(s =>
    !query.value || s.name.includes(query.value)
  )
)

function onDragStart(evt, item) {
  draggingSymbol.value = item.symbol || item.code
  evt.dataTransfer.setData('application/json', JSON.stringify(item))
  evt.dataTransfer.effectAllowed = 'copy'
}

function isInWatchlist(symbol) {
  return watchlist.value.has(symbol)
}

<<<<<<< Updated upstream
async function toggleWatchlist(symbol) {
  try {
    if (isInWatchlist(symbol)) {
      await removeFromWatchlist(symbol)
      watchlist.value.delete(symbol)
    } else {
      await addToWatchlist(symbol)
      watchlist.value.add(symbol)
    }
  } catch (err) {
    console.error('自选股操作失败:', err)
=======
function toggleWatchlist(symbol) {
  const next = new Set(watchlist.value)
  if (next.has(symbol)) {
    next.delete(symbol)
  } else {
    next.add(symbol)
>>>>>>> Stashed changes
  }
  watchlist.value = next
  localStorage.setItem(WATCHLIST_KEY, JSON.stringify([...next]))
}

function loadWatchlist() {
  try {
    const saved = localStorage.getItem(WATCHLIST_KEY)
    if (saved) {
      watchlist.value = new Set(JSON.parse(saved))
    }
  } catch {
    watchlist.value = new Set()
  }
}

onMounted(loadWatchlist)

// ── 重力感应倾斜 ──────────────────────────────────
function onTiltEnter(e) {
  const card = e.currentTarget
  card.style.transition = 'none'
}

function onTiltMove(e) {
  const card = e.currentTarget
  const rect = card.getBoundingClientRect()
  const cx = rect.left + rect.width / 2
  const cy = rect.top + rect.height / 2
  const dx = (e.clientX - cx) / (rect.width / 2)   // -1 ~ 1
  const dy = (e.clientY - cy) / (rect.height / 2)  // -1 ~ 1

  // 倾斜角度更夸张
  const rotX = -dy * 16
  const rotY =  dx * 16

  // 光泽跟随鼠标
  const px = ((dx + 1) / 2 * 100).toFixed(0)
  const py = ((dy + 1) / 2 * 100).toFixed(0)
  const shine = card.querySelector('.card-shine')
  if (shine) {
    shine.style.background = `radial-gradient(circle at ${px}% ${py}%, rgba(255,255,255,0.65) 0%, rgba(255,255,255,0.18) 35%, transparent 65%)`
    shine.style.opacity = '1'
  }

  // 阴影方向与倾斜相反，模拟光源在上方
  const sx = (-dx * 24).toFixed(1)
  const sy = (-dy * 24).toFixed(1)

  card.style.transform = `rotateX(${rotX}deg) rotateY(${rotY}deg) translateZ(36px) scale(1.08)`
  card.style.boxShadow = `
    ${sx}px ${sy}px 48px rgba(75,169,154,0.4),
    0 20px 50px rgba(0,0,0,0.15),
    0 6px 16px rgba(75,169,154,0.2),
    inset 0 1px 0 rgba(255,255,255,0.5)
  `
}

function onTiltLeave(e) {
  const card = e.currentTarget
  card.style.transition = 'transform .5s cubic-bezier(0.23, 1, 0.32, 1), box-shadow .5s cubic-bezier(0.23, 1, 0.32, 1)'
  card.style.transform = ''
  card.style.boxShadow = ''

  const shine = card.querySelector('.card-shine')
  if (shine) {
    shine.style.opacity = '0'
    shine.style.background = 'none'
  }
}

function onDragEnd(e) {
  draggingSymbol.value = ''
  onTiltLeave(e)
}
</script>

<style scoped>
.sg-search-wrap { margin-bottom: 14px; }
.sg-search {
  width: 100%; max-width: 320px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 8px 14px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  transition: border-color .2s;
}
.sg-search:focus { border-color: var(--border-hl); }

<<<<<<< Updated upstream
=======
.sg-filter {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 7px 10px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  cursor: pointer;
  transition: border-color .2s;
  max-width: 130px;
}
.sg-filter:focus { border-color: var(--border-hl); }

/* ── 列数由 JS gridStyle 控制，此处只设 gap ── */
.stock-grid-5col {
  gap: 10px !important;
}

/* ── 分隔线 ── */
.watchlist-divider {
  grid-column: 1 / -1;
  margin: 10px 0;
}
.divider-line {
  position: relative;
  height: 1px;
  background: var(--border);
}
.divider-label {
  position: absolute;
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
  white-space: nowrap;
  background: var(--bg-panel);
  padding: 0 6px;
  top: 50%;
  transform: translateY(-50%);
}
.divider-label--top  { right: 8px; }
.divider-label--bottom { left: 8px; }

>>>>>>> Stashed changes
/* ── 3D 场景容器 ── */
.card-scene {
  perspective: 500px;
  perspective-origin: 50% 50%;
  animation: cardRise .4s ease both;
}

/* ── 卡片本体 ── */
.tilt-card {
  position: relative;
  transform-style: preserve-3d;
  transform-origin: center center;
  cursor: grab;
  user-select: none;
  will-change: transform;
  /* 默认无 transition，mousemove 时实时更新；离开时由 JS 加回 */
}
.tilt-card:active { cursor: grabbing; }
.tilt-card.dragging { opacity: .5; transform: scale(0.95) !important; }

/* 卡片正面内容层 */
.card-face {
  position: relative;
  z-index: 2;
}

/* ── 光泽层 ── */
.card-shine {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  opacity: 0;
  z-index: 3;
  transition: opacity .3s;
  mix-blend-mode: screen;
}

<<<<<<< Updated upstream
/* ── 卡片底部厚度阴影（translateZ 负方向伪造侧面） ── */
.tilt-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: inherit;
  transform: translateZ(-8px);
  filter: brightness(0.7);
  z-index: 0;
}
=======
>>>>>>> Stashed changes

/* ── 顶部边缘高光线 ── */
.tilt-card::after {
  content: '';
  position: absolute;
  top: 0; left: 8%; right: 8%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.7), transparent);
  border-radius: 1px;
  z-index: 4;
  pointer-events: none;
}

<<<<<<< Updated upstream
/* 自选按钮 */
=======
/* ── 自选按钮 ── */
>>>>>>> Stashed changes
.sc-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 2px;
}
.watchlist-btn {
  background: none; border: none;
  color: var(--text-muted);
<<<<<<< Updated upstream
  font-size: 16px; line-height: 1;
  cursor: pointer; padding: 0;
=======
  font-size: 24px; line-height: 1;
  cursor: pointer; padding: 0 2px;
>>>>>>> Stashed changes
  transition: color .2s, transform .2s;
}
.watchlist-btn:hover { color: var(--gold); transform: scale(1.15); }
.watchlist-btn.active { color: var(--gold); }

/* 拖拽提示 — 绝对定位，不占卡片高度 */
.drag-tip {
  position: absolute;
  bottom: 4px; left: 0; right: 0;
  text-align: center;
  font-size: 10px; color: var(--text-muted);
<<<<<<< Updated upstream
  margin-top: 6px; opacity: 0;
=======
  opacity: 0;
>>>>>>> Stashed changes
  transition: opacity .2s;
  pointer-events: none;
}
.tilt-card:hover .drag-tip { opacity: 1; }

.ic-leader { font-size: 11px; color: var(--text-muted); margin-top: 2px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.ic-count  { font-size: 11px; color: var(--text-secondary); margin-top: 1px; }
.ic-change { font-size: 15px; font-weight: 800; margin-top: 5px; }
.ic-bar    { height: 3px; border-radius: 2px; background: var(--bg-card2); margin-top: 5px; overflow: hidden; }

/* 个股次要信息字号 */
.stock-card .sc-code     { font-size: 11px; color: var(--text-secondary); margin-top: 1px; }
.stock-card .sc-price    { font-size: 15px; font-weight: 800; margin-top: 5px; }
.stock-card .sc-change   { font-size: 11px; margin-top: 2px; }
.stock-card .sc-industry { font-size: 11px; color: var(--text-muted); margin-top: 2px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }

/* ── 统一个股和行业卡片尺寸 ── */
.card-scene {
  height: 155px;
}

.stock-card,
.industry-card {
  padding: 10px 12px;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.stock-card .card-face,
.industry-card .card-face {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

/* 个股名称：允许换行，最多两行，字体自适应 */
.stock-card .sc-name {
  font-size: clamp(11px, 1.8vw, 14px);
  white-space: normal;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.3;
  word-break: break-all;
}

/* 行业名称：允许换行，最多两行，字体自适应 */
.industry-card .ic-name {
  font-size: clamp(11px, 1.8vw, 14px);
  white-space: normal;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.3;
  word-break: break-all;
}
</style>
