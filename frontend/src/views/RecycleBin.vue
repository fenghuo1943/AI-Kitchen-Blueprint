<template>
  <div class="recycle-bin">
    <div class="header">
      <button @click="$router.back()" class="btn-back">返回</button>
      <h1>回收站</h1>
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
      <div v-for="recipe in items" :key="recipe.id" class="list-row">
        <div class="row-main">
          <span class="row-title">{{ recipe.title }}</span>
          <span v-if="recipe.deleted_at" class="row-time">删除于 {{ formatTime(recipe.deleted_at) }}</span>
        </div>
        <div class="row-actions">
          <button class="btn-small btn-confirm" @click="restore(recipe.id)">恢复</button>
          <button class="btn-small btn-danger" @click="hardDelete(recipe.id)">彻底删除</button>
        </div>
      </div>
    </div>
    <div v-else class="empty-state">🗑 回收站是空的</div>

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
import { recipeApi } from '../services/api';
import { toast } from '../composables/useToast';
import { usePageSize } from '../composables/usePageSize';
import { useInfiniteList } from '../composables/useInfiniteList';
import LoadMoreFooter from '../components/LoadMoreFooter.vue';
import type { Recipe } from '../types';

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
} = useInfiniteList<Recipe>({
  fetcher: (page, pageSize) => recipeApi.list({ deleted: true, page, page_size: pageSize }),
  getPageSize: () => pageSize.value
});

function formatTime(t: string) {
  return new Date(t).toLocaleString();
}

async function restore(id: string) {
  try {
    await recipeApi.restore(id);
    toast('已恢复');
    load();
  } catch (e) {
    console.error('restore failed', e);
  }
}

async function hardDelete(id: string) {
  if (!window.confirm('彻底删除后不可恢复，确定继续？')) return;
  try {
    await recipeApi.delete(id, true);
    toast('已彻底删除');
    load();
  } catch (e) {
    console.error('hard delete failed', e);
  }
}

onMounted(() => {
  pageSizeReady.then(load);
});
</script>

<style scoped>
.recycle-bin { padding: 20px; }
.header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.header h1 { margin: 0; }
.list { background: white; border-radius: 12px; overflow: hidden; }
.list-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 16px; border-bottom: 1px solid #f0f0f0; gap: 12px;
}
.row-main { flex: 1; display: flex; flex-direction: column; gap: 4px; }
.row-title { font-weight: 500; color: #333; }
.row-time { font-size: 12px; color: #999; }
.row-actions { display: flex; gap: 8px; }

.btn { padding: 10px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; min-height: 44px; }
.btn-secondary { background: #f0f0f0; color: #333; }
.btn-primary { background: #4a90d9; color: white; }
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
.btn-small { padding: 8px 14px; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; min-height: 36px; }
.btn-confirm { background: #4a90d9; color: white; }
.btn-danger { background: #f44336; color: white; }

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
  .recycle-bin { padding: 16px; }
  .list-row { flex-direction: row; align-items: center; }
  .row-actions { flex-direction: column; align-items: stretch; gap: 6px; }
  .row-actions .btn-small { min-height: 32px; padding: 6px 12px; }
}
</style>
