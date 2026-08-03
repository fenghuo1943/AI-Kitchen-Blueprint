<template>
  <div class="discover">
    <div class="header">
      <h1>✨ 发现</h1>
      <button class="btn btn-secondary" @click="loadAll">刷新</button>
    </div>

    <!-- 今日推荐 -->
    <section class="section">
      <div class="section-head">
        <h2>🔥 今日推荐</h2>
        <span class="section-hint">当天稳定，每天更新</span>
      </div>
      <div v-if="today.length" class="card-grid">
        <RecipeCard
          v-for="recipe in today"
          :key="recipe.id"
          :recipe="recipe"
          @favorite="toggleFavorite"
          @menu="openAddMenu"
        />
      </div>
      <div v-else class="empty-hint">暂无推荐</div>
    </section>

    <!-- 随机推荐 -->
    <section class="section">
      <div class="section-head">
        <h2>🎲 随机推荐</h2>
        <button class="btn btn-secondary btn-small" @click="loadRandom">换一批</button>
      </div>
      <div v-if="randomRecipes.length" class="card-grid">
        <RecipeCard
          v-for="recipe in randomRecipes"
          :key="recipe.id"
          :recipe="recipe"
          @favorite="toggleFavorite"
          @menu="openAddMenu"
        />
      </div>
    </section>

    <!-- 热门 -->
    <section class="section">
      <div class="section-head">
        <h2>🏆 热门</h2>
      </div>
      <div v-if="hot.length" class="card-grid">
        <RecipeCard
          v-for="recipe in hot"
          :key="recipe.id"
          :recipe="recipe"
          @favorite="toggleFavorite"
          @menu="openAddMenu"
        />
      </div>
      <div v-else class="empty-hint">暂无热门菜谱</div>
    </section>

    <!-- 最近添加 -->
    <section class="section">
      <div class="section-head">
        <h2>🆕 最近添加</h2>
      </div>
      <div v-if="latest.length" class="card-grid">
        <RecipeCard
          v-for="recipe in latest"
          :key="recipe.id"
          :recipe="recipe"
          @favorite="toggleFavorite"
          @menu="openAddMenu"
        />
      </div>
    </section>

    <AddToMenuModal ref="menuModal" :recipe-id="activeMenuRecipeId" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import RecipeCard from '../components/RecipeCard.vue';
import AddToMenuModal from '../components/AddToMenuModal.vue';
import { discoverApi, favoriteApi, getHouseholdId } from '../services/api';
import { toast } from '../composables/useToast';
import type { DiscoverRecipe, Recipe } from '../types';

const today = ref<DiscoverRecipe[]>([]);
const randomRecipes = ref<DiscoverRecipe[]>([]);
const hot = ref<DiscoverRecipe[]>([]);
const latest = ref<DiscoverRecipe[]>([]);

const menuModal = ref();
const activeMenuRecipeId = ref('');

async function loadAll() {
  const householdId = getHouseholdId();
  const params = { household_id: householdId, limit: 6 };
  try {
    const [t, r, h, n] = await Promise.all([
      discoverApi.get({ ...params, type: 'today' }),
      discoverApi.get({ ...params, type: 'random' }),
      discoverApi.get({ ...params, type: 'hot' }),
      discoverApi.get({ ...params, type: 'new' })
    ]);
    today.value = t.list;
    randomRecipes.value = r.list;
    hot.value = h.list;
    latest.value = n.list;
  } catch (e) {
    console.error('load discover failed', e);
  }
}

async function loadRandom() {
  const householdId = getHouseholdId();
  try {
    const res = await discoverApi.get({ type: 'random', household_id: householdId, limit: 6 });
    randomRecipes.value = res.list;
  } catch (e) {
    console.error('load random failed', e);
  }
}

async function toggleFavorite(recipe: Recipe | DiscoverRecipe) {
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

function openAddMenu(recipe: Recipe | DiscoverRecipe) {
  activeMenuRecipeId.value = recipe.id;
  menuModal.value?.open();
}

onMounted(loadAll);
</script>

<style scoped>
.discover { padding: 20px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.header h1 { margin: 0; }

.section { margin-bottom: 28px; }
.section-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.section-head h2 { margin: 0; font-size: 1.15rem; }
.section-hint { font-size: 12px; color: #999; }

.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }
.empty-hint { color: #999; padding: 20px; text-align: center; background: white; border-radius: 12px; }

.btn { padding: 10px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; min-height: 44px; }
.btn-secondary { background: #f0f0f0; color: #333; }
.btn-small { padding: 8px 14px; min-height: 36px; font-size: 13px; }

@media (max-width: 767px) {
  .discover { padding: 16px; }
  .card-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
}
</style>
