<template>
  <div class="detail-panel">
    <!-- Header -->
    <div class="detail-header">
      <button class="back-btn" @click="$emit('back')">
        <span class="back-arrow">‹</span>
        <span class="back-text">返回</span>
      </button>
      <span class="detail-name">{{ industry.name }}</span>
      <span class="detail-code">{{ industry.count }} 家公司</span>
      <div class="detail-spacer"></div>
      <span class="detail-change" :class="industry.change_pct >= 0 ? 'red' : 'green'">
        {{ industry.change_pct >= 0 ? '+' : '' }}{{ industry.change_pct?.toFixed(2) }}%
      </span>
    </div>

    <!-- Tab 切换 -->
    <div class="tab-bar">
      <button
        v-for="t in tabs"
        :key="t.key"
        class="tab-btn"
        :class="{ active: activeTab === t.key }"
        @click="activeTab = t.key"
      >{{ t.label }}</button>
    </div>

    <div class="content-scroll">

      <!-- 公司 & 宏观 -->
      <template v-if="activeTab === 'overview'">
        <div class="section-title">板块成分股</div>
        <div class="company-list">
          <div v-for="c in companies" :key="c.symbol" class="company-item">
            <div class="ci-left">
              <div class="ci-name">{{ c.name }}</div>
              <div class="ci-code">{{ c.symbol }}</div>
            </div>
            <div class="ci-right">
              <div class="ci-price" :class="c.change >= 0 ? 'red' : 'green'">{{ c.price?.toFixed(2) }}</div>
              <div class="ci-change" :class="c.change >= 0 ? 'red' : 'green'">
                {{ c.change >= 0 ? '+' : '' }}{{ c.change_pct?.toFixed(2) }}%
              </div>
            </div>
          </div>
        </div>

        <div class="section-title" style="margin-top:20px;">宏观数据参考</div>
        <div class="macro-grid">
          <div v-for="m in macroData" :key="m.label" class="macro-card">
            <div class="macro-label">{{ m.label }}</div>
            <div class="macro-value" :class="m.trend === 'up' ? 'red' : m.trend === 'down' ? 'green' : ''">
              {{ m.value }}
            </div>
            <div class="macro-sub">{{ m.sub }}</div>
          </div>
        </div>
      </template>

      <!-- 行业研报 -->
      <template v-else-if="activeTab === 'report'">
        <div class="section-title">行业研报</div>
        <div v-if="reportsLoading" class="empty-state">加载中...</div>
        <div v-else-if="reports.length === 0" class="empty-state">暂无研报数据</div>
        <div v-else class="report-list">
          <a
            v-for="r in reports"
            :key="r.id"
            class="report-item"
            :href="r.source_url || '#'"
            target="_blank"
            rel="noopener"
          >
            <div class="report-title">{{ r.title }}</div>
            <div class="report-meta">
              {{ r.broker }}<template v-if="r.date"> · {{ r.date }}</template>
              <span class="preview-hint">点击跳转 ↗</span>
            </div>
          </a>
        </div>
      </template>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { getMacroSummary } from '../api/macro'
import { getReportsByIndustry } from '../api/news'

const props = defineProps({
  industry:   { type: Object, required: true },
  stocks:     { type: Array,  default: () => [] },
  panelWidth: { type: Number, default: 0 },
})
defineEmits(['back'])

const activeTab = ref('overview')
const tabs = [
  { key: 'overview', label: '公司 & 宏观' },
  { key: 'report',   label: '行业研报' },
]

const companies = computed(() =>
  props.stocks.filter(s => s.industry === props.industry.name)
)

// 宏观数据
const macroData = ref([])

async function loadMacroData() {
  try {
    const items = await getMacroSummary(['CPI', 'PPI', '社融', 'GDP'], 1)
    const list = Array.isArray(items) ? items : []
    macroData.value = list.map(item => ({
      label: (item.indicator_name || item.name || '') + ' 同比',
      value: item.latest_value ?? item.value ?? '--',
      sub:   item.latest_period ?? item.period ?? '',
      trend: (() => {
        if (item.trend) return item.trend
        const v = parseFloat(item.latest_value ?? item.value)
        if (isNaN(v)) return ''
        return v > 0 ? 'up' : v < 0 ? 'down' : ''
      })(),
    }))
  } catch (err) {
    console.error('[loadMacroData]', err)
  }
}

// 行业研报
const reports = ref([])
const reportsLoading = ref(false)

async function loadReports() {
  reportsLoading.value = true
  try {
    const industryCode = props.industry.code || props.industry.name
    const items = await getReportsByIndustry(industryCode, 365)
    const list = Array.isArray(items) ? items : []
    reports.value = list.slice(0, 30).map((item, i) => ({
      id:         item.id || i,
      title:      item.title || '',
      broker:     item.report_org || '--',
      date:       (item.publish_date || '').slice(0, 10),
      source_url: item.source_url || '',
      publish_date: item.publish_date || '',
    }))
  } catch (err) {
    console.error('[loadReports]', err)
  } finally {
    reportsLoading.value = false
  }
}

onMounted(() => {
  loadMacroData()
  loadReports()
})

watch(() => props.industry, () => {
  activeTab.value = 'overview'
  loadMacroData()
  loadReports()
})
</script>

<style scoped>
.detail-panel {
  display: flex; flex-direction: column; height: 100%;
  background: var(--bg-panel);
}

.detail-header {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  display: flex; align-items: center; gap: 8px;
  overflow: hidden;
}

.back-btn {
  display: inline-flex; align-items: center; gap: 4px;
  background: var(--bg-card2); border: 1px solid var(--border);
  border-radius: 24px; color: var(--text-secondary);
  cursor: pointer; font-size: 13px; font-weight: 500;
  padding: 5px 12px 5px 8px; flex-shrink: 0;
  transition: background .2s, border-color .2s, color .2s, transform .15s;
}
.back-btn:hover {
  background: rgba(75,169,154,0.1); border-color: var(--accent);
  color: var(--accent); transform: translateX(-2px);
}
.back-arrow { font-size: 18px; line-height: 1; font-weight: 300; }
.back-text  { font-size: 13px; }

.detail-name {
  font-size: 15px; font-weight: 700; color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  min-width: 0; flex-shrink: 1;
}
.detail-code {
  font-size: 11px; color: var(--text-muted);
  background: var(--bg-card2); border: 1px solid var(--border);
  border-radius: 4px; padding: 1px 5px;
  white-space: nowrap; flex-shrink: 0;
}
.detail-spacer { flex: 1; }
.detail-change { font-size: 13px; font-weight: 700; white-space: nowrap; flex-shrink: 0; }
.red   { color: var(--red); }
.green { color: var(--green); }

/* Tab 栏 */
.tab-bar {
  display: flex; flex-shrink: 0;
  border-bottom: 2px solid var(--border);
  background: var(--bg-card);
}
.tab-btn {
  flex: 1; padding: 10px 0;
  background: none; border: none;
  border-bottom: 3px solid transparent;
  color: var(--text-muted); font-size: 13px; font-weight: 500;
  cursor: pointer; transition: all .2s; outline: none;
}
.tab-btn:hover { color: var(--text-primary); background: rgba(75,169,154,0.08); }
.tab-btn.active {
  color: var(--accent); background: rgba(75,169,154,0.12);
  border-bottom-color: var(--accent); font-weight: 600;
}

.content-scroll { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 16px; }

.section-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 10px; }

/* 成分股列表 */
.company-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 4px; }
.company-item {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 8px; padding: 9px 12px;
}
.ci-left  { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.ci-name  { font-size: 13px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ci-code  { font-size: 10px; color: var(--text-muted); }
.ci-right { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; flex-shrink: 0; }
.ci-price { font-size: 14px; font-weight: 700; }
.ci-change{ font-size: 11px; font-weight: 500; }

/* 宏观数据 */
.macro-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.macro-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 8px; padding: 10px 12px;
}
.macro-label { font-size: 11px; color: var(--text-muted); margin-bottom: 4px; }
.macro-value { font-size: 16px; font-weight: 700; color: var(--text-primary); }
.macro-sub   { font-size: 10px; color: var(--text-muted); margin-top: 2px; }

/* 研报列表 */
.report-list { display: flex; flex-direction: column; gap: 10px; }
.report-item {
  background: var(--bg-card); border-radius: 10px;
  padding: 12px; border: 1px solid var(--border);
  cursor: pointer; transition: border-color .2s, box-shadow .2s;
}
.report-item:hover {
  border-color: var(--accent);
  box-shadow: 0 2px 12px rgba(75,169,154,0.12);
}
.report-title { font-size: 13px; font-weight: 500; color: var(--text-primary); margin-bottom: 6px; }
.report-meta  { font-size: 11px; color: var(--text-muted); display: flex; align-items: center; gap: 6px; }
.preview-hint {
  margin-left: auto;
  font-size: 10px; color: var(--accent);
  opacity: 0; transition: opacity .2s;
}
.report-item:hover .preview-hint { opacity: 1; }

.empty-state { text-align: center; padding: 32px; color: var(--text-muted); font-size: 13px; }

/* 预览弹窗 */
.preview-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(4px);
}
.preview-modal {
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: 14px;
  width: min(680px, 92vw);
  max-height: 85vh;
  display: flex; flex-direction: column;
  box-shadow: 0 24px 60px rgba(0,0,0,0.3);
  overflow: hidden;
}
.preview-header {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.preview-title {
  flex: 1; font-size: 13px; font-weight: 600; color: var(--text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.preview-close {
  background: none; border: none; cursor: pointer;
  color: var(--text-muted); font-size: 16px; padding: 2px 6px;
  border-radius: 6px; transition: background .2s, color .2s;
}
.preview-close:hover { background: var(--bg-card2); color: var(--text-primary); }

.preview-body {
  flex: 1; overflow-y: auto; padding: 16px;
}
.preview-loading {
  display: flex; flex-direction: column; align-items: center;
  gap: 12px; padding: 48px; color: var(--text-muted); font-size: 13px;
}
.spinner {
  width: 28px; height: 28px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.preview-error {
  text-align: center; padding: 48px;
  color: var(--text-muted); font-size: 13px; line-height: 1.6;
}
.preview-pages { display: flex; flex-direction: column; gap: 20px; }
.preview-page {
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}
.preview-page-label {
  font-size: 11px; font-weight: 700; color: var(--accent2);
  background: rgba(75,169,154,0.08);
  padding: 6px 14px;
  border-bottom: 1px solid var(--border);
}
.preview-text {
  font-size: 13px; line-height: 1.9; color: var(--text-primary);
  white-space: pre-wrap; word-break: break-word;
  padding: 16px 18px;
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
}
</style>
