<template>
  <div class="recipes">
    <!-- 右下角悬浮添加按钮 -->
    <button @click="goCreate" class="fab" aria-label="添加菜谱">+</button>

    <!-- 顶部搜索 -->
    <div class="top-bar">
      <input
        v-model="searchInput"
        type="text"
        placeholder="搜索菜谱 / 拼音 / 食材..."
        class="search-input"
        @input="debouncedSearch"
      />
      <button @click="clearFilters" class="btn clear-btn">清除筛选</button>
    </div>

    <!-- 筛选面板 -->
    <div class="filters">
      <div class="filter-row">
        <button @click="openIngredientModal" class="btn btn-secondary">食材筛选</button>
        <div class="match-mode-switch">
          <div :class="['match-mode-option', match === 'exact' ? 'active' : '']" @click="setMatch('exact')">精确</div>
          <div :class="['match-mode-option', match === 'any' ? 'active' : '']" @click="setMatch('any')">模糊</div>
        </div>
        <span class="filter-count">共 {{ total }} 个菜谱</span>
        <span v-if="selectedIngredients.length" class="filter-count">已选{{ selectedIngredients.length }}食材</span>
      </div>

      <div class="filter-row">
        <select v-model="sort" @change="loadRecipes" class="filter-select">
          <option value="score">综合推荐</option>
          <option value="date">最新添加</option>
          <option value="cook">做过次数</option>
          <option value="random">随机推荐</option>
          <option value="title">名称排序</option>
        </select>
        <select v-model="categoryId" @change="loadRecipes" class="filter-select">
          <option value="">全部分类</option>
          <option v-for="c in recipeCategories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <select v-model="status" @change="loadRecipes" class="filter-select">
          <option value="">全部状态</option>
          <option value="draft">草稿</option>
          <option value="published">已发布</option>
          <option value="archived">已归档</option>
        </select>
      </div>

      <!-- 已选食材 chips -->
      <div v-if="selectedIngredients.length" class="chosen-ingredients">
        <span v-for="ing in selectedIngredients" :key="ing.id" class="chosen-chip">
          {{ ing.name }}
          <button class="chip-remove" @click="removeIngredient(ing.id)">×</button>
        </span>
      </div>

    </div>

    <!-- 菜谱列表 -->
    <div class="recipe-grid" v-if="recipes.length > 0">
      <RecipeCard
        v-for="recipe in recipes"
        :key="recipe.id"
        :recipe="recipe"
        @favorite="toggleFavorite"
        @menu="openAddMenu"
      />
    </div>
    <div v-else class="empty-state">
      <p>📭 暂无菜谱</p>
      <button @click="goCreate" class="btn btn-primary">添加第一个菜谱</button>
    </div>

    <!-- 分页 -->
    <div class="pagination" v-if="total > pageSize">
      <button @click="prevPage" :disabled="page === 1">上一页</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button @click="nextPage" :disabled="page === totalPages">下一页</button>
    </div>

    <!-- 食材筛选弹窗 -->
    <div v-if="showIngModal" class="modal-overlay" @click.self="showIngModal = false">
      <div class="modal">
        <h3>食材筛选</h3>
        <input v-model="ingSearch" type="text" placeholder="搜索食材" class="modal-search" />
        <select v-model="ingCategoryFilter" class="modal-select">
          <option value="">全部分类</option>
          <option v-for="c in ingCategories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <div class="ing-list">
          <span
            v-for="ing in filteredIngredients"
            :key="ing.id"
            :class="['item-modal', isSelected(ing.id) ? 'selected' : '']"
            @click="toggleIngredient(ing)"
          >
            {{ ing.canonical_name }}
          </span>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showIngModal = false">完成</button>
        </div>
      </div>
    </div>

    <!-- 加入菜单弹窗 -->
    <AddToMenuModal ref="menuModal" :recipe-id="activeMenuRecipeId" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import RecipeCard from '../components/RecipeCard.vue';
import AddToMenuModal from '../components/AddToMenuModal.vue';
import { recipeApi, categoryApi, ingredientApi, favoriteApi, getHouseholdId } from '../services/api';
import { toast } from '../composables/useToast';
import type { Recipe, Category, Ingredient } from '../types';

const router = useRouter();
const route = useRoute();

const recipes = ref<Recipe[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;

const searchInput = ref('');
const status = ref('');
const sort = ref('score');
const match = ref<'exact' | 'any'>('exact');
const categoryId = ref('');
const selectedIngredients = ref<{ id: string; name: string }[]>([]);

const recipeCategories = ref<Category[]>([]);
const ingCategories = ref<Category[]>([]);
const allIngredients = ref<Ingredient[]>([]);

const showIngModal = ref(false);
const ingSearch = ref('');
const ingCategoryFilter = ref('');

const menuModal = ref();
const activeMenuRecipeId = ref('');

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));
const filteredIngredients = computed(() => {
  return allIngredients.value.filter(ing => {
    if (ingCategoryFilter.value && ing.category_id !== ingCategoryFilter.value) return false;
    if (ingSearch.value && !ing.canonical_name.includes(ingSearch.value)) return false;
    return true;
  });
});

let searchTimeout: ReturnType<typeof setTimeout>;
function debouncedSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    page.value = 1;
    loadRecipes();
  }, 400);
}

function setMatch(m: 'exact' | 'any') {
  match.value = m;
  loadRecipes();
}

function isSelected(id: string) {
  return selectedIngredients.value.some(i => i.id === id);
}

function toggleIngredient(ing: Ingredient) {
  const idx = selectedIngredients.value.findIndex(i => i.id === ing.id);
  if (idx >= 0) selectedIngredients.value.splice(idx, 1);
  else selectedIngredients.value.push({ id: ing.id, name: ing.canonical_name });
  loadRecipes();
}

function removeIngredient(id: string) {
  selectedIngredients.value = selectedIngredients.value.filter(i => i.id !== id);
  loadRecipes();
}

function openIngredientModal() {
  showIngModal.value = true;
  ingSearch.value = '';
  ingCategoryFilter.value = '';
}

function clearFilters() {
  searchInput.value = '';
  status.value = '';
  sort.value = 'score';
  match.value = 'exact';
  categoryId.value = '';
  selectedIngredients.value = [];
  page.value = 1;
  loadRecipes();
}

async function loadRecipes() {
  try {
    const response = await recipeApi.list({
      query: searchInput.value || undefined,
      status: status.value || undefined,
      sort: sort.value,
      category_id: categoryId.value || undefined,
      ingredients: selectedIngredients.value.map(i => i.id).join(',') || undefined,
      match: selectedIngredients.value.length ? match.value : undefined,
      household_id: getHouseholdId(),
      page: page.value,
      page_size: pageSize
    });
    recipes.value = response.data;
    total.value = response.total;
  } catch (error) {
    console.error('Failed to load recipes:', error);
  }
}

async function toggleFavorite(recipe: Recipe | import('../types').DiscoverRecipe) {
  const householdId = getHouseholdId();
  if (!householdId) {
    toast('请先创建/选择家庭（库存管理页）', 'error');
    return;
  }
  try {
    if (recipe.is_favorited) {
      await favoriteApi.remove(recipe.id, householdId);
      recipe.is_favorited = false;
      toast('已取消收藏');
    } else {
      await favoriteApi.add(recipe.id, householdId);
      recipe.is_favorited = true;
      toast('已收藏');
    }
  } catch (e) {
    console.error('favorite failed', e);
  }
}

function openAddMenu(recipe: Recipe | import('../types').DiscoverRecipe) {
  activeMenuRecipeId.value = recipe.id;
  menuModal.value?.open();
}

function viewRecipe(id: string) {
  router.push(`/recipes/${id}`);
}

function goCreate() {
  router.push('/recipes/new');
}

function prevPage() {
  if (page.value > 1) { page.value--; loadRecipes(); }
}
function nextPage() {
  if (page.value < totalPages.value) { page.value++; loadRecipes(); }
}

onMounted(async () => {
  // 从首页搜索跳转时带上关键词
  const q = route.query.q as string | undefined;
  if (q) {
    searchInput.value = q;
  }
  loadRecipes();
  try {
    const [rc, ic, ings] = await Promise.all([
      categoryApi.list('recipe'),
      categoryApi.list('ingredient'),
      ingredientApi.list({ page: 1, page_size: 100 })
    ]);
    recipeCategories.value = rc.data;
    ingCategories.value = ic.data;
    allIngredients.value = ings.data;
  } catch (e) {
    console.error('Failed to load filters:', e);
  }
});
</script>

<style scoped>
.recipes { padding: 20px; }
.top-bar { display: flex; gap: 10px; margin-bottom: 12px; }

/* 右下角悬浮添加按钮 */
.fab {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: #4a90d9;
  color: white;
  border: none;
  font-size: 30px;
  line-height: 1;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
}
.fab:hover { background: #3a80c9; }
.fab:active { transform: scale(0.95); }
.search-input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 16px; min-height: 44px; }

.filters {
  background: white;
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.filter-row { display: flex; gap: 10px; align-items: center; margin-bottom: 8px; flex-wrap: wrap; }
.filter-select { padding: 8px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }

.match-mode-switch { display: flex; border: 1px solid #ddd; border-radius: 6px; overflow: hidden; }
.match-mode-option { padding: 8px 16px; cursor: pointer; font-size: 13px; }
.match-mode-option.active { background: #4a90d9; color: white; }

.filter-count { font-size: 13px; color: #888; }
.chosen-ingredients { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
.chosen-chip {
  background: #e3f2fd; color: #1976d2; padding: 4px 10px; border-radius: 14px; font-size: 12px;
  display: inline-flex; align-items: center; gap: 6px;
}
.chip-remove { border: none; background: none; color: #1976d2; cursor: pointer; font-size: 14px; padding: 0; }

.recipe-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }

.empty-state { text-align: center; padding: 60px 20px; color: #888; }
.empty-state p { font-size: 1.2rem; margin-bottom: 20px; }

.pagination { display: flex; justify-content: center; align-items: center; gap: 20px; margin-top: 20px; }
.pagination button { min-height: 44px; padding: 8px 16px; border: 1px solid #ddd; border-radius: 6px; background: white; cursor: pointer; }
.pagination button:disabled { opacity: 0.5; cursor: not-allowed; }

.btn { padding: 10px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; min-height: 44px; }
.btn-primary { background: #4a90d9; color: white; }
.btn-secondary { background: #f0f0f0; color: #333; }
.clear-btn { background: #4a90d9; color: white; flex-shrink: 0; white-space: nowrap; }

/* 食材弹窗 */
.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 16px;
}
.modal { background: white; border-radius: 12px; padding: 24px; width: 100%; max-width: 480px; max-height: 80vh; display: flex; flex-direction: column; }
.modal h3 { margin: 0 0 12px 0; }
.modal-search, .modal-select { padding: 10px; border: 1px solid #ddd; border-radius: 6px; min-height: 44px; margin-bottom: 10px; width: 100%; box-sizing: border-box; }
.ing-list { display: flex; flex-wrap: wrap; gap: 8px; overflow-y: auto; flex: 1; padding: 4px; }
.item-modal {
  padding: 8px 14px; border: 1px solid #ddd; border-radius: 16px; cursor: pointer; font-size: 14px;
}
.item-modal.selected { background: #4a90d9; color: white; border-color: #4a90d9; }
.modal-actions { display: flex; justify-content: flex-end; margin-top: 16px; }

@media (max-width: 767px) {
  .recipes { padding: 16px; }
  .fab { right: 16px; bottom: 80px; width: 52px; height: 52px; font-size: 28px; }
  .top-bar { flex-direction: row; align-items: center; }
  .clear-btn { padding: 10px 12px; }
  .filter-row { gap: 8px; }
  .filter-select { flex: 1; min-width: 0; }
  .recipe-grid { grid-template-columns: 1fr; gap: 10px; }
  .modal-overlay { padding: 0; align-items: flex-end; }
  .modal { border-radius: 12px 12px 0 0; max-height: 90vh; }
}
</style>
