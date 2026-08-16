<template>
  <div class="recycle-bin">
    <div class="header">
      <div class="header-left">
        <button @click="goBack" class="btn-back" aria-label="返回">返回</button>
        <h1>回收站</h1>
      </div>
    </div>

    <div class="type-tabs">
      <button
        v-for="t in tabs"
        :key="t.value"
        :class="['tab-btn', activeType === t.value ? 'active' : '']"
        @click="switchTab(t.value)"
      >{{ t.label }}</button>
    </div>

    <div class="toolbar">
      <template v-if="selecting">
        <label class="select-all">
          <input type="checkbox" :checked="allSelected" @change="toggleSelectAll" />
          <span>全选</span>
        </label>
        <span class="selected-count">已选 {{ selectedIds.size }} 项</span>
        <div class="toolbar-actions">
          <button
            class="btn btn-danger"
            :disabled="!selectedIds.size"
            @click="batchHardDelete"
          >批量彻底删除</button>
          <button class="btn btn-secondary" @click="exitSelect">取消</button>
        </div>
      </template>
      <button v-else class="btn btn-secondary" :disabled="!items.length" @click="enterSelect">批量删除</button>
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
      <div v-for="row in items" :key="row.id" class="list-row">
        <input
          v-if="selecting"
          type="checkbox"
          class="row-checkbox"
          :checked="selectedIds.has(row.id)"
          @change="toggleSelect(row.id)"
        />
        <div class="row-main">
          <span class="row-title">{{ rowName(row) }}</span>
          <span v-if="rowSub(row)" class="row-sub">{{ rowSub(row) }}</span>
          <span v-if="row.deleted_at" class="row-time">删除于 {{ formatTime(row.deleted_at) }}</span>
        </div>
        <div v-if="!selecting" class="row-actions">
          <button class="btn-small btn-confirm" @click="restore(row.id)">恢复</button>
          <button class="btn-small btn-danger" @click="hardDelete(row.id)">彻底删除</button>
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
import { ref, reactive, computed, onMounted } from 'vue';
import { recipeApi, ingredientApi, seasoningApi } from '../services/api';
import { toast } from '../composables/useToast';
import { useGoBack } from '../composables/useGoBack';
import { usePageSize } from '../composables/usePageSize';
import { useInfiniteList } from '../composables/useInfiniteList';
import LoadMoreFooter from '../components/LoadMoreFooter.vue';
import type { Recipe, Ingredient, Seasoning } from '../types';

const { goBack } = useGoBack('/me');

/** 回收站条目类型：菜谱 / 食材 / 调料 */
type RecycleType = 'recipe' | 'ingredient' | 'seasoning';
type RecycleItem = Recipe | Ingredient | Seasoning;

const tabs = [
  { label: '菜谱回收站', value: 'recipe' as RecycleType },
  { label: '食材回收站', value: 'ingredient' as RecycleType },
  { label: '调料回收站', value: 'seasoning' as RecycleType }
];
const activeType = ref<RecycleType>('recipe');

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
} = useInfiniteList<RecycleItem>({
  fetcher: (page, pageSize) => {
    if (activeType.value === 'recipe') {
      return recipeApi.list({ deleted: true, page, page_size: pageSize });
    }
    if (activeType.value === 'ingredient') {
      return ingredientApi.list({ deleted: true, page, page_size: pageSize });
    }
    return seasoningApi.list({ deleted: true, page, page_size: pageSize });
  },
  getPageSize: () => pageSize.value
});

// ---- 批量删除（多选模式）----
const selecting = ref(false);
const selectedIds = reactive(new Set<string>());
const allSelected = computed(() =>
  items.value.length > 0 && items.value.every(row => selectedIds.has(row.id))
);

function enterSelect() {
  if (!items.value.length) return;
  selecting.value = true;
  selectedIds.clear();
}

function exitSelect() {
  selecting.value = false;
  selectedIds.clear();
}

function toggleSelect(id: string) {
  if (selectedIds.has(id)) selectedIds.delete(id);
  else selectedIds.add(id);
}

function toggleSelectAll() {
  if (allSelected.value) {
    selectedIds.clear();
  } else {
    items.value.forEach(row => selectedIds.add(row.id));
  }
}

function rowName(row: RecycleItem) {
  return 'title' in row ? row.title : row.canonical_name;
}

function rowSub(row: RecycleItem) {
  return 'category_name' in row && row.category_name ? row.category_name : '';
}

function formatTime(t: string) {
  return new Date(t).toLocaleString();
}

function switchTab(type: RecycleType) {
  if (activeType.value === type) return;
  exitSelect();
  activeType.value = type;
  // 切换标签清空旧数据，避免上一标签的列表短暂残留
  items.value = [];
  load();
}

async function restore(id: string) {
  try {
    if (activeType.value === 'recipe') {
      await recipeApi.restore(id);
    } else if (activeType.value === 'ingredient') {
      await ingredientApi.restore(id);
    } else {
      await seasoningApi.restore(id);
    }
    toast('已恢复');
    load();
  } catch (e: any) {
    console.error('restore failed', e);
    toast(e?.response?.data?.detail || '恢复失败', 'error');
  }
}

async function hardDelete(id: string) {
  if (!window.confirm('彻底删除后不可恢复，确定继续？')) return;
  try {
    if (activeType.value === 'recipe') {
      await recipeApi.delete(id, true);
    } else if (activeType.value === 'ingredient') {
      await ingredientApi.delete(id, true);
    } else {
      await seasoningApi.delete(id, true);
    }
    toast('已彻底删除');
    load();
  } catch (e: any) {
    console.error('hard delete failed', e);
    toast(e?.response?.data?.detail || '删除失败', 'error');
  }
}

async function batchHardDelete() {
  const ids = [...selectedIds];
  if (!ids.length) return;
  if (!window.confirm(`确定彻底删除选中的 ${ids.length} 项？此操作不可恢复。`)) return;

  try {
    let result;
    if (activeType.value === 'recipe') {
      result = await recipeApi.batchDelete(ids);
    } else if (activeType.value === 'ingredient') {
      result = await ingredientApi.batchDelete(ids);
    } else {
      result = await seasoningApi.batchDelete(ids);
    }
    const failed = result.failed || [];
    if (failed.length) {
      const names = failed.slice(0, 3).map(f => `${f.name}（${f.reason}）`).join('、');
      const more = failed.length > 3 ? ` 等 ${failed.length} 项` : '';
      toast(`已彻底删除 ${result.deleted_count} 项，${failed.length} 项无法删除：${names}${more}`, 'error');
    } else {
      toast(`已彻底删除 ${ids.length} 项`);
    }
    exitSelect();
    load();
  } catch (e: any) {
    console.error('batch delete failed', e);
    toast(e?.response?.data?.detail || '批量删除失败', 'error');
  }
}

onMounted(() => {
  pageSizeReady.then(load);
});
</script>

<style scoped>
.recycle-bin { padding: 20px; }
.header { display: flex; align-items: center; margin-bottom: 16px; }
.header-left { display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1; }
.header h1 { margin: 0; }
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

.type-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.tab-btn {
  padding: 10px 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  font-size: 14px;
  min-height: 44px;
}
.tab-btn.active { background: #4a90d9; color: white; border-color: #4a90d9; }

.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.select-all { display: inline-flex; align-items: center; gap: 6px; font-size: 14px; color: #333; cursor: pointer; }
.select-all input { width: 18px; height: 18px; }
.selected-count { font-size: 14px; color: #666; }
.toolbar-actions { display: flex; gap: 8px; margin-left: auto; }

.list { background: white; border-radius: 12px; overflow: hidden; }
.list-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 16px; border-bottom: 1px solid #f0f0f0; gap: 12px;
}
.row-checkbox { width: 18px; height: 18px; flex-shrink: 0; }
.row-main { flex: 1; display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.row-title { font-weight: 500; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.row-sub { font-size: 12px; color: #4a90d9; }
.row-time { font-size: 12px; color: #999; }
.row-actions { display: flex; gap: 8px; flex-shrink: 0; }

.btn { padding: 10px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; min-height: 44px; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { background: #f0f0f0; color: #333; }
.btn-primary { background: #4a90d9; color: white; }
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
  .header h1 { text-align: center; }
  .header-left { justify-content: center; position: relative; width: 100%; }
  .btn-back { position: absolute; left: 0; }
  .type-tabs { width: 100%; }
  .tab-btn { flex: 1; padding: 10px 4px; }
  .toolbar-actions { margin-left: 0; width: 100%; }
  .toolbar-actions .btn { flex: 1; }
  .list-row { flex-direction: row; align-items: center; gap: 8px; }
  .row-actions { flex-direction: column; align-items: stretch; gap: 6px; }
  .row-actions .btn-small { min-height: 32px; padding: 6px 12px; }
}
</style>
