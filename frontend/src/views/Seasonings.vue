<template>
  <div class="seasonings">
    <div class="header">
      <h1>🧂 调料管理</h1>
      <router-link to="/categories" class="btn btn-secondary">分类管理</router-link>
    </div>

    <div class="search-row">
      <input v-model="query" type="text" placeholder="搜索调料 / 拼音" @input="debouncedSearch" />
    </div>

    <div class="add-row">
      <input v-model="newName" type="text" placeholder="输入调料名称" />
      <select v-model="newCategoryId">
        <option value="">默认分类</option>
        <option v-for="c in seaCategories" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
      <button class="btn btn-primary" @click="create" :disabled="!newName.trim()">添加</button>
    </div>

    <div class="list">
      <div v-for="s in seasonings" :key="s.id" class="list-row">
        <div class="row-main">
          <span class="row-title">{{ s.canonical_name }}</span>
          <span class="row-sub">{{ s.category_name || '默认分类' }} · {{ s.pinyin }}</span>
        </div>
        <button class="btn-small btn-danger" @click="remove(s)">删除</button>
      </div>
    </div>
    <div v-if="!seasonings.length" class="empty-state">暂无调料</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { seasoningApi, categoryApi } from '../services/api';
import { toast } from '../composables/useToast';
import type { Seasoning, Category } from '../types';

const seasonings = ref<Seasoning[]>([]);
const seaCategories = ref<Category[]>([]);
const query = ref('');
const newName = ref('');
const newCategoryId = ref('');

let timer: ReturnType<typeof setTimeout>;
function debouncedSearch() {
  clearTimeout(timer);
  timer = setTimeout(load, 400);
}

async function load() {
  try {
    const res = await seasoningApi.list({ query: query.value || undefined, page: 1, page_size: 100 });
    seasonings.value = res.data;
  } catch (e) {
    console.error('load seasonings failed', e);
  }
}

async function loadCategories() {
  try {
    const res = await categoryApi.list('seasoning');
    seaCategories.value = res.data;
  } catch (e) {
    console.error('load sea categories failed', e);
  }
}

async function create() {
  const name = newName.value.trim();
  if (!name) return;
  try {
    await seasoningApi.create({ canonical_name: name, category_id: newCategoryId.value || undefined });
    toast('已添加');
    newName.value = '';
    load();
  } catch (e: any) {
    toast(e?.response?.data?.detail || '添加失败', 'error');
  }
}

async function remove(s: Seasoning) {
  if (!window.confirm(`确定删除调料「${s.canonical_name}」？`)) return;
  try {
    await seasoningApi.delete(s.id);
    toast('已删除');
    load();
  } catch (e: any) {
    toast(e?.response?.data?.detail || '删除失败', 'error');
  }
}

onMounted(() => { load(); loadCategories(); });
</script>

<style scoped>
.seasonings { padding: 20px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.header h1 { margin: 0; }
.search-row, .add-row { display: flex; gap: 10px; margin-bottom: 12px; }
.search-row input, .add-row input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 6px; min-height: 44px; font-size: 16px; }
.add-row select { padding: 10px; border: 1px solid #ddd; border-radius: 6px; min-height: 44px; }

.list { background: white; border-radius: 12px; overflow: hidden; }
.list-row { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; border-bottom: 1px solid #f0f0f0; }
.row-main { display: flex; flex-direction: column; gap: 2px; }
.row-title { font-weight: 500; }
.row-sub { font-size: 12px; color: #999; }

.btn { padding: 10px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; min-height: 44px; text-decoration: none; display: inline-flex; align-items: center; }
.btn-primary { background: #4a90d9; color: white; }
.btn-primary:disabled { background: #ccc; cursor: not-allowed; }
.btn-secondary { background: #f0f0f0; color: #333; }
.btn-small { padding: 8px 12px; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; min-height: 36px; }
.btn-danger { background: #f44336; color: white; }
.empty-state { text-align: center; padding: 40px 20px; color: #888; }

@media (max-width: 767px) {
  .seasonings { padding: 16px; }
  .header h1 { text-align: center; }
  .add-row { flex-wrap: wrap; }
  .add-row input { flex-basis: 100%; }
  .add-row select { flex: 1; }
}
</style>
