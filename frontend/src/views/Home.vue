<template>
  <div class="home">
    <div class="hero">
      <h1>🍳 AI 家庭厨房助手</h1>
      <p class="subtitle">让每一餐都美味可口</p>
      <form class="search-box" @submit.prevent="search">
        <input v-model="keyword" type="text" placeholder="搜索菜谱 / 拼音 / 食材..." />
        <button type="submit" class="btn btn-primary">搜索</button>
      </form>
    </div>

    <!-- 今日推荐 -->
    <section class="section" v-if="today.length">
      <div class="section-head">
        <h2>🔥 今日推荐</h2>
        <router-link to="/discover" class="more-link">更多 ›</router-link>
      </div>
      <div class="card-grid">
        <RecipeCard
          v-for="recipe in today"
          :key="recipe.id"
          :recipe="recipe"
          @favorite="toggleFavorite"
          @menu="openAddMenu"
        />
      </div>
    </section>

    <!-- 最近添加 -->
    <section class="section" v-if="latest.length">
      <div class="section-head">
        <h2>🆕 最近添加</h2>
        <router-link to="/recipes" class="more-link">全部 ›</router-link>
      </div>
      <div class="card-grid">
        <RecipeCard
          v-for="recipe in latest"
          :key="recipe.id"
          :recipe="recipe"
          @favorite="toggleFavorite"
          @menu="openAddMenu"
        />
      </div>
    </section>

    <!-- 快捷入口 -->
    <section class="section">
      <div class="features">
        <router-link to="/recipes" class="feature-card"><div class="feature-icon">📚</div><h3>菜谱库</h3><p>筛选和管理菜谱</p></router-link>
        <router-link to="/menu" class="feature-card"><div class="feature-icon">📅</div><h3>菜单</h3><p>安排每日菜谱</p></router-link>
        <router-link to="/discover" class="feature-card"><div class="feature-icon">✨</div><h3>发现</h3><p>推荐与灵感</p></router-link>
        <router-link to="/inventory" class="feature-card"><div class="feature-icon">🥬</div><h3>库存</h3><p>追踪食材保质期</p></router-link>
      </div>
    </section>

    <AddToMenuModal ref="menuModal" :recipe-id="activeMenuRecipeId" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import RecipeCard from '../components/RecipeCard.vue';
import AddToMenuModal from '../components/AddToMenuModal.vue';
import { discoverApi, favoriteApi, getHouseholdId } from '../services/api';
import { toast } from '../composables/useToast';
import type { DiscoverRecipe, Recipe } from '../types';

const router = useRouter();
const keyword = ref('');
const today = ref<DiscoverRecipe[]>([]);
const latest = ref<DiscoverRecipe[]>([]);
const menuModal = ref();
const activeMenuRecipeId = ref('');

function search() {
  const q = keyword.value.trim();
  router.push(q ? { path: '/recipes', query: { q } } : '/recipes');
}

async function loadRecommendations() {
  const householdId = getHouseholdId();
  try {
    const [t, n] = await Promise.all([
      discoverApi.get({ type: 'today', household_id: householdId, limit: 4 }),
      discoverApi.get({ type: 'new', household_id: householdId, limit: 4 })
    ]);
    today.value = t.list;
    latest.value = n.list;
  } catch (e) {
    console.error('load home recs failed', e);
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
    } else {
      await favoriteApi.add(recipe.id, householdId);
      recipe.is_favorited = true;
    }
  } catch (e) {
    console.error('favorite failed', e);
  }
}

function openAddMenu(recipe: Recipe | DiscoverRecipe) {
  activeMenuRecipeId.value = recipe.id;
  menuModal.value?.open();
}

onMounted(loadRecommendations);
</script>

<style scoped>
.home { text-align: center; padding: 24px 20px; }

.hero { padding: 20px 0 28px; }
.hero h1 { font-size: 2rem; margin-bottom: 8px; color: #333; }
.subtitle { font-size: 1.1rem; color: #666; margin-bottom: 24px; }
.search-box { display: flex; gap: 10px; max-width: 520px; margin: 0 auto; }
.search-box input {
  flex: 1; padding: 12px 16px; border: 1px solid #ddd; border-radius: 24px;
  font-size: 16px; min-height: 48px; box-sizing: border-box;
}
.btn { padding: 12px 24px; border: none; border-radius: 24px; cursor: pointer; font-size: 15px; min-height: 48px; }
.btn-primary { background: #4a90d9; color: white; }

.section { margin-bottom: 32px; text-align: left; }
.section-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.section-head h2 { margin: 0; font-size: 1.15rem; }
.more-link { color: #4a90d9; text-decoration: none; font-size: 14px; }

.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }

.features { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
.feature-card {
  background: white; border-radius: 12px; padding: 24px 16px; text-decoration: none; color: inherit;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08); transition: transform 0.2s;
}
.feature-card:hover { transform: translateY(-4px); }
.feature-icon { font-size: 2.2rem; margin-bottom: 10px; }
.feature-card h3 { margin: 0 0 6px 0; font-size: 1rem; }
.feature-card p { margin: 0; color: #888; font-size: 0.85rem; }

@media (max-width: 767px) {
  .home { padding: 16px; }
  .hero h1 { font-size: 1.6rem; }
  .subtitle { font-size: 1rem; margin-bottom: 16px; }
  .search-box { flex-direction: column; gap: 8px; }
  .search-box .btn { width: 100%; }
  .card-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .features { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .feature-card { padding: 16px 12px; }
}
</style>
