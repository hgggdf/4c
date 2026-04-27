<template>
  <div class="news-panel">
    <div class="news-toolbar">
      <span class="news-count" v-if="!loading">{{ news.length }} 条</span>
    </div>

    <div class="news-list" v-if="!loading && news.length">
      <div
        v-for="item in news"
        :key="item.id"
        class="news-item"
        @click="openDetail(item)"
      >
        <div class="news-item-top">
          <span class="news-type-badge" :class="typeBadgeClass(item.news_type)">
            {{ typeLabel(item.news_type) }}
          </span>
          <span class="news-time">{{ fmtTime(item.publish_time) }}</span>
        </div>
        <div class="news-title">{{ item.title }}</div>
        <div class="news-meta" v-if="item.source_name">{{ item.source_name }}</div>
      </div>
    </div>

    <div v-else-if="loading" class="empty-state">加载中…</div>
    <div v-else class="empty-state">暂无新闻数据</div>

    <!-- 详情弹窗 -->
    <Teleport to="body">
      <div v-if="detail.visible" class="detail-overlay" @click.self="detail.visible = false">
        <div class="detail-modal">
          <div class="detail-header">
            <span class="detail-title">{{ detail.item?.title }}</span>
            <a v-if="isSpecificUrl(detail.item?.source_url)" :href="detail.item.source_url" target="_blank" class="detail-link-btn">查看原文 ↗</a>
            <button class="detail-close" @click="detail.visible = false">✕</button>
          </div>
          <div class="detail-body">
            <div class="detail-meta-row">
              <span class="news-type-badge" :class="typeBadgeClass(detail.item?.news_type)">{{ typeLabel(detail.item?.news_type) }}</span>
              <span class="detail-meta-time">{{ detail.item?.publish_time }}</span>
              <span class="detail-meta-src" v-if="detail.item?.source_name">{{ detail.item.source_name }}</span>
            </div>
            <div class="detail-content">{{ detail.item?.content || detail.item?.summary_text || '暂无内容' }}</div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getNewsLatest } from '../api/news'

const news = ref([])
const loading = ref(false)
const detail = ref({ visible: false, item: null })

function typeLabel(t) {
  return { industry_news: '行业', company_news: '个股', macro_news: '宏观' }[t] || '资讯'
}

function typeBadgeClass(t) {
  return { industry_news: 'badge-industry', company_news: 'badge-company', macro_news: 'badge-macro' }[t] || 'badge-default'
}

// 只有 URL 包含具体路径（不是纯首页域名）才显示跳转按钮
function isSpecificUrl(url) {
  if (!url) return false
  try {
    const u = new URL(url)
    return u.pathname.length > 1  // 排除 "/" 这种纯首页
  } catch {
    return false
  }
}

function fmtTime(t) {
  if (!t) return ''
  // "2026-04-27 04:59:23" → "04-27 04:59"
  const m = String(t).match(/\d{4}-(\d{2}-\d{2}) (\d{2}:\d{2})/)
  return m ? `${m[1]} ${m[2]}` : String(t).slice(0, 16)
}

function openDetail(item) {
  detail.value = { visible: true, item }
}

async function load() {
  loading.value = true
  try {
    const res = await getNewsLatest(7)
    news.value = Array.isArray(res) ? res : (res?.data ?? [])
  } catch (e) {
    console.error('[NewsPanel]', e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.news-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.news-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px 8px;
  flex-shrink: 0;
  border-bottom: 1px solid var(--border);
}

.news-count {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}

.news-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.news-item {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
  transition: border-color .15s, box-shadow .15s;
}
.news-item:hover {
  border-color: var(--accent);
  box-shadow: 0 2px 10px rgba(75,169,154,0.1);
}

.news-item-top {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 5px;
}

.news-type-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 20px;
}
.badge-industry { background: rgba(99,102,241,0.1); color: #4f46e5; border: 1px solid rgba(99,102,241,0.2); }
.badge-company  { background: rgba(75,169,154,0.1); color: var(--accent2); border: 1px solid rgba(75,169,154,0.25); }
.badge-macro    { background: rgba(232,160,32,0.1); color: #a07010; border: 1px solid rgba(232,160,32,0.2); }
.badge-default  { background: var(--bg-card2); color: var(--text-muted); border: 1px solid var(--border); }

.news-time {
  font-size: 10px;
  color: var(--text-muted);
  margin-left: auto;
}

.news-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  line-height: 1.5;
  margin-bottom: 4px;
}

.news-meta {
  font-size: 11px;
  color: var(--text-muted);
}

.empty-state {
  text-align: center;
  padding: 48px 16px;
  color: var(--text-muted);
  font-size: 13px;
}

/* ── 详情弹窗 ── */
.detail-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.55);
  display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(4px);
}
.detail-modal {
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: 14px;
  width: min(640px, 92vw);
  max-height: 82vh;
  display: flex; flex-direction: column;
  box-shadow: 0 24px 60px rgba(0,0,0,0.28);
  overflow: hidden;
}
.detail-header {
  display: flex; align-items: center; gap: 10px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.detail-title {
  flex: 1;
  font-size: 13px; font-weight: 600; color: var(--text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.detail-link-btn {
  font-size: 12px; font-weight: 500; color: var(--accent);
  text-decoration: none; padding: 3px 10px;
  border: 1px solid var(--accent); border-radius: 6px;
  transition: background .15s; white-space: nowrap; flex-shrink: 0;
}
.detail-link-btn:hover { background: rgba(75,169,154,0.1); }
.detail-close {
  background: none; border: none; cursor: pointer;
  color: var(--text-muted); font-size: 16px; padding: 2px 6px;
  border-radius: 6px; transition: background .15s, color .15s;
}
.detail-close:hover { background: var(--bg-card2); color: var(--text-primary); }

.detail-body { flex: 1; overflow-y: auto; padding: 16px 18px; }
.detail-meta-row {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 14px;
}
.detail-meta-time { font-size: 11px; color: var(--text-muted); }
.detail-meta-src  { font-size: 11px; color: var(--text-muted); }
.detail-content {
  font-size: 13px; line-height: 1.9;
  color: var(--text-primary);
  white-space: pre-wrap; word-break: break-word;
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
}
</style>
