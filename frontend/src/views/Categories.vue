<template>
  <div class="categories">
    <div class="header">
      <h1>📁 分类管理</h1>
    </div>

    <div class="type-tabs">
      <button
        v-for="t in tabs"
        :key="t.value"
        :class="['tab-btn', activeType === t.value ? 'active' : '']"
        @click="activeType = t.value; load()"
      >{{ t.label }}</button>
    </div>

    <div class="add-row">
      <input v-model="newName" type="text" placeholder="输入分类名称" @keyup.enter="create" />
      <button class="btn btn-primary" @click="create" :disabled="!newName.trim()">添加</button>
    </div>

    <div class="list">
      <div v-for="c in categories" :key="c.id" class="list-row">
        <span class="row-title">{{ c.name }}</span>
        <div class="row-actions">
          <button class="btn-small btn-secondary" @click="startRename(c)">重命名</button>
          <button class="btn-small btn-danger" @click="remove(c)">删除</button>
        </div>
      </div>
    </div>
    <div v-if="!categories.length" class="empty-state">暂无分类</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { categoryApi } from '../services/api';
import { toast } from '../composables/useToast';
import type { Category, CategoryType } from '../types';

const tabs = [
  { label: '菜谱分类', value: 'recipe' as CategoryType },
  { label: '食材分类', value: 'ingredient' as CategoryType },
  { label: '调料分类', value: 'seasoning' as CategoryType }
];
const activeType = ref<CategoryType>('recipe');
const categories = ref<Category[]>([]);
const newName = ref('');

async function load() {
  try {
    const res = await categoryApi.list(activeType.value);
    categories.value = res.data;
  } catch (e) {
    console.error('load categories failed', e);
  }
}

async function create() {
  const name = newName.value.trim();
  if (!name) return;
  try {
    await categoryApi.create(activeType.value, { name });
    toast('已添加');
    newName.value = '';
    load();
  } catch (e: any) {
    toast(e?.response?.data?.detail || '添加失败', 'error');
  }
}

function startRename(c: Category) {
  const name = window.prompt('新的分类名称：', c.name);
  if (!name || name === c.name) return;
  categoryApi.update(activeType.value, c.id, { name })
    .then(() => { toast('已重命名'); load(); })
    .catch((e: any) => toast(e?.response?.data?.detail || '重命名失败', 'error'));
}

async function remove(c: Category) {
  if (!window.confirm(`确定删除分类「${c.name}」？`)) return;
  try {
    await categoryApi.delete(activeType.value, c.id);
    toast('已删除');
    load();
  } catch (e: any) {
    toast(e?.response?.data?.detail || '删除失败', 'error');
  }
}

onMounted(load);
</script>

<style scoped>
.categories { padding: 20px; }
.header h1 { margin: 0 0 16px 0; }
.type-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.tab-btn { padding: 10px 16px; border: 1px solid #ddd; border-radius: 8px; background: white; cursor: pointer; font-size: 14px; min-height: 44px; }
.tab-btn.active { background: #4a90d9; color: white; border-color: #4a90d9; }

.add-row { display: flex; gap: 10px; margin-bottom: 16px; }
.add-row input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 6px; min-height: 44px; font-size: 16px; }

.list { background: white; border-radius: 12px; overflow: hidden; }
.list-row { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; border-bottom: 1px solid #f0f0f0; }
.row-title { font-weight: 500; }
.row-actions { display: flex; gap: 8px; }

.btn { padding: 10px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; min-height: 44px; }
.btn-primary { background: #4a90d9; color: white; }
.btn-primary:disabled { background: #ccc; cursor: not-allowed; }
.btn-small { padding: 8px 12px; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; min-height: 36px; }
.btn-secondary { background: #f0f0f0; color: #333; }
.btn-danger { background: #f44336; color: white; }
.empty-state { text-align: center; padding: 40px 20px; color: #888; }

@media (max-width: 767px) {
  .categories { padding: 16px; }
  .header h1 { text-align: center; }
  .type-tabs { width: 100%; }
  .tab-btn { flex: 1; }
  .list-row { flex-direction: column; gap: 8px; align-items: stretch; }
  .row-actions { width: 100%; }
  .row-actions .btn-small { flex: 1; }
}
</style>
