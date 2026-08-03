<template>
  <div class="recipes">
    <div class="header">
      <h1>📚 菜谱库</h1>
      <button @click="showCreateModal = true" class="btn btn-primary">添加菜谱</button>
    </div>

    <div class="filters">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索菜谱..."
        @input="debouncedSearch"
      />
      <select v-model="statusFilter" @change="loadRecipes">
        <option value="">全部状态</option>
        <option value="draft">草稿</option>
        <option value="published">已发布</option>
        <option value="archived">已归档</option>
      </select>
    </div>

    <div class="recipe-list" v-if="recipes.length > 0">
      <div v-for="recipe in recipes" :key="recipe.id" class="recipe-card" @click="viewRecipe(recipe.id)">
        <div class="recipe-header">
          <h3>{{ recipe.title }}</h3>
          <span :class="['status-badge', recipe.status]">{{ recipe.status }}</span>
        </div>
        <p class="recipe-summary">{{ recipe.summary || '暂无简介' }}</p>
        <div class="recipe-meta">
          <span v-if="recipe.servings">👥 {{ recipe.servings }}人份</span>
          <span v-if="recipe.total_minutes">⏱️ {{ (recipe.prep_minutes || 0) + (recipe.cook_minutes || 0) }}分钟</span>
          <span v-if="recipe.difficulty">📊 {{ recipe.difficulty }}</span>
        </div>
        <div class="recipe-tags">
          <span v-for="tag in recipe.tags.slice(0, 3)" :key="tag.id" class="tag">{{ tag.name }}</span>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>📭 暂无菜谱</p>
      <button @click="showCreateModal = true" class="btn btn-primary">添加第一个菜谱</button>
    </div>

    <div class="pagination" v-if="total > pageSize">
      <button @click="prevPage" :disabled="page === 1">上一页</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button @click="nextPage" :disabled="page === totalPages">下一页</button>
    </div>

    <!-- 创建菜谱弹窗 -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal">
        <h2>添加新菜谱</h2>
        <form @submit.prevent="createRecipe">
          <div class="form-group">
            <label>菜谱名称 *</label>
            <input v-model="newRecipe.title" type="text" required />
          </div>
          <div class="form-group">
            <label>简介</label>
            <textarea v-model="newRecipe.summary"></textarea>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>份量</label>
              <input v-model.number="newRecipe.servings" type="number" min="1" />
            </div>
            <div class="form-group">
              <label>准备时间(分钟)</label>
              <input v-model.number="newRecipe.prep_minutes" type="number" min="0" />
            </div>
            <div class="form-group">
              <label>烹饪时间(分钟)</label>
              <input v-model.number="newRecipe.cook_minutes" type="number" min="0" />
            </div>
          </div>
          <div class="form-group">
            <label>难度</label>
            <select v-model="newRecipe.difficulty">
              <option value="">请选择</option>
              <option value="简单">简单</option>
              <option value="中等">中等</option>
              <option value="困难">困难</option>
            </select>
          </div>
          <div class="modal-actions">
            <button type="button" @click="showCreateModal = false" class="btn btn-secondary">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="!newRecipe.title">创建</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { recipeApi } from '../services/api';
import type { Recipe } from '../types';

const router = useRouter();

const recipes = ref<Recipe[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const searchQuery = ref('');
const statusFilter = ref('');
const showCreateModal = ref(false);

const newRecipe = ref({
  title: '',
  summary: '',
  servings: undefined as number | undefined,
  prep_minutes: undefined as number | undefined,
  cook_minutes: undefined as number | undefined,
  difficulty: ''
});

const totalPages = computed(() => Math.ceil(total.value / pageSize));

let searchTimeout: ReturnType<typeof setTimeout>;

function debouncedSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    page.value = 1;
    loadRecipes();
  }, 300);
}

async function loadRecipes() {
  try {
    const response = await recipeApi.list({
      query: searchQuery.value || undefined,
      status: statusFilter.value || undefined,
      page: page.value,
      page_size: pageSize
    });
    recipes.value = response.data;
    total.value = response.total;
  } catch (error) {
    console.error('Failed to load recipes:', error);
  }
}

function viewRecipe(id: string) {
  router.push(`/recipes/${id}`);
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

async function createRecipe() {
  try {
    await recipeApi.create(newRecipe.value);
    showCreateModal.value = false;
    newRecipe.value = {
      title: '',
      summary: '',
      servings: undefined,
      prep_minutes: undefined,
      cook_minutes: undefined,
      difficulty: ''
    };
    loadRecipes();
  } catch (error) {
    console.error('Failed to create recipe:', error);
  }
}

onMounted(() => {
  loadRecipes();
});
</script>

<style scoped>
.recipes {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
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
  display: grid;
  gap: 16px;
}

.recipe-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.recipe-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.recipe-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.recipe-header h3 {
  margin: 0;
  color: #333;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
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

.recipe-summary {
  color: #666;
  margin: 0 0 10px 0;
  font-size: 14px;
}

.recipe-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #888;
  margin-bottom: 10px;
}

.recipe-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tag {
  background: #f0f0f0;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  color: #666;
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

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
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

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 12px;
  padding: 30px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal h2 {
  margin: 0 0 20px 0;
  color: #333;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  color: #555;
}

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group textarea {
  min-height: 80px;
  resize: vertical;
}

.form-row {
  display: flex;
  gap: 12px;
}

.form-row .form-group {
  flex: 1;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
</style>
