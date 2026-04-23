<template>
  <div>
    <div class="section-title">
      {{ mode === 'stock' ? '医药个股' : '行业板块' }}
      <span style="font-size:12px;color:var(--text-muted);font-weight:400;margin-left:4px;">
        （拖入对话框进行多标的分析）
      </span>
    </div>

    <!-- 搜索框 + 行业筛选（仅个股模式） -->
    <div v-if="mode === 'stock'" class="sg-toolbar">
      <input
        v-model="query"
        class="sg-search"
        placeholder="搜索股票名称或代码…"
      />
      <select v-model="selectedIndustry" class="sg-filter">
        <option value="">全部行业</option>
        <option v-for="ind in industryOptions" :key="ind" :value="ind">{{ ind }}</option>
      </select>
    </div>

    <!-- 个股网格 -->
    <div v-if="mode === 'stock'" class="stock-grid stock-grid-5col">

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
      <div
        v-for="(item, idx) in nonWatchlistStocks"
        :key="'nw-' + item.symbol"
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
                @click.stop="toggleWatchlist(item.symbol)"
                title="加入自选"
              >☆</button>
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
    <div v-else class="stock-grid stock-grid-5col">
      <div
        v-for="(item, idx) in industries"
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
            <div class="ic-name" :title="item.name">{{ item.name }}</div>
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
          </div>
          <div class="card-shine"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getWatchlist, addToWatchlist, removeFromWatchlist } from '../api/stock'

const props = defineProps({
  mode: { type: String, default: 'stock' }, // 'stock' | 'industry'
  stocks: { type: Array, default: () => [] },
  industries: { type: Array, default: () => [] },
})

defineEmits(['open-detail', 'open-industry', 'drag-item'])

const query = ref('')
const selectedIndustry = ref('')
const draggingSymbol = ref('')
const watchlist = ref(new Set())

const industryOptions = computed(() => {
  const set = new Set(props.stocks.map(s => s.industry).filter(Boolean))
  return Array.from(set).sort()
})

const filteredStocks = computed(() =>
  props.stocks.filter(s => {
    const matchQuery = !query.value || s.name.includes(query.value) || s.symbol.includes(query.value)
    const matchIndustry = !selectedIndustry.value || s.industry === selectedIndustry.value
    return matchQuery && matchIndustry
  })
)

const watchlistStocks = computed(() =>
  filteredStocks.value.filter(s => watchlist.value.has(s.symbol))
)

const nonWatchlistStocks = computed(() =>
  filteredStocks.value.filter(s => !watchlist.value.has(s.symbol))
)

function onDragStart(evt, item) {
  draggingSymbol.value = item.symbol || item.code
  evt.dataTransfer.setData('application/json', JSON.stringify(item))
  evt.dataTransfer.effectAllowed = 'copy'
}

function isInWatchlist(symbol) {
  return watchlist.value.has(symbol)
}

async function toggleWatchlist(symbol) {
  try {
    if (isInWatchlist(symbol)) {
      await removeFromWatchlist(symbol)
      const next = new Set(watchlist.value)
      next.delete(symbol)
      watchlist.value = next
    } else {
      await addToWatchlist(symbol)
      watchlist.value = new Set([...watchlist.value, symbol])
    }
  } catch (err) {
    console.error('自选股操作失败:', err)
  }
}

async function loadWatchlist() {
  try {
    const list = await getWatchlist()
    watchlist.value = new Set((list || []).map(item => item.symbol))
  } catch (err) {
    console.error('加载自选股失败:', err)
  }
}

onMounted(loadWatchlist)

function onTiltEnter(e) {}

function onTiltMove(e) {
  const card = e.currentTarget
  const rect = card.getBoundingClientRect()
  const dx = (e.clientX - rect.left - rect.width / 2) / (rect.width / 2)
  const dy = (e.clientY - rect.top - rect.height / 2) / (rect.height / 2)
  const px = ((dx + 1) / 2 * 100).toFixed(0)
  const py = ((dy + 1) / 2 * 100).toFixed(0)
  const shine = card.querySelector('.card-shine')
  if (shine) {
    shine.style.background = `radial-gradient(circle at ${px}% ${py}%, rgba(255,255,255,0.65) 0%, rgba(255,255,255,0.18) 35%, transparent 65%)`
    shine.style.opacity = '1'
  }
}

function onTiltLeave(e) {
  const shine = e.currentTarget.querySelector('.card-shine')
  if (shine) {
    shine.style.opacity = '0'
    shine.style.background = 'none'
  }
}

function onDragEnd(e) {
  draggingSymbol.value = ''
}
</script>

<style scoped>
/* ── 工具栏：搜索 + 筛选 ── */
.sg-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.sg-search {
  flex: 1;
  min-width: 120px;
  max-width: 220px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 7px 12px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  transition: border-color .2s;
}
.sg-search:focus { border-color: var(--border-hl); }

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

/* ── 自适应列数（两列档~320px，五列档~600px） ── */
.stock-grid-5col {
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)) !important;
  gap: 8px !important;
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

/* ── 3D 场景容器 ── */
.card-scene {
  perspective: 500px;
  perspective-origin: 50% 50%;
  animation: cardRise .4s ease both;
  display: flex;
  flex-direction: column;
}

/* ── 卡片本体 ── */
.tilt-card {
  position: relative;
  transform-style: preserve-3d;
  transform-origin: center center;
  cursor: grab;
  user-select: none;
  will-change: transform;
  flex: 1;
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

/* ── 卡片底部厚度阴影 ── */
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

/* ── 自选按钮（更大，方便点击） ── */
.sc-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 2px;
}
.watchlist-btn {
  background: none; border: none;
  color: var(--text-muted);
  font-size: 26px; line-height: 1;
  cursor: pointer; padding: 2px 4px;
  transition: color .2s, transform .2s;
  flex-shrink: 0;
}
.watchlist-btn:hover { color: var(--gold); transform: scale(1.2); }
.watchlist-btn.active { color: var(--gold); }

/* 拖拽提示 */
.drag-tip {
  font-size: 10px; color: var(--text-muted);
  margin-top: 4px; opacity: 0;
  transition: opacity .2s;
}
.tilt-card:hover .drag-tip { opacity: 1; }

.ic-leader { font-size: 11px; color: var(--text-muted); margin-top: 4px; }
</style>
