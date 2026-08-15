<template>
  <div class="history">
    <div class="header">
      <h1>🕐 浏览历史</h1>
      <button v-if="items.length" class="btn btn-secondary" @click="clearAll">清空</button>
    </div>

    <div v-if="loading && !items.length" class="empty-state">
      <span class="spinner" aria-hidden="true"></span>
      <p>加载中...</p>
    </div>
    <div v-else-if="loadError && !items.length" class="empty-state">
      <p>加载失败</p>
      <button class="btn btn-primary" @click="load">点击重试</button>
    </div>
    <div v-else-if="items.length" class="list">
      <div v-for="item in items" :key="item.id" class="list-row">
        <div class="row-main" @click="goDetail(item.recipe_id)">
          <span class="row-title">{{ item.recipe_title }}</span>
          <span class="row-time">浏览于 {{ formatTime(item.viewed_at) }}</span>
        </div>
        <button class="btn-small btn-cancel" @click="removeOne(item)">删除</button>
      </div>
    </div>
    <div v-else class="empty-state">📭 暂无浏览记录</div>

    <LoadMoreFooter
      :show="total > pageSize"
      :loading="loadingMore"
      :error="loadError"
      :finished="!hasMore && total > pageSize"
      @retry="loadMore"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { historyApi } from '../services/api';
import { toast } from '../composables/useToast';
import { usePageSize } from '../composables/usePageSize';
import { useInfiniteList } from '../composables/useInfiniteList';
import LoadMoreFooter from '../components/LoadMoreFooter.vue';
import type { HistoryItem } from '../types';

const router = useRouter();
const { pageSize, ready: pageSizeReady } = usePageSize();
const {
  items,
  total,
  loading,
  loadingMore,
  loadError,
  hasMore,
  reset: load,
  loadMore
} = useInfiniteList<HistoryItem>({
  fetcher: (page, pageSize) => historyApi.list({ page, page_size: pageSize }),
  getPageSize: () => pageSize.value
});

function formatTime(t: string) {
  return new Date(t).toLocaleString();
}

async function removeOne(item: HistoryItem) {
  try {
    await historyApi.removeOne(item.recipe_id);
    toast('已删除该记录');
    load();
  } catch (e) {
    console.error('remove history failed', e);
  }
}

async function clearAll() {
  if (!window.confirm('确定清空全部浏览历史？')) return;
  try {
    await historyApi.clear();
    toast('已清空');
    load();
  } catch (e) {
    console.error('clear history failed', e);
  }
}

function goDetail(id: string) {
  router.push(`/recipes/${id}`);
}

onMounted(() => {
  pageSizeReady.then(load);
});
</script>

<style scoped>
.history { padding: 20px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.header h1 { margin: 0; }
.list { background: white; border-radius: 12px; overflow: hidden; }
.list-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 16px; border-bottom: 1px solid #f0f0f0;
}
.row-main { cursor: pointer; flex: 1; display: flex; flex-direction: column; gap: 4px; }
.row-title { font-weight: 500; color: #333; }
.row-time { font-size: 12px; color: #999; }

.btn { padding: 10px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; min-height: 44px; }
.btn-secondary { background: #f0f0f0; color: #333; }
.btn-primary { background: #4a90d9; color: white; }
.btn-small { padding: 8px 14px; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; min-height: 36px; }
.btn-cancel { background: #f8d7da; color: #721c24; }

.empty-state { text-align: center; padding: 60px 20px; color: #888; }
.empty-state p { margin: 0 0 16px; }
.spinner {
  display: inline-block;
  width: 32px; height: 32px;
  border: 3px solid #e0e0e0; border-top-color: #4a90d9;
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 767px) {
  .history { padding: 16px; }
  .header h1 { text-align: center; }
  .list-row { flex-direction: column; gap: 8px; align-items: stretch; }
  .btn-small { width: 100%; }
}
</style>
