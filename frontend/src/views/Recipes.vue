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
        <select v-model="sort" @change="scheduleLoad()" class="filter-select">
          <option value="score">综合推荐</option>
          <option value="date">最新添加</option>
          <option value="cook">做过次数</option>
          <option value="random">随机推荐</option>
          <option value="title">名称排序</option>
        </select>
        <select v-model="categoryId" @change="scheduleLoad()" class="filter-select">
          <option value="">全部分类</option>
          <option v-for="c in recipeCategories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <select v-model="status" @change="scheduleLoad()" class="filter-select">
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
    <div v-if="loading && !recipes.length" class="loading-state">
      <span class="spinner" aria-hidden="true"></span>
      <p>加载中...</p>
    </div>
    <div v-else-if="loadError && !recipes.length" class="empty-state">
      <p>加载失败</p>
      <button class="btn btn-primary" @click="loadRecipes">点击重试</button>
    </div>
    <template v-else-if="recipes.length > 0">
      <div class="recipe-grid">
        <RecipeCard
          v-for="recipe in recipes"
          :key="recipe.id"
          :recipe="recipe"
          @favorite="toggleFavorite"
          @menu="openAddMenu"
        />
      </div>
    </template>
    <div v-else class="empty-state">
      <p>📭 暂无菜谱</p>
      <button @click="goCreate" class="btn btn-primary">添加第一个菜谱</button>
    </div>

    <LoadMoreFooter
      :show="total > pageSize"
      :loading="loadingMore"
      :error="loadError"
      :finished="!hasMore && total > pageSize"
      @retry="loadMore"
    />

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
import { ref, computed, onMounted, onActivated, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import RecipeCard from '../components/RecipeCard.vue';
import AddToMenuModal from '../components/AddToMenuModal.vue';
import { recipeApi, categoryApi, ingredientApi, favoriteApi } from '../services/api';
import { useAppStore } from '../stores/app';
import { toast } from '../composables/useToast';
import { usePageSize } from '../composables/usePageSize';
import { useInfiniteList } from '../composables/useInfiniteList';
import LoadMoreFooter from '../components/LoadMoreFooter.vue';
import type { Recipe, Category, Ingredient } from '../types';

defineOptions({ name: 'Recipes' }); // 供 KeepAlive include 精确匹配

const router = useRouter();
const route = useRoute();
const appStore = useAppStore();

// 已展示列表对应的数据版本：返回页面时若 recipeVersion 未变则跳过刷新
let loadedVersion = -1;

const searchInput = ref('');
const status = ref('');
const sort = ref('score');
const match = ref<'exact' | 'any'>('exact');
const categoryId = ref('');
const selectedIngredients = ref<{ id: string; name: string }[]>([]);

const { pageSize, ready: pageSizeReady } = usePageSize();
const {
  items: recipes,
  total,
  loading,
  loadingMore,
  loadError,
  hasMore,
  reset: loadRecipes,
  loadMore
} = useInfiniteList<Recipe>({
  fetcher: (page, pageSize) =>
    recipeApi.list({
      query: searchInput.value || undefined,
      status: status.value || undefined,
      sort: sort.value,
      category_id: categoryId.value || undefined,
      ingredients: selectedIngredients.value.map(i => i.id).join(',') || undefined,
      match: selectedIngredients.value.length ? match.value : undefined,
      page,
      page_size: pageSize
    }),
  getPageSize: () => pageSize.value,
  dedupeKey: (r) => r.id
});

const recipeCategories = ref<Category[]>([]);
const ingCategories = ref<Category[]>([]);
const allIngredients = ref<Ingredient[]>([]);

const showIngModal = ref(false);
const ingSearch = ref('');
const ingCategoryFilter = ref('');

const menuModal = ref();
const activeMenuRecipeId = ref('');

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
    loadRecipes();
  }, 400);
}

// 筛选类变更统一走防抖，减少菜谱刷新频率（分类/排序/状态/食材）
let reloadTimer: ReturnType<typeof setTimeout>;
function scheduleLoad(delay = 300) {
  clearTimeout(reloadTimer);
  reloadTimer = setTimeout(loadRecipes, delay);
}

function setMatch(m: 'exact' | 'any') {
  match.value = m;
  scheduleLoad();
}

function isSelected(id: string) {
  return selectedIngredients.value.some(i => i.id === id);
}

function toggleIngredient(ing: Ingredient) {
  const idx = selectedIngredients.value.findIndex(i => i.id === ing.id);
  if (idx >= 0) selectedIngredients.value.splice(idx, 1);
  else selectedIngredients.value.push({ id: ing.id, name: ing.canonical_name });
  scheduleLoad();
}

function removeIngredient(id: string) {
  selectedIngredients.value = selectedIngredients.value.filter(i => i.id !== id);
  scheduleLoad();
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
  loadRecipes();
}

async function toggleFavorite(recipe: Recipe | import('../types').DiscoverRecipe) {
  try {
    if (recipe.is_favorited) {
      await favoriteApi.remove(recipe.id);
      recipe.is_favorited = false;
      toast('已取消收藏');
    } else {
      await favoriteApi.add(recipe.id);
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

onMounted(async () => {
  // 从首页搜索跳转时带上关键词
  const q = route.query.q as string | undefined;
  if (q) {
    searchInput.value = q;
  }
  loadedVersion = appStore.recipeVersion;
  console.log(`[recipeVersion] 菜谱库首次挂载，记录 loadedVersion=${loadedVersion}，加载列表`);
  await pageSizeReady;
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

// 组件被 KeepAlive 缓存，从详情页返回时重新激活：
// 数据未变（recipeVersion 相同）则不刷新，保留筛选与列表；菜谱有增删改才重新拉取
onActivated(async () => {
  if (loadedVersion !== appStore.recipeVersion) {
    console.log(`[recipeVersion] 菜谱库重新激活：loadedVersion=${loadedVersion} ≠ recipeVersion=${appStore.recipeVersion}，重新拉取`);
    loadedVersion = appStore.recipeVersion;
    await pageSizeReady;
    loadRecipes();
  } else {
    console.log(`[recipeVersion] 菜谱库重新激活：版本未变（${loadedVersion}），跳过刷新`);
  }
});

// 缓存期间从首页搜索跳转（/recipes?q=xxx）时更新关键词并刷新
watch(() => route.query.q, async (q) => {
  searchInput.value = (q as string) || '';
  console.log(`[recipeVersion] 路由参数 q 变化触发刷新，keyword="${searchInput.value}"`);
  await pageSizeReady;
  loadRecipes();
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

.loading-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; padding: 60px 20px; color: #888;
}
.spinner {
  width: 32px; height: 32px; border: 3px solid #e0e0e0; border-top-color: #4a90d9;
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

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
