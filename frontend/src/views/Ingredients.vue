<template>
  <div class="ingredients">
    <div class="header">
      <div class="header-left">
        <button @click="goBack" class="btn-back" aria-label="返回">返回</button>
        <h1>食材管理</h1>
      </div>
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
        <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
      </select>
    </div>

    <div v-if="loading && !ingredients.length" class="empty-state">
      <span class="spinner" aria-hidden="true"></span>
      <p>加载中...</p>
    </div>
    <div v-else-if="loadError && !ingredients.length" class="empty-state">
      <p>加载失败</p>
      <button class="btn btn-primary" @click="loadIngredients">点击重试</button>
    </div>
    <div class="ingredient-list" v-else-if="ingredients.length > 0">
      <div v-for="ing in ingredients" :key="ing.id" class="ingredient-card">
        <div class="card-main" @click="editIngredient(ing)">
          <div class="ingredient-header">
            <div class="ingredient-title">
              <h3>{{ ing.canonical_name }}</h3>
              <span class="category-badge">{{ ing.category_name || '未分类' }}</span>
            </div>
            <div class="ingredient-actions">
              <button @click.stop="openAliasEditor(ing)" class="btn btn-small btn-primary">编辑别名</button>
              <button @click.stop="deleteIngredient(ing.id)" class="btn btn-small btn-danger">删除</button>
            </div>
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
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>📭 暂无食材</p>
      <button @click="showCreateModal = true" class="btn btn-primary">添加第一个食材</button>
    </div>

    <LoadMoreFooter
      :show="total > pageSize"
      :loading="loadingMore"
      :error="loadError"
      :finished="!hasMore && total > pageSize"
      @retry="loadMore"
    />

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
            <AppSelect
              v-model="ingredientForm.category_id"
              :options="categoryOptions"
              placeholder="请选择"
              search-placeholder="搜索分类..."
            />
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

    <!-- 编辑别名弹窗 -->
    <div v-if="showAliasModal" class="modal-overlay" @click.self="showAliasModal = false">
      <div class="modal">
        <h2>编辑别名 - {{ aliasIngredient?.canonical_name }}</h2>
        <div class="alias-list" v-if="aliasIngredient?.aliases?.length">
          <div v-for="a in aliasIngredient.aliases" :key="a.id" class="alias-item">
            <span>{{ a.alias }}</span>
            <button @click="removeAlias(a)" class="btn-small btn-danger">删除</button>
          </div>
        </div>
        <p v-else class="empty-alias">暂无别名</p>
        <form @submit.prevent="addAlias">
          <div class="form-group">
            <label>新增别名</label>
            <input v-model="aliasName" type="text" placeholder="输入新别名" />
          </div>
          <div class="modal-actions">
            <button type="button" @click="showAliasModal = false" class="btn btn-secondary">关闭</button>
            <button type="submit" class="btn btn-primary" :disabled="!aliasName.trim()">添加</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useGoBack } from '../composables/useGoBack';
import { ingredientApi, categoryApi } from '../services/api';
import { toast } from '../composables/useToast';
import { usePageSize } from '../composables/usePageSize';
import { useInfiniteList } from '../composables/useInfiniteList';
import LoadMoreFooter from '../components/LoadMoreFooter.vue';
import AppSelect from '../components/AppSelect.vue';
import type { Ingredient, IngredientAlias, Category } from '../types';

const { goBack } = useGoBack('/me');

const searchQuery = ref('');
const categoryFilter = ref('');

const { pageSize, ready: pageSizeReady } = usePageSize();
const {
  items: ingredients,
  total,
  loading,
  loadingMore,
  loadError,
  hasMore,
  reset: loadIngredients,
  loadMore
} = useInfiniteList<Ingredient>({
  fetcher: (page, pageSize) => ingredientApi.list({
    query: searchQuery.value || undefined,
    category_id: categoryFilter.value || undefined,
    page,
    page_size: pageSize
  }),
  getPageSize: () => pageSize.value
});
const showCreateModal = ref(false);
const showAliasModal = ref(false);
const editingIngredient = ref<Ingredient | null>(null);
const aliasIngredient = ref<Ingredient | null>(null);
const aliasName = ref('');

const seasonInput = ref('');
const allergenInput = ref('');

const categories = ref<Category[]>([]);

// 分类下拉选项，首项“请选择”用于清空分类
const categoryOptions = computed(() => [
  { value: '', label: '请选择' },
  ...categories.value.map(c => ({ value: c.id, label: c.name }))
]);

const ingredientForm = ref({
  canonical_name: '',
  category_id: ''
});

let searchTimeout: ReturnType<typeof setTimeout>;

function debouncedSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    loadIngredients();
  }, 300);
}

async function loadCategories() {
  try {
    const res = await categoryApi.list('ingredient');
    categories.value = res.data;
  } catch (error) {
    console.error('Failed to load categories:', error);
  }
}

function editIngredient(ing: Ingredient) {
  editingIngredient.value = ing;
  ingredientForm.value = {
    canonical_name: ing.canonical_name,
    category_id: ing.category_id || ''
  };
  seasonInput.value = ing.season_months ? ing.season_months.join(',') : '';
  allergenInput.value = ing.allergens ? ing.allergens.join(',') : '';
  showCreateModal.value = true;
}

function openAliasEditor(ing: Ingredient) {
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
        category_id: ingredientForm.value.category_id || undefined,
        season_months,
        allergens
      });
    } else {
      await ingredientApi.create({
        canonical_name: ingredientForm.value.canonical_name,
        category_id: ingredientForm.value.category_id || undefined
      });
    }
    closeCreateModal();
    loadIngredients();
  } catch (error) {
    console.error('Failed to save ingredient:', error);
  }
}

async function addAlias() {
  if (!aliasIngredient.value || !aliasName.value.trim()) return;
  try {
    await ingredientApi.addAlias(aliasIngredient.value.id, aliasName.value.trim());
    toast('别名已添加');
    aliasName.value = '';
    await loadIngredients();
    refreshAliasIngredient();
  } catch (error: any) {
    toast(error?.response?.data?.detail || '添加别名失败', 'error');
  }
}

async function removeAlias(alias: IngredientAlias) {
  if (!aliasIngredient.value) return;
  if (!confirm(`确定删除别名「${alias.alias}」吗？`)) return;
  try {
    await ingredientApi.removeAlias(alias.id);
    toast('别名已删除');
    await loadIngredients();
    refreshAliasIngredient();
  } catch (error: any) {
    toast(error?.response?.data?.detail || '删除别名失败', 'error');
  }
}

function refreshAliasIngredient() {
  aliasIngredient.value = ingredients.value.find(i => i.id === aliasIngredient.value?.id) ?? null;
}

async function deleteIngredient(id: string) {
  if (!confirm('确定要删除这个食材吗？')) return;
  try {
    await ingredientApi.delete(id);
    toast('已删除');
    loadIngredients();
  } catch (error: any) {
    toast(error?.response?.data?.detail || '删除失败', 'error');
  }
}

function closeCreateModal() {
  showCreateModal.value = false;
  editingIngredient.value = null;
  ingredientForm.value = {
    canonical_name: '',
    category_id: ''
  };
  seasonInput.value = '';
  allergenInput.value = '';
}

onMounted(() => {
  pageSizeReady.then(loadIngredients);
  loadCategories();
});
</script>

<style scoped>
.ingredients {
  padding: 0 20px 20px;
}

.header {
  position: sticky;
  top: var(--navbar-height, 64px);
  z-index: 150;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 16px 0;
  margin-bottom: 20px;
  background: #f5f5f5;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

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

.btn-back:hover {
  background: rgba(7, 132, 255, 0.08);
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

.card-main {
  cursor: pointer;
}

.card-main:active {
  opacity: 0.75;
}

.ingredient-header {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.ingredient-title {
  display: flex;
  flex-direction: row;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
}

.ingredient-title h3 {
  margin: 0;
  color: #333;
  line-height: 1.3;
}

.category-badge {
  background: #f0f0f0;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  color: #666;
  line-height: 1;
  display: inline-flex;
  align-items: center;
}

.ingredient-details {
  margin-bottom: 0;
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

.alias-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.alias-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f5f5f5;
  border-radius: 6px;
}

.alias-item span {
  font-size: 14px;
  color: #333;
}

.alias-item .btn-small {
  flex-shrink: 0;
}

.empty-alias {
  color: #888;
  font-size: 14px;
  text-align: center;
  padding: 12px 0;
  margin-bottom: 16px;
}

.ingredient-actions {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-shrink: 0;
  margin-left: auto;
}

.ingredient-actions .btn-small {
  white-space: nowrap;
  padding: 5px 14px;
  min-height: 30px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #888;
}

.empty-state p {
  margin: 0 0 16px;
}

.spinner {
  display: inline-block;
  width: 32px; height: 32px;
  border: 3px solid #e0e0e0; border-top-color: #4a90d9;
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

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
  padding: 16px;
}

.modal {
  background: white;
  border-radius: 12px;
  padding: 30px;
  width: 100%;
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
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  box-sizing: border-box;
  min-height: 44px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

/* 移动端响应式样式 */
@media (max-width: 767px) {
  .ingredients {
    padding: 0 16px 16px;
  }

  .header {
    flex-direction: row;
    gap: 10px;
    align-items: center;
    padding: 14px 0;
  }

  .header h1 {
    font-size: 1.5rem;
    margin: 0;
    text-align: center;
  }

  .header-left {
    justify-content: center;
    position: relative;
    flex: 1;
    min-width: 0;
  }

  .btn-back {
    position: absolute;
    left: 0;
  }

  .header .btn {
    flex-shrink: 0;
    width: auto;
  }

  .filters {
    flex-direction: row;
    gap: 8px;
    align-items: center;
  }

  .filters input {
    flex: 1;
    min-width: 0;
    min-height: 44px;
  }

  .filters select {
    width: auto;
    min-height: 44px;
    flex-shrink: 0;
  }

  .ingredient-card {
    padding: 12px;
  }

  .ingredient-header {
    gap: 8px;
  }

  .ingredient-title {
    gap: 6px;
  }

  .ingredient-title h3 {
    font-size: 1.1rem;
  }

  .ingredient-actions {
    gap: 6px;
  }

  .ingredient-actions .btn-small {
    padding: 4px 10px;
    font-size: 11px;
    min-height: 28px;
  }

  /* 移动端模态框 */
  .modal-overlay {
    padding: 0;
    align-items: flex-end;
  }

  .modal {
    border-radius: 12px 12px 0 0;
    max-height: 95vh;
    padding: 24px 16px;
  }

  .modal-actions {
    flex-direction: column;
    gap: 8px;
  }

  .modal-actions .btn {
    width: 100%;
  }
}

/* 平板端响应式样式 */
@media (min-width: 768px) and (max-width: 1023px) {
  .ingredient-actions {
    gap: 6px;
  }

  .ingredient-actions .btn-small {
    padding: 6px 10px;
    font-size: 11px;
  }
}
</style>
