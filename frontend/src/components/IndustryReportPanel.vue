<template>
  <div class="report-panel">
    <div class="section-title">行业研报</div>
    <div v-if="loading" class="empty-state">加载中...</div>
    <div v-else-if="reports.length === 0" class="empty-state">暂无研报数据</div>
    <div v-else class="report-list">
      <div v-for="r in reports" :key="r.id" class="report-item">
        <div class="report-title">{{ r.title }}</div>
        <div class="report-meta">{{ r.broker }}<template v-if="r.date"> · {{ r.date }}</template></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getReportsByIndustry } from '../api/news'

const reports = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const items = await getReportsByIndustry('', 365)
    const list = Array.isArray(items) ? items : []
    reports.value = list.slice(0, 30).map((item, i) => ({
      id: item.id || i,
      title: item.title || '',
      broker: item.report_org || '--',
      date: (item.publish_date || '').slice(0, 10),
    }))
  } catch (err) {
    console.error('[IndustryReportPanel]', err)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.report-panel { padding: 16px; height: 100%; overflow-y: auto; }

.section-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 12px; }

.report-list { display: flex; flex-direction: column; gap: 10px; }
.report-item {
  background: var(--bg-card); border-radius: 10px;
  padding: 12px; border: 1px solid var(--border);
}
.report-title { font-size: 13px; font-weight: 500; color: var(--text-primary); margin-bottom: 6px; }
.report-meta  { font-size: 11px; color: var(--text-muted); }

.empty-state { text-align: center; padding: 32px; color: var(--text-muted); font-size: 13px; }
</style>
