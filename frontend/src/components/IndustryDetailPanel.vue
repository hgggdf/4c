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
      >
        <span class="tab-icon">{{ t.icon }}</span>
        <span class="tab-label">{{ t.label }}</span>
      </button>
    </div>

    <div class="content-scroll">

      <!-- 公司 & 宏观 Tab -->
      <div v-if="activeTab === 'overview'">
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
      </div>

      <!-- 行业研报 Tab -->
      <div v-else-if="activeTab === 'report'">
        <div class="section-title">行业研报</div>
        <div v-if="reports.length === 0" class="empty-state">暂无研报数据</div>
        <div class="report-list">
          <div v-for="r in reports" :key="r.id" class="report-item">
            <div class="report-title">{{ r.title }}</div>
            <div class="report-meta">{{ r.broker }}<template v-if="r.date"> · {{ r.date }}</template></div>
            <span class="report-rating" :class="{
              'rating-buy':  r.rating === '买入' || r.rating === '增持',
              'rating-hold': r.rating === '中性' || r.rating === '推荐',
              'rating-sell': r.rating === '卖出' || r.rating === '减持',
            }">{{ r.rating }}</span>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  industry: { type: Object, required: true },
  stocks:   { type: Array,  default: () => [] },
  panelWidth: { type: Number, default: 0 },
})
defineEmits(['back'])

const activeTab = ref('overview')
const tabs = [
  { key: 'overview', label: '公司 & 宏观', icon: '🏢' },
  { key: 'report',   label: '行业研报',   icon: '📄' },
]

// 该行业下的成分股
const companies = computed(() =>
  props.stocks.filter(s => s.industry === props.industry.name)
)

// Mock 宏观数据
const macroData = computed(() => {
  const name = props.industry.name
  const base = [
    { label: 'CPI 同比',    value: '+0.4%',  sub: '2026年3月', trend: 'up' },
    { label: 'PPI 同比',    value: '-2.1%',  sub: '2026年3月', trend: 'down' },
    { label: '社融增速',    value: '+8.3%',  sub: '2026年3月', trend: 'up' },
    { label: 'GDP 增速',    value: '+5.2%',  sub: '2025年全年', trend: 'up' },
  ]
  if (name.includes('眼科') || name.includes('医疗')) {
    return [
      ...base,
      { label: '医疗支出占GDP', value: '6.8%',  sub: '2025年', trend: '' },
      { label: '老龄化率',      value: '21.1%', sub: '2025年', trend: 'up' },
    ]
  }
  if (name.includes('创新药') || name.includes('生物')) {
    return [
      ...base,
      { label: '医药研发投入增速', value: '+12.4%', sub: '2025年', trend: 'up' },
      { label: 'NDA 获批数量',    value: '38 个',   sub: '2025年', trend: 'up' },
    ]
  }
  return base
})

// Mock 行业研报
const REPORT_MOCK = {
  default: [
    { id: 1, title: '医药行业2026年中期策略：集采压力缓解，创新药迎来估值修复', broker: '中信证券', date: '2026-04-10', rating: '增持' },
    { id: 2, title: '医疗服务板块深度报告：消费复苏驱动院外连锁加速扩张', broker: '华泰证券', date: '2026-04-08', rating: '买入' },
    { id: 3, title: '生物制药行业周报：GLP-1赛道国内竞争格局分析', broker: '国泰君安', date: '2026-04-05', rating: '推荐' },
    { id: 4, title: '医药行业政策跟踪：医保谈判规则优化对创新药影响评估', broker: '招商证券', date: '2026-03-28', rating: '中性' },
    { id: 5, title: '眼科医疗行业专题：近视防控政策落地，市场空间测算', broker: '兴业证券', date: '2026-03-20', rating: '买入' },
    { id: 6, title: '原料药板块季报点评：出口景气度持续，成本端压力边际改善', broker: '申万宏源', date: '2026-03-15', rating: '增持' },
  ],
}

const reports = computed(() => REPORT_MOCK.default)
</script>

<style scoped>
.detail-panel {
  display: flex; flex-direction: column; height: 100%;
  background: var(--bg-panel);
}

/* ── Header ── */
.detail-header {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  overflow: hidden;
}

.back-btn {
  display: inline-flex; align-items: center; gap: 4px;
  background: var(--bg-card2);
  border: 1px solid var(--border);
  border-radius: 24px;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 13px; font-weight: 500;
  padding: 5px 12px 5px 8px;
  flex-shrink: 0;
  transition: background .2s, border-color .2s, color .2s, transform .15s;
}
.back-btn:hover {
  background: rgba(75,169,154,0.1);
  border-color: var(--accent);
  color: var(--accent);
  transform: translateX(-2px);
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
  background: var(--bg-card2);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1px 5px;
  white-space: nowrap; flex-shrink: 0;
}
.detail-spacer { flex: 1; }
.detail-change { font-size: 13px; font-weight: 700; white-space: nowrap; flex-shrink: 0; }
.red   { color: var(--red); }
.green { color: var(--green); }

/* ── Tab 栏 ── */
.tab-bar {
  display: flex; flex-shrink: 0;
  width: 100%;
  border-bottom: 2px solid var(--border);
  background: var(--bg-card);
}
.tab-btn {
  flex: 1;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 6px; padding: 12px 0;
  background: none; border: none;
  border-right: 1px solid var(--border);
  border-bottom: 3px solid transparent;
  color: var(--text-muted);
  font-size: 13px; font-weight: 500;
  cursor: pointer; transition: all .2s; outline: none;
}
.tab-btn:last-child { border-right: none; }
.tab-btn:hover { color: var(--text-primary); background: rgba(75,169,154,0.08); }
.tab-btn.active {
  color: var(--accent);
  background: rgba(75,169,154,0.12);
  border-bottom-color: var(--accent);
  font-weight: 600;
}
.tab-icon  { font-size: 22px; line-height: 1; }
.tab-label { font-size: 13px; font-weight: 600; }

.content-scroll { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 16px; }

.section-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 10px; }

/* ── 成分股列表 ── */
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

/* ── 宏观数据格 ── */
.macro-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.macro-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 8px; padding: 10px 12px;
}
.macro-label { font-size: 11px; color: var(--text-muted); margin-bottom: 4px; }
.macro-value { font-size: 16px; font-weight: 700; color: var(--text-primary); }
.macro-sub   { font-size: 10px; color: var(--text-muted); margin-top: 2px; }

/* ── 研报（与个股详情页一致） ── */
.report-list { display: flex; flex-direction: column; gap: 10px; }
.report-item {
  background: var(--bg-card); border-radius: 10px;
  padding: 12px; border: 1px solid var(--border); position: relative;
}
.report-title { font-size: 13px; font-weight: 500; color: var(--text-primary); margin-bottom: 6px; padding-right: 60px; }
.report-meta  { font-size: 11px; color: var(--text-muted); }
.report-rating {
  position: absolute; top: 12px; right: 12px;
  font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px;
}
.rating-buy  { background: rgba(34,197,94,.12);  color: var(--green); }
.rating-hold { background: rgba(245,158,11,.12); color: var(--gold); }
.rating-sell { background: rgba(239,68,68,.12);  color: var(--red); }

.empty-state { text-align: center; padding: 32px; color: var(--text-muted); font-size: 13px; }
</style>
