<template>
  <div class="recycle-bin">
    <div class="header">
      <h1>🗑 回收站</h1>
      <button @click="$router.back()" class="btn btn-secondary">← 返回</button>
    </div>

    <div v-if="items.length" class="list">
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

    <div class="pagination" v-if="total > pageSize">
      <button @click="page--; load()" :disabled="page === 1">上一页</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button @click="page++; load()" :disabled="page >= totalPages">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { recipeApi } from '../services/api';
import { toast } from '../composables/useToast';
import type { Recipe } from '../types';

const items = ref<Recipe[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));

function formatTime(t: string) {
  return new Date(t).toLocaleString();
}

async function load() {
  try {
    const res = await recipeApi.list({
      deleted: true,
      page: page.value,
      page_size: pageSize
    });
    items.value = res.data;
    total.value = res.total;
  } catch (e) {
    console.error('load recycle bin failed', e);
  }
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

onMounted(load);
</script>

<style scoped>
.recycle-bin { padding: 20px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
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
.btn-small { padding: 8px 14px; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; min-height: 36px; }
.btn-confirm { background: #4a90d9; color: white; }
.btn-danger { background: #f44336; color: white; }
.empty-state { text-align: center; padding: 60px 20px; color: #888; }
.pagination { display: flex; justify-content: center; align-items: center; gap: 20px; margin-top: 20px; }
.pagination button { min-height: 44px; padding: 8px 16px; border: 1px solid #ddd; border-radius: 6px; background: white; cursor: pointer; }

@media (max-width: 767px) {
  .recycle-bin { padding: 16px; }
  .header h1 { text-align: center; }
  .list-row { flex-direction: column; align-items: stretch; }
  .row-actions { width: 100%; }
  .row-actions .btn-small { flex: 1; }
}
</style>
