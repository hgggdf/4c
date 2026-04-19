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
    <div v-if="mode === 'stock'" class="stock-grid">
      <div
        v-for="(item, idx) in filteredStocks"
        :key="item.symbol"
        class="stock-card"
        :class="{ dragging: draggingSymbol === item.symbol }"
        draggable="true"
        :style="{ animationDelay: `${idx * 40}ms` }"
        @dragstart="onDragStart($event, item)"
        @dragend="draggingSymbol = ''"
        @click="$emit('open-detail', item)"
      >
        <div class="sc-name">{{ item.name }}</div>
        <div class="sc-code">{{ item.symbol }}</div>
        <div class="sc-price" :class="item.change >= 0 ? 'red' : 'green'">
          {{ item.price.toFixed(2) }}
        </div>
        <div class="sc-change" :class="item.change >= 0 ? 'red' : 'green'">
          {{ item.change >= 0 ? '+' : '' }}{{ item.change_pct.toFixed(2) }}%
        </div>
        <div class="sc-industry">{{ item.industry }}</div>

        <!-- 拖拽提示 -->
        <div class="drag-tip">⇠ 拖入对话</div>
      </div>
    </div>

    <!-- 行业网格 -->
    <div v-else class="stock-grid">
      <div
        v-for="(item, idx) in filteredIndustries"
        :key="item.code"
        class="industry-card"
        draggable="true"
        :style="{ animationDelay: `${idx * 40}ms` }"
        @dragstart="onDragStart($event, { symbol: item.code, name: item.name, type: 'industry' })"
        @dragend="draggingSymbol = ''"
        @click="$emit('open-industry', item)"
      >
        <div class="ic-name">{{ item.name }}</div>
        <div class="ic-count">{{ item.count }} 家上市公司</div>
        <div class="ic-change" :class="item.change_pct >= 0 ? 'red' : 'green'">
          {{ item.change_pct >= 0 ? '+' : '' }}{{ item.change_pct.toFixed(2) }}%
        </div>
        <div class="ic-bar">
          <div
            class="ic-bar-fill"
            :style="{
              width: `${item.heat * 100}%`,
              background: item.change_pct >= 0 ? 'var(--red)' : 'var(--green)'
            }"
          />
        </div>
        <div class="ic-leader">龙头：{{ item.leader }}</div>
        <div class="drag-tip">⇠ 拖入对话</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  mode: { type: String, default: 'stock' }, // 'stock' | 'industry'
  stocks: { type: Array, default: () => [] },
  industries: { type: Array, default: () => [] },
})

defineEmits(['open-detail', 'open-industry', 'drag-item'])

const query = ref('')
const draggingSymbol = ref('')

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

.drag-tip {
  font-size: 10px; color: var(--text-muted);
  margin-top: 6px; opacity: 0;
  transition: opacity .2s;
}
.stock-card:hover .drag-tip,
.industry-card:hover .drag-tip { opacity: 1; }

.ic-leader {
  font-size: 11px; color: var(--text-muted); margin-top: 4px;
}
</style>
