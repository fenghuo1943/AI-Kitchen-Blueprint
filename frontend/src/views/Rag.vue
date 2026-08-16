<template>
  <div class="rag">
    <div class="header">
      <div class="header-left">
        <button @click="goBack" class="btn-back" aria-label="返回">返回</button>
        <h1>AI 语义检索</h1>
      </div>
    </div>

    <!-- 索引状态 -->
    <section class="card status-card">
      <div class="card-head">
        <h3>索引状态</h3>
        <div class="head-actions">
          <button class="btn btn-secondary btn-small" :disabled="loadingStatus" @click="loadStatus">
            {{ loadingStatus ? '刷新中…' : '刷新' }}
          </button>
          <button class="btn btn-primary btn-small" :disabled="!!status && status.running.includes('rebuild')" @click="rebuild">
            全量重建
          </button>
        </div>
      </div>

      <div v-if="status" class="stats">
        <div class="stat">
          <div class="stat-num">{{ status.indexed_count }}<span class="stat-unit">/{{ status.published_count }}</span></div>
          <div class="stat-label">已索引菜谱</div>
        </div>
        <div class="stat">
          <div class="stat-num" :class="{ warn: pendingCount > 0 }">{{ pendingCount }}</div>
          <div class="stat-label">待索引</div>
        </div>
        <div class="stat">
          <div class="stat-num">{{ chunkTotal }}</div>
          <div class="stat-label">块总数</div>
        </div>
        <div class="stat">
          <div class="stat-num" :class="{ warn: status.failed > 0 }">{{ status.failed }}</div>
          <div class="stat-label">失败任务</div>
        </div>
      </div>
      <div v-else class="empty-hint">加载中…</div>

      <div v-if="status" class="detail">
        <div class="detail-row" v-if="Object.keys(status.breakdown_by_type).length">
          <span class="detail-label">各类型块数</span>
          <span v-for="(count, type) in status.breakdown_by_type" :key="type" class="type-chip">
            {{ chunkTypeLabel(type) }} {{ count }}
          </span>
        </div>
        <div class="detail-row">
          <span class="detail-label">最近重建</span>
          <span>{{ formatTime(status.last_rebuild_at) }}</span>
        </div>
        <div class="detail-row" v-if="status.running.length || status.queued.length">
          <span class="detail-label">后台任务</span>
          <span class="task-list">
            <span v-for="t in status.running" :key="t" class="task task-running">运行中: {{ t }}</span>
            <span v-for="t in status.queued" :key="t" class="task task-queued">排队: {{ t }}</span>
          </span>
        </div>
        <div class="detail-row" v-if="Object.keys(status.last_error).length">
          <span class="detail-label">最近错误</span>
          <span class="error-text">{{ JSON.stringify(status.last_error) }}</span>
        </div>
      </div>
    </section>

    <!-- 语义检索 -->
    <section class="card search-card">
      <h3>语义检索</h3>
      <p class="search-hint">输入自然语言描述想吃的菜，按语义匹配已发布菜谱（如「番茄炒鸡蛋怎么做」「晚上想吃点热乎的」）。</p>

      <div class="search-bar">
        <input
          v-model="query"
          class="search-input"
          type="text"
          maxlength="200"
          placeholder="描述你想吃的菜…"
          @keyup.enter="doSearch"
        />
        <select v-model="topK" class="topk-select">
          <option :value="5">5</option>
          <option :value="10">10</option>
          <option :value="20">20</option>
        </select>
        <button class="btn btn-primary" :disabled="searching" @click="doSearch">
          {{ searching ? '检索中…' : '检索' }}
        </button>
      </div>

      <div v-if="searchMeta && !searchMeta.engine_available" class="warn-banner">
        检索引擎暂不可用：{{ searchMeta.error || '索引/嵌入服务异常' }}。核心功能不受影响，请稍后再试或重建索引。
      </div>

      <div v-if="searchMeta && searchMeta.engine_available && !results.length" class="empty-hint">
        「{{ query }}」没有匹配的菜谱
      </div>

      <div v-if="results.length" class="result-meta">
        找到 {{ searchMeta?.total }} 道菜谱，耗时 {{ searchMeta?.took_ms }}ms
      </div>

      <div class="result-list">
        <div v-for="item in results" :key="item.recipe_id" class="result-item">
          <div class="result-head">
            <router-link :to="`/recipes/${item.recipe_id}`" class="result-title">{{ item.title }}</router-link>
            <span class="score-badge">相关度 {{ item.score.toFixed(2) }}</span>
          </div>
          <div v-if="item.summary" class="result-summary">{{ item.summary }}</div>
          <div v-if="item.matched_ingredients.length" class="result-tags">
            <span v-for="m in item.matched_ingredients" :key="m" class="tag">{{ m }}</span>
          </div>
          <div v-if="item.chunks.length" class="chunk-toggle">
            <button class="btn btn-secondary btn-small" @click="toggleExpand(item.recipe_id)">
              {{ expanded.has(item.recipe_id) ? '收起命中内容' : `查看命中内容（${item.chunks.length}）` }}
            </button>
          </div>
          <div v-if="expanded.has(item.recipe_id)" class="chunks">
            <div v-for="(c, i) in item.chunks" :key="i" class="chunk">
              <div class="chunk-head">
                <span class="chunk-type">{{ chunkTypeLabel(c.chunk_type) }}</span>
                <span class="chunk-score">向量相似 {{ c.vector_score.toFixed(3) }}</span>
              </div>
              <pre class="chunk-text">{{ c.text }}</pre>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { ragApi } from '../services/api';
import { toast } from '../composables/useToast';
import { useGoBack } from '../composables/useGoBack';
import type { IndexStatus, RagSearchItem } from '../types';

const { goBack } = useGoBack('/me');

const CHUNK_TYPE_LABELS: Record<string, string> = {
  overview: '概览',
  ingredients: '食材',
  steps: '步骤',
  tips: '小贴士'
};

function chunkTypeLabel(type: string): string {
  return CHUNK_TYPE_LABELS[type] || type;
}

function formatTime(iso?: string): string {
  if (!iso) return '-';
  const d = new Date(iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleString('zh-CN');
}

// ---- 索引状态 ----
const status = ref<IndexStatus | null>(null);
const loadingStatus = ref(false);

const chunkTotal = computed(() =>
  status.value ? Object.values(status.value.breakdown_by_type).reduce((a, b) => a + b, 0) : 0
);
const pendingCount = computed(() =>
  status.value ? Math.max(0, status.value.published_count - status.value.indexed_count) : 0
);

async function loadStatus() {
  loadingStatus.value = true;
  try {
    status.value = await ragApi.status();
  } catch (e) {
    console.error('load rag status failed', e);
    toast('获取索引状态失败', 'error');
  } finally {
    loadingStatus.value = false;
  }
}

async function rebuild() {
  if (!window.confirm('确定全量重建索引吗？将按已发布菜谱重新生成向量。')) return;
  try {
    await ragApi.rebuild();
    toast('已提交全量重建，后台执行中');
    setTimeout(loadStatus, 1500);
  } catch (e) {
    console.error('rebuild failed', e);
    toast('全量重建提交失败', 'error');
  }
}

// ---- 语义检索 ----
const query = ref('');
const topK = ref(10);
const searching = ref(false);
const results = ref<RagSearchItem[]>([]);
const searchMeta = ref<{ total: number; took_ms: number; engine_available: boolean; error?: string } | null>(null);
const expanded = ref<Set<string>>(new Set());

async function doSearch() {
  const q = query.value.trim();
  if (!q) {
    toast('请输入查询内容', 'error');
    return;
  }
  searching.value = true;
  searchMeta.value = null;
  try {
    const res = await ragApi.search({ query: q, top_k: topK.value });
    results.value = res.results;
    searchMeta.value = {
      total: res.total,
      took_ms: res.took_ms,
      engine_available: res.engine_available,
      error: res.error
    };
  } catch (e) {
    console.error('rag search failed', e);
    results.value = [];
    toast('检索失败，请稍后再试', 'error');
  } finally {
    searching.value = false;
  }
}

function toggleExpand(recipeId: string) {
  const next = new Set(expanded.value);
  if (next.has(recipeId)) next.delete(recipeId);
  else next.add(recipeId);
  expanded.value = next;
}

onMounted(loadStatus);
</script>

<style scoped>
.rag { padding: 20px; max-width: 900px; margin: 0 auto; }
.header {
  position: sticky;
  top: var(--navbar-height, 64px);
  z-index: 150;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 16px 0;
  margin-bottom: 20px;
  background: #f5f5f5;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}
.header h1 { margin: 0; font-size: 1.3rem; }
.btn-back {
  height: 36px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid #0784ff;
  border-radius: 8px;
  cursor: pointer;
  flex-shrink: 0;
  color: #0784ff;
  font-size: 14px;
  font-weight: 500;
}
.btn-back:hover { background: rgba(7, 132, 255, 0.08); }

.card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.card h3 { margin: 0; font-size: 1rem; }
.head-actions { display: flex; gap: 8px; }

.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 14px; }
.stat {
  background: #f7f8fa; border-radius: 10px; padding: 14px 10px; text-align: center;
}
.stat-num { font-size: 1.5rem; font-weight: 600; color: #333; }
.stat-num.warn { color: #e67e22; }
.stat-unit { font-size: 0.9rem; color: #999; font-weight: 400; }
.stat-label { font-size: 12px; color: #888; margin-top: 4px; }

.detail-row { display: flex; align-items: flex-start; gap: 10px; padding: 6px 0; font-size: 13px; color: #555; }
.detail-label { color: #999; min-width: 80px; flex-shrink: 0; }
.type-chip {
  background: #eef4fb; color: #4a90d9; border-radius: 20px; padding: 3px 10px; font-size: 12px;
}
.task-list { display: flex; flex-wrap: wrap; gap: 6px; }
.task { font-size: 12px; border-radius: 20px; padding: 2px 10px; }
.task-running { background: #fff3cd; color: #997a00; }
.task-queued { background: #eef4fb; color: #4a90d9; }
.error-text { color: #d9534f; word-break: break-all; }

.search-hint { font-size: 13px; color: #888; margin: 8px 0 14px; }
.search-bar { display: flex; gap: 10px; }
.search-input {
  flex: 1; padding: 12px 14px; border: 1px solid #e0e0e0; border-radius: 8px;
  font-size: 15px; min-height: 46px; outline: none;
}
.search-input:focus { border-color: #4a90d9; }
.topk-select {
  padding: 0 10px; border: 1px solid #e0e0e0; border-radius: 8px; background: white;
  font-size: 14px; min-height: 46px;
}

.btn { padding: 10px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; min-height: 44px; }
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-primary { background: #4a90d9; color: white; }
.btn-secondary { background: #f0f0f0; color: #333; }
.btn-small { padding: 8px 14px; min-height: 36px; font-size: 13px; }

.warn-banner {
  margin-top: 14px; padding: 12px 14px; background: #fff7ed; color: #c05621;
  border-radius: 8px; font-size: 13px;
}
.empty-hint { color: #999; padding: 20px; text-align: center; font-size: 14px; }
.result-meta { margin-top: 14px; font-size: 12px; color: #999; }

.result-list { margin-top: 10px; }
.result-item {
  border: 1px solid #f0f0f0; border-radius: 10px; padding: 14px 16px; margin-bottom: 10px;
}
.result-head { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.result-title { color: #333; font-size: 16px; font-weight: 600; text-decoration: none; }
.result-title:hover { color: #4a90d9; }
.score-badge {
  flex-shrink: 0; background: #e8f4fd; color: #2f7ac9; border-radius: 20px; padding: 3px 10px; font-size: 12px;
}
.result-summary { margin-top: 6px; font-size: 13px; color: #666; }
.result-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.tag { background: #f2f6ee; color: #5a7a3a; border-radius: 4px; padding: 2px 8px; font-size: 12px; }
.chunk-toggle { margin-top: 10px; }

.chunks { margin-top: 10px; border-top: 1px dashed #e8e8e8; padding-top: 10px; }
.chunk { background: #fafbfc; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; }
.chunk-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.chunk-type { font-size: 12px; font-weight: 600; color: #4a90d9; }
.chunk-score { font-size: 12px; color: #999; }
.chunk-text {
  margin: 0; font-size: 13px; line-height: 1.7; color: #444;
  white-space: pre-wrap; word-break: break-word; font-family: inherit;
}

@media (max-width: 767px) {
  .rag { padding: 16px; }
  .stats { grid-template-columns: repeat(2, 1fr); }
  .search-bar { flex-wrap: wrap; }
  .search-input { min-width: 100%; }
  .topk-select { min-height: 44px; }
}
</style>
