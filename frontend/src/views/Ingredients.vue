<template>
  <div class="ingredients">
    <div class="header">
      <h1>🧅 食材管理</h1>
      <button @click="showCreateModal = true" class="btn btn-primary">添加食材</button>
    </div>

    <div class="filters">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索食材..."
        @input="debouncedSearch"
      />
      <select v-model="categoryFilter" @change="loadIngredients">
        <option value="">全部分类</option>
        <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
      </select>
    </div>

    <div class="ingredient-list" v-if="ingredients.length > 0">
      <div v-for="ing in ingredients" :key="ing.id" class="ingredient-card">
        <div class="ingredient-header">
          <h3>{{ ing.canonical_name }}</h3>
          <span class="category-badge">{{ ing.category || '未分类' }}</span>
        </div>
        <div class="ingredient-details">
          <div v-if="ing.season_months && ing.season_months.length > 0" class="detail-item">
            <span class="label">应季月份:</span>
            <span>{{ ing.season_months.join(', ') }}月</span>
          </div>
          <div v-if="ing.allergens && ing.allergens.length > 0" class="detail-item">
            <span class="label">过敏原:</span>
            <span class="allergen">{{ ing.allergens.join(', ') }}</span>
          </div>
          <div v-if="ing.aliases.length > 0" class="detail-item">
            <span class="label">别名:</span>
            <span>{{ ing.aliases.map(a => a.alias).join(', ') }}</span>
          </div>
        </div>
        <div class="ingredient-actions">
          <button @click="editIngredient(ing)" class="btn btn-small">编辑</button>
          <button @click="showAddAlias(ing)" class="btn btn-small">添加别名</button>
          <button @click="deleteIngredient(ing.id)" class="btn btn-small btn-danger">删除</button>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>📭 暂无食材</p>
      <button @click="showCreateModal = true" class="btn btn-primary">添加第一个食材</button>
    </div>

    <div class="pagination" v-if="total > pageSize">
      <button @click="prevPage" :disabled="page === 1">上一页</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button @click="nextPage" :disabled="page === totalPages">下一页</button>
    </div>

    <!-- 创建/编辑食材弹窗 -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="closeCreateModal">
      <div class="modal">
        <h2>{{ editingIngredient ? '编辑食材' : '添加食材' }}</h2>
        <form @submit.prevent="saveIngredient">
          <div class="form-group">
            <label>标准名称 *</label>
            <input v-model="ingredientForm.canonical_name" type="text" required />
          </div>
          <div class="form-group">
            <label>分类</label>
            <select v-model="ingredientForm.category">
              <option value="">请选择</option>
              <option value="蔬菜">蔬菜</option>
              <option value="肉类">肉类</option>
              <option value="蛋类">蛋类</option>
              <option value="主食">主食</option>
              <option value="豆制品">豆制品</option>
              <option value="水产">水产</option>
              <option value="调料">调料</option>
            </select>
          </div>
          <div class="form-group">
            <label>应季月份 (1-12，逗号分隔)</label>
            <input v-model="seasonInput" type="text" placeholder="例: 5,6,7,8" />
          </div>
          <div class="form-group">
            <label>过敏原 (逗号分隔)</label>
            <input v-model="allergenInput" type="text" placeholder="例: gluten, dairy" />
          </div>
          <div class="modal-actions">
            <button type="button" @click="closeCreateModal" class="btn btn-secondary">取消</button>
            <button type="submit" class="btn btn-primary">{{ editingIngredient ? '保存' : '添加' }}</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 添加别名弹窗 -->
    <div v-if="showAliasModal" class="modal-overlay" @click.self="showAliasModal = false">
      <div class="modal">
        <h2>添加别名 - {{ aliasIngredient?.canonical_name }}</h2>
        <form @submit.prevent="addAlias">
          <div class="form-group">
            <label>别名 *</label>
            <input v-model="aliasName" type="text" required />
          </div>
          <div class="modal-actions">
            <button type="button" @click="showAliasModal = false" class="btn btn-secondary">取消</button>
            <button type="submit" class="btn btn-primary">添加</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { ingredientApi } from '../services/api';
import type { Ingredient } from '../types';

const ingredients = ref<Ingredient[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const searchQuery = ref('');
const categoryFilter = ref('');
const showCreateModal = ref(false);
const showAliasModal = ref(false);
const editingIngredient = ref<Ingredient | null>(null);
const aliasIngredient = ref<Ingredient | null>(null);
const aliasName = ref('');

const seasonInput = ref('');
const allergenInput = ref('');

const categories = ['蔬菜', '肉类', '蛋类', '主食', '豆制品', '水产', '调料'];

const ingredientForm = ref({
  canonical_name: '',
  category: ''
});

const totalPages = computed(() => Math.ceil(total.value / pageSize));

let searchTimeout: ReturnType<typeof setTimeout>;

function debouncedSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    page.value = 1;
    loadIngredients();
  }, 300);
}

async function loadIngredients() {
  try {
    const response = await ingredientApi.list({
      query: searchQuery.value || undefined,
      category: categoryFilter.value || undefined,
      page: page.value,
      page_size: pageSize
    });
    ingredients.value = response.data;
    total.value = response.total;
  } catch (error) {
    console.error('Failed to load ingredients:', error);
  }
}

function editIngredient(ing: Ingredient) {
  editingIngredient.value = ing;
  ingredientForm.value = {
    canonical_name: ing.canonical_name,
    category: ing.category || ''
  };
  seasonInput.value = ing.season_months ? ing.season_months.join(',') : '';
  allergenInput.value = ing.allergens ? ing.allergens.join(',') : '';
  showCreateModal.value = true;
}

function showAddAlias(ing: Ingredient) {
  aliasIngredient.value = ing;
  aliasName.value = '';
  showAliasModal.value = true;
}

async function saveIngredient() {
  try {
    const season_months = seasonInput.value
      ? seasonInput.value.split(',').map(s => s.trim()).filter(Boolean)
      : undefined;
    const allergens = allergenInput.value
      ? allergenInput.value.split(',').map(s => s.trim()).filter(Boolean)
      : undefined;

    if (editingIngredient.value) {
      await ingredientApi.update(editingIngredient.value.id, {
        canonical_name: ingredientForm.value.canonical_name,
        category: ingredientForm.value.category || undefined,
        season_months,
        allergens
      });
    } else {
      await ingredientApi.create({
        canonical_name: ingredientForm.value.canonical_name,
        category: ingredientForm.value.category || undefined
      });
    }
    closeCreateModal();
    loadIngredients();
  } catch (error) {
    console.error('Failed to save ingredient:', error);
  }
}

async function addAlias() {
  if (!aliasIngredient.value || !aliasName.value) return;
  try {
    // This would need a dedicated API endpoint
    console.log('Add alias:', aliasIngredient.value.id, aliasName.value);
    showAliasModal.value = false;
    loadIngredients();
  } catch (error) {
    console.error('Failed to add alias:', error);
  }
}

async function deleteIngredient(id: string) {
  if (!confirm('确定要删除这个食材吗？')) return;
  try {
    await ingredientApi.delete(id);
    loadIngredients();
  } catch (error) {
    console.error('Failed to delete ingredient:', error);
  }
}

function closeCreateModal() {
  showCreateModal.value = false;
  editingIngredient.value = null;
  ingredientForm.value = {
    canonical_name: '',
    category: ''
  };
  seasonInput.value = '';
  allergenInput.value = '';
}

function prevPage() {
  if (page.value > 1) {
    page.value--;
    loadIngredients();
  }
}

function nextPage() {
  if (page.value < totalPages.value) {
    page.value++;
    loadIngredients();
  }
}

onMounted(() => {
  loadIngredients();
});
</script>

<style scoped>
.ingredients {
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

.ingredient-list {
  display: grid;
  gap: 16px;
}

.ingredient-card {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.ingredient-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.ingredient-header h3 {
  margin: 0;
  color: #333;
}

.category-badge {
  background: #f0f0f0;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  color: #666;
}

.ingredient-details {
  margin-bottom: 12px;
}

.detail-item {
  font-size: 13px;
  color: #666;
  margin-bottom: 4px;
}

.detail-item .label {
  color: #888;
  margin-right: 8px;
}

.allergen {
  color: #dc3545;
  font-weight: 500;
}

.ingredient-actions {
  display: flex;
  gap: 8px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #888;
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

.btn-small {
  padding: 6px 12px;
  font-size: 12px;
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

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-danger:hover {
  background: #c82333;
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
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
</style>
