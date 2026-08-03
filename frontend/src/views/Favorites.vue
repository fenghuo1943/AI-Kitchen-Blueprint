<template>
  <div class="favorites">
    <div class="header">
      <h1>♥ 我的收藏</h1>
    </div>

    <div v-if="items.length" class="list">
      <div v-for="item in items" :key="item.id" class="list-row">
        <div class="row-main" @click="goDetail(item.recipe_id)">
          <span class="row-title">{{ item.recipe_title }}</span>
          <span class="row-time">收藏于 {{ formatTime(item.created_at) }}</span>
        </div>
        <button class="btn-small btn-cancel" @click="remove(item)">取消收藏</button>
      </div>
    </div>
    <div v-else class="empty-state">📭 还没有收藏，去菜谱库点亮收藏吧</div>

    <div class="pagination" v-if="total > pageSize">
      <button @click="page--; load()" :disabled="page === 1">上一页</button>
      <span>{{ page }}</span>
      <button @click="page++; load()" :disabled="page >= totalPages">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { favoriteApi, getHouseholdId } from '../services/api';
import { toast } from '../composables/useToast';
import type { FavoriteItem } from '../types';

const router = useRouter();
const items = ref<FavoriteItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 30;
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));

function formatTime(t: string) {
  return new Date(t).toLocaleString();
}

async function load() {
  const householdId = getHouseholdId();
  if (!householdId) return;
  try {
    const res = await favoriteApi.list({ household_id: householdId, page: page.value, page_size: pageSize });
    items.value = res.data;
    total.value = res.total;
  } catch (e) {
    console.error('load favorites failed', e);
  }
}

async function remove(item: FavoriteItem) {
  const householdId = getHouseholdId();
  if (!householdId) return;
  try {
    await favoriteApi.remove(item.recipe_id, householdId);
    toast('已取消收藏');
    load();
  } catch (e) {
    console.error('remove favorite failed', e);
  }
}

function goDetail(id: string) {
  router.push(`/recipes/${id}`);
}

onMounted(load);
</script>

<style scoped>
.favorites { padding: 20px; }
.header h1 { margin: 0 0 16px 0; }
.list { background: white; border-radius: 12px; overflow: hidden; }
.list-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 16px; border-bottom: 1px solid #f0f0f0;
}
.row-main { cursor: pointer; flex: 1; display: flex; flex-direction: column; gap: 4px; }
.row-title { font-weight: 500; color: #333; }
.row-time { font-size: 12px; color: #999; }

.btn-small { padding: 8px 14px; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; min-height: 36px; }
.btn-cancel { background: #f8d7da; color: #721c24; }
.empty-state { text-align: center; padding: 60px 20px; color: #888; }
.pagination { display: flex; justify-content: center; align-items: center; gap: 20px; margin-top: 20px; }
.pagination button { min-height: 44px; padding: 8px 16px; border: 1px solid #ddd; border-radius: 6px; background: white; cursor: pointer; }

@media (max-width: 767px) {
  .favorites { padding: 16px; }
  .header h1 { text-align: center; }
  .list-row { flex-direction: column; gap: 8px; align-items: stretch; }
  .btn-small { width: 100%; }
}
</style>
