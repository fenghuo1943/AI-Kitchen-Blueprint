<template>
  <div class="recipe-management">
    <div class="header">
      <h1>📖 菜谱管理</h1>
      <button @click="goCreate" class="btn btn-primary">新建菜谱</button>
    </div>

    <div class="filters">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索菜谱 / 拼音 / 食材..."
        @input="debouncedSearch"
      />
      <select v-model="statusFilter" @change="loadRecipes">
        <option value="">全部状态</option>
        <option value="draft">草稿</option>
        <option value="published">已发布</option>
        <option value="archived">已归档</option>
      </select>
    </div>

    <div v-if="loading && !recipes.length" class="loading-state">
      <span class="spinner" aria-hidden="true"></span>
      <p>加载中...</p>
    </div>

    <div v-else-if="recipes.length > 0" class="recipe-list">
      <div v-for="recipe in recipes" :key="recipe.id" class="recipe-row">
        <div class="row-cover" v-if="recipe.cover">
          <img :src="recipe.cover" :alt="recipe.title" />
        </div>
        <div class="row-main">
          <div class="row-title-line">
            <span class="row-title" @click="viewRecipe(recipe.id)">{{ recipe.title }}</span>
            <span :class="['status-badge', recipe.status]">{{ statusLabel(recipe.status) }}</span>
          </div>
          <div class="row-meta">
            <span v-if="recipe.categories.length">📁 {{ recipe.categories.map(c => c.name).join(' / ') }}</span>
            <span v-if="recipe.prep_minutes || recipe.cook_minutes">
              ⏱️ {{ (recipe.prep_minutes || 0) + (recipe.cook_minutes || 0) }}分钟
            </span>
            <span v-if="recipe.difficulty">📊 {{ recipe.difficulty }}</span>
          </div>
          <div class="row-meta">
            <span>🕐 更新于 {{ formatTime(recipe.updated_at) }}</span>
          </div>
        </div>
        <div class="row-actions">
          <button class="btn-small btn-secondary" @click="viewRecipe(recipe.id)">查看</button>
          <button class="btn-small btn-confirm" @click="editRecipe(recipe.id)">编辑</button>
          <button class="btn-small btn-danger" @click="deleteRecipe(recipe.id, recipe.title)">删除</button>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>📭 暂无菜谱</p>
      <button @click="goCreate" class="btn btn-primary">新建菜谱</button>
    </div>

    <div class="pagination" v-if="total > pageSize">
      <button @click="prevPage" :disabled="page === 1">上一页</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button @click="nextPage" :disabled="page >= totalPages">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated } from 'vue';
import { useRouter } from 'vue-router';
import { recipeApi } from '../services/api';
import { useAppStore } from '../stores/app';
import { toast } from '../composables/useToast';
import type { Recipe } from '../types';

defineOptions({ name: 'RecipeManagement' });

const router = useRouter();
const appStore = useAppStore();

const recipes = ref<Recipe[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const searchQuery = ref('');
const statusFilter = ref('');
const loading = ref(false);

let loadSeq = 0; // 请求序号，用于忽略过期的慢响应

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  published: '已发布',
  archived: '已归档'
};

function statusLabel(status: string) {
  return STATUS_LABELS[status] || status;
}

function formatTime(t: string) {
  return new Date(t).toLocaleString();
}

let searchTimeout: ReturnType<typeof setTimeout>;
function debouncedSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    page.value = 1;
    loadRecipes();
  }, 300);
}

async function loadRecipes() {
  const seq = ++loadSeq;
  loading.value = true;
  try {
    const response = await recipeApi.list({
      query: searchQuery.value || undefined,
      status: statusFilter.value || undefined,
      sort: 'date',
      page: page.value,
      page_size: pageSize
    });
    if (seq !== loadSeq) return; // 忽略过期响应
    recipes.value = response.data;
    total.value = response.total;
  } catch (error) {
    if (seq === loadSeq) console.error('Failed to load recipes:', error);
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

function viewRecipe(id: string) {
  router.push(`/recipes/${id}`);
}

function editRecipe(id: string) {
  router.push(`/recipes/${id}/edit`);
}

function goCreate() {
  router.push('/recipes/new');
}

async function deleteRecipe(id: string, title: string) {
  if (!window.confirm(`确定将「${title}」删除吗？删除后可在回收站恢复。`)) return;
  try {
    await recipeApi.delete(id);
    appStore.bumpRecipeVersion('delete'); // 通知缓存的菜谱库列表需要刷新
    toast('已删除，可在回收站找回');
    loadRecipes();
  } catch (error: any) {
    toast(error?.response?.data?.detail || '删除失败', 'error');
  }
}

function prevPage() {
  if (page.value > 1) {
    page.value--;
    loadRecipes();
  }
}

function nextPage() {
  if (page.value < totalPages.value) {
    page.value++;
    loadRecipes();
  }
}

onMounted(loadRecipes);

// 从编辑/详情页返回时刷新（若菜谱有变化）
onActivated(() => {
  loadRecipes();
});
</script>

<style scoped>
.recipe-management {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h1 {
  margin: 0;
  font-size: 1.5rem;
  color: #333;
}

.filters {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.filters input,
.filters select {
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.filters input {
  flex: 1;
}

.recipe-list {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.recipe-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.recipe-row:last-child {
  border-bottom: none;
}

.row-cover {
  width: 64px;
  height: 64px;
  border-radius: 8px;
  overflow: hidden;
  background: #f0f0f0;
  flex-shrink: 0;
}

.row-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.row-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.row-title-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.row-title {
  font-weight: 500;
  color: #333;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row-title:hover {
  color: #4a90d9;
}

.status-badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  flex-shrink: 0;
}

.status-badge.draft {
  background: #fff3cd;
  color: #856404;
}

.status-badge.published {
  background: #d4edda;
  color: #155724;
}

.status-badge.archived {
  background: #e2e3e5;
  color: #383d41;
}

.row-meta {
  font-size: 12px;
  color: #999;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.row-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px 20px;
  color: #888;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e0e0e0;
  border-top-color: #4a90d9;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #888;
}

.empty-state p {
  font-size: 1.2rem;
  margin-bottom: 20px;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  margin-top: 20px;
}

.pagination button {
  min-height: 44px;
  padding: 8px 16px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  cursor: pointer;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-small {
  padding: 8px 12px;
  font-size: 12px;
  min-height: 36px;
}

.btn-primary {
  background: #4a90d9;
  color: white;
}

.btn-primary:hover {
  background: #357abd;
}

.btn-secondary {
  background: #e0e0e0;
  color: #333;
}

.btn-secondary:hover {
  background: #d0d0d0;
}

.btn-confirm {
  background: #4a90d9;
  color: white;
}

.btn-danger {
  background: #f44336;
  color: white;
}

/* 移动端响应式样式 */
@media (max-width: 767px) {
  .recipe-management {
    padding: 16px;
  }

  .header {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }

  .header h1 {
    font-size: 1.5rem;
    margin: 0;
    text-align: center;
  }

  .header .btn {
    width: 100%;
  }

  .filters {
    flex-direction: column;
    gap: 8px;
  }

  .filters input,
  .filters select {
    width: 100%;
    min-height: 44px;
  }

  .recipe-row {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .row-cover {
    display: none;
  }

  .row-actions {
    width: 100%;
  }

  .row-actions .btn-small {
    flex: 1;
  }

  .pagination {
    gap: 12px;
  }

  .pagination button {
    min-height: 44px;
    padding: 8px 16px;
  }
}
</style>
