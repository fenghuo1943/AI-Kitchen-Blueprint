<template>
  <div class="categories">
    <div class="header">
      <div class="header-left">
        <button @click="goBack" class="btn-back" aria-label="返回">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path d="M19 12H6" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
            <path d="M12 19L5 12L12 5" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
          </svg>
        </button>
        <h1>📁 分类管理</h1>
      </div>
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
        <span class="row-title">
          {{ c.name }}
          <span v-if="isDefaultCategory(c)" class="tag-default">默认</span>
        </span>
        <div class="row-actions">
          <button
            v-if="!isDefaultCategory(c)"
            class="btn-small btn-secondary"
            @click="startRename(c)"
          >编辑</button>
          <button
            v-if="!isDefaultCategory(c)"
            class="btn-small btn-danger"
            @click="remove(c)"
          >删除</button>
        </div>
      </div>
    </div>
    <div v-if="!categories.length" class="empty-state">暂无分类</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useGoBack } from '../composables/useGoBack';
import { categoryApi } from '../services/api';
import { toast } from '../composables/useToast';
import type { Category, CategoryType } from '../types';

const { goBack } = useGoBack('/me');

const tabs = [
  { label: '菜谱分类', value: 'recipe' as CategoryType },
  { label: '食材分类', value: 'ingredient' as CategoryType },
  { label: '调料分类', value: 'seasoning' as CategoryType }
];
const activeType = ref<CategoryType>('recipe');
const categories = ref<Category[]>([]);
const newName = ref('');

// 与后端 category_repository 保持一致：默认分类按名称「默认」解析，回落 id '1'
const DEFAULT_CATEGORY_NAME = '默认';
const DEFAULT_CATEGORY_ID = '1';

function isDefaultCategory(c: Category): boolean {
  return c.name === DEFAULT_CATEGORY_NAME || c.id === DEFAULT_CATEGORY_ID;
}

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
.header { display: flex; align-items: center; margin-bottom: 16px; }
.header-left { display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1; }
.header h1 { margin: 0; }
.btn-back {
  width: 36px;
  height: 36px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid #0784ff;
  border-radius: 8px;
  cursor: pointer;
  flex-shrink: 0;
}
.btn-back:hover { background: rgba(7, 132, 255, 0.08); }
.type-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.tab-btn { padding: 10px 16px; border: 1px solid #ddd; border-radius: 8px; background: white; cursor: pointer; font-size: 14px; min-height: 44px; }
.tab-btn.active { background: #4a90d9; color: white; border-color: #4a90d9; }

.add-row { display: flex; gap: 10px; margin-bottom: 16px; }
.add-row input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 6px; min-height: 44px; font-size: 16px; }

.list { background: white; border-radius: 12px; overflow: hidden; }
.list-row { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; border-bottom: 1px solid #f0f0f0; }
.row-title { font-weight: 500; }
.tag-default {
  margin-left: 6px;
  padding: 1px 8px;
  font-size: 12px;
  line-height: 18px;
  color: #4a90d9;
  background: rgba(74, 144, 217, 0.1);
  border: 1px solid #4a90d9;
  border-radius: 10px;
}
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
  .header-left { justify-content: center; position: relative; width: 100%; }
  .btn-back { position: absolute; left: 0; }
  .type-tabs { width: 100%; }
  .tab-btn { flex: 1; }
  .list-row { flex-direction: row; justify-content: space-between; align-items: center; gap: 8px; }
  .row-title { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .row-actions { display: flex; gap: 6px; flex-shrink: 0; }
  .row-actions .btn-small { flex: none; padding: 6px 10px; font-size: 12px; min-height: 30px; }
}
</style>
