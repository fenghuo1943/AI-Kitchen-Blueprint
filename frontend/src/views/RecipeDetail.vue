<template>
  <div class="recipe-detail" v-if="recipe">
    <div class="header">
      <div class="header-left">
        <button @click="$router.back()" class="btn-back" aria-label="返回">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path d="M19 12H6" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
            <path d="M12 19L5 12L12 5" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
          </svg>
        </button>
        <h1 class="header-title">{{ recipe.title }}</h1>
      </div>
      <div class="actions">
        <button
          @click="toggleFavorite"
          class="btn-fav"
          :class="{ favorited: recipe.is_favorited }"
          aria-label="收藏"
        >
          <svg viewBox="0 0 24 24" class="heart-icon">
            <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
          </svg>
        </button>
        <button v-if="recipe.status === 'draft'" @click="publishRecipe" class="btn btn-primary">发布</button>
        <button @click="goEdit" class="btn btn-secondary btn-sm">✏️ 编辑</button>
      </div>
    </div>

    <!-- 加入菜单悬浮按钮 -->
    <button @click="openAddMenu" class="btn-fab">加入菜单</button>

    <div class="recipe-content">
      <p class="summary">{{ recipe.summary }}</p>

      <div class="meta">
        <span v-if="recipe.servings">👥 {{ recipe.servings }}人份</span>
        <span v-if="recipe.prep_minutes">⏱️ 准备 {{ recipe.prep_minutes }}分钟</span>
        <span v-if="recipe.cook_minutes">🔥 烹饪 {{ recipe.cook_minutes }}分钟</span>
        <span v-if="recipe.difficulty">📊 {{ recipe.difficulty }}</span>
      </div>

      <div class="tags" v-if="recipe.tags.length > 0">
        <span v-for="tag in recipe.tags" :key="tag.id" class="tag">{{ tag.name }}</span>
      </div>

      <div class="categories">
        <span :class="['status-badge', recipe.status]">{{ recipe.status }}</span>
        <template v-if="recipe.categories.length > 0">
          <span v-for="cat in recipe.categories" :key="cat.id" class="tag category-tag">📁 {{ cat.name }}</span>
        </template>
      </div>

      <section class="section">
        <h2>🥬 食材清单</h2>
        <div class="ingredient-list">
          <span v-for="ing in recipe.ingredients" :key="ing.id" class="ingredient-chip">
            {{ ing.ingredient_name }}
            <em v-if="ing.quantity">{{ ing.quantity }} {{ ing.unit }}</em>
            <em v-if="ing.preparation" class="prep">({{ ing.preparation }})</em>
            <em v-if="ing.optional" class="optional">可选</em>
          </span>
        </div>
      </section>

      <section class="section" v-if="recipe.seasonings.length > 0">
        <h2>🧂 调料</h2>
        <div class="seasoning-list">
          <span v-for="sea in recipe.seasonings" :key="sea.id" class="seasoning-chip">
            {{ sea.seasoning_name }} <em v-if="sea.quantity">{{ sea.quantity }}</em>
          </span>
        </div>
      </section>

      <section class="section">
        <h2>📝 烹饪步骤</h2>
        <ol class="step-list">
          <li v-for="step in recipe.steps" :key="step.id">
            <div class="step-content">
              <p>{{ step.instruction }}</p>
              <span v-if="step.duration_minutes" class="step-duration">⏱️ {{ step.duration_minutes }}分钟</span>
            </div>
          </li>
        </ol>
      </section>

      <!-- 加入菜单弹窗 -->
      <AddToMenuModal ref="menuModal" :recipe-id="recipe.id" />

      <div class="coverage-section">
        <h2>🥗 食材覆盖率</h2>
        <div class="coverage-input">
          <input
            v-model="coverageInput"
            placeholder="输入您现有的食材，用逗号分隔"
          />
          <button @click="calculateCoverage" class="btn btn-primary" :disabled="!coverageInput">计算</button>
        </div>
        <div v-if="coverageResult" class="coverage-result">
          <div class="coverage-score">
            <span class="score-value">{{ Math.round(coverageResult.coverage_score * 100) }}%</span>
            <span class="score-label">覆盖率</span>
          </div>
          <div v-if="coverageResult.matched_ingredients.length > 0" class="coverage-matched">
            <h4>✅ 已有食材</h4>
            <span v-for="ing in coverageResult.matched_ingredients" :key="ing" class="matched">{{ ing }}</span>
          </div>
          <div v-if="coverageResult.missing_ingredients.length > 0" class="coverage-missing">
            <h4>❌ 缺少食材</h4>
            <span v-for="ing in coverageResult.missing_ingredients" :key="ing" class="missing">{{ ing }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div v-else class="loading">
    <p>加载中...</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import AddToMenuModal from '../components/AddToMenuModal.vue';
import { recipeApi, recommendationApi, favoriteApi } from '../services/api';
import { useAppStore } from '../stores/app';
import { toast } from '../composables/useToast';
import type { Recipe } from '../types';

const route = useRoute();
const router = useRouter();
const appStore = useAppStore();

const recipe = ref<Recipe | null>(null);
const coverageInput = ref('');
const coverageResult = ref<any>(null);
const menuModal = ref();

async function loadRecipe() {
  try {
    const id = route.params.id as string;
    recipe.value = await recipeApi.get(id);
  } catch (error) {
    console.error('Failed to load recipe:', error);
  }
}

async function publishRecipe() {
  if (!recipe.value) return;
  try {
    await recipeApi.publish(recipe.value.id);
    appStore.bumpRecipeVersion('publish'); // 状态变化，通知缓存的菜谱库列表需要刷新
    toast('已发布');
    loadRecipe();
  } catch (error) {
    console.error('Failed to publish recipe:', error);
  }
}

async function toggleFavorite() {
  if (!recipe.value) return;
  try {
    if (recipe.value.is_favorited) {
      await favoriteApi.remove(recipe.value.id);
      recipe.value.is_favorited = false;
      toast('已取消收藏');
    } else {
      await favoriteApi.add(recipe.value.id);
      recipe.value.is_favorited = true;
      toast('已收藏');
    }
  } catch (e) {
    console.error('favorite failed', e);
  }
}

function openAddMenu() {
  if (!recipe.value) return;
  menuModal.value?.open();
}

function goEdit() {
  if (!recipe.value) return;
  router.push(`/recipes/${recipe.value.id}/edit`);
}

async function calculateCoverage() {
  if (!recipe.value || !coverageInput.value) return;
  try {
    const ingredients = coverageInput.value.split(/[,，]/).map(s => s.trim()).filter(Boolean);
    coverageResult.value = await recommendationApi.calculateCoverage({
      recipe_id: recipe.value.id,
      available_ingredients: ingredients
    });
  } catch (error) {
    console.error('Failed to calculate coverage:', error);
  }
}

onMounted(() => {
  loadRecipe();
});
</script>

<style scoped>
.recipe-detail {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
  padding-bottom: 100px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.header-title {
  margin: 0;
  font-size: 1.3rem;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

/* 返回按钮：向左箭头，蓝色轮廓，透明背景，圆角矩形外形 */
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
  transition: background 0.2s;
}

.btn-back:hover {
  background: rgba(7, 132, 255, 0.08);
}

/* 收藏按钮：心形图案，已收藏为红色，未收藏为透明(空心) */
.btn-fav {
  width: 44px;
  height: 44px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 50%;
  cursor: pointer;
}

.heart-icon {
  width: 24px;
  height: 24px;
}

.heart-icon path {
  fill: transparent;
  stroke: #999;
  stroke-width: 1.8;
  transition: fill 0.2s, stroke 0.2s;
}

.btn-fav.favorited .heart-icon path {
  fill: #e53935;
  stroke: #e53935;
}

/* 加入菜单悬浮按钮：腰圆孔形状 */
.btn-fab {
  position: fixed;
  right: 24px;
  bottom: 80px;
  z-index: 100;
  min-height: 48px;
  padding: 14px 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #4a90d9;
  color: white;
  border: none;
  border-radius: 999px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.22);
  transition: background 0.2s, transform 0.2s;
}

.btn-fab:hover {
  background: #357abd;
  transform: translateY(-1px);
}

.recipe-content {
  margin-top: 4px;
}

.summary {
  color: #666;
  font-size: 1.1rem;
  margin-bottom: 20px;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 14px;
  color: #888;
  margin-bottom: 16px;
}

.tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.tag {
  background: #f0f0f0;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 13px;
  color: #666;
}

.categories {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 24px;
}

.category-tag {
  background: #e3f2fd;
  color: #1976d2;
}

.seasoning-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.seasoning-chip {
  background: #fff3cd;
  color: #856404;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 13px;
}

.seasoning-chip em {
  font-style: normal;
  color: #b78a00;
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

.section {
  margin-bottom: 30px;
}

.section h2 {
  font-size: 1.3rem;
  color: #333;
  margin-bottom: 16px;
}

.ingredient-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.ingredient-chip {
  background: #e8f0f7;
  color: #333;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 13px;
}

.ingredient-chip em {
  font-style: normal;
  color: #5a7d9c;
  margin-left: 2px;
}

.ingredient-chip em.prep {
  color: #888;
}

.ingredient-chip em.optional {
  background: #e3f2fd;
  color: #1976d2;
  padding: 1px 6px;
  border-radius: 10px;
  font-size: 11px;
  margin-left: 4px;
}

.step-list {
  padding-left: 24px;
  margin: 0;
}

.step-list li {
  margin-bottom: 16px;
}

.step-content {
  background: #f9f9f9;
  padding: 16px;
  border-radius: 8px;
}

.step-content p {
  margin: 0 0 8px 0;
  color: #333;
  line-height: 1.6;
}

.step-duration {
  font-size: 13px;
  color: #888;
}

.coverage-section {
  background: #f5f5f5;
  padding: 20px;
  border-radius: 12px;
  margin-top: 30px;
}

.coverage-section h2 {
  margin-top: 0;
}

.coverage-input {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.coverage-input input {
  flex: 1;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  min-height: 44px;
}

.coverage-result {
  background: white;
  padding: 16px;
  border-radius: 8px;
}

.coverage-score {
  text-align: center;
  margin-bottom: 16px;
}

.score-value {
  font-size: 2.5rem;
  font-weight: bold;
  color: #4a90d9;
}

.score-label {
  display: block;
  font-size: 14px;
  color: #888;
}

.coverage-matched,
.coverage-missing {
  margin-top: 16px;
}

.coverage-matched h4,
.coverage-missing h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #555;
}

.matched {
  display: inline-block;
  background: #d4edda;
  color: #155724;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  margin: 0 4px 4px 0;
}

.missing {
  display: inline-block;
  background: #f8d7da;
  color: #721c24;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  margin: 0 4px 4px 0;
}

.loading {
  text-align: center;
  padding: 60px;
  color: #888;
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

.btn-primary {
  background: #4a90d9;
  color: white;
}

.btn-primary:hover {
  background: #357abd;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-secondary {
  background: #e0e0e0;
  color: #333;
}

.btn-secondary:hover {
  background: #d0d0d0;
}

/* 小尺寸按钮：减小内边距 */
.btn-sm {
  padding: 4px 12px;
  min-height: 32px;
  font-size: 13px;
}

/* 移动端响应式样式 */
@media (max-width: 767px) {
  .recipe-detail {
    padding: 16px;
    padding-bottom: 104px;
  }

  .header {
    flex-direction: row;
    gap: 8px;
    align-items: center;
  }

  .actions {
    margin-left: auto;
  }

  .header-title {
    font-size: 1.1rem;
  }

  .summary {
    font-size: 1rem;
    margin-bottom: 16px;
  }

  .meta {
    gap: 12px;
    font-size: 13px;
  }

  .tags {
    gap: 6px;
    margin-bottom: 20px;
  }

  .tag {
    padding: 4px 10px;
    font-size: 12px;
  }

  .section {
    margin-bottom: 24px;
  }

  .section h2 {
    font-size: 1.1rem;
    margin-bottom: 12px;
  }

  .step-content {
    padding: 12px;
  }

  .step-content p {
    font-size: 0.95rem;
  }

  .coverage-section {
    padding: 16px;
    margin-top: 24px;
  }

  .coverage-input {
    flex-direction: column;
    gap: 8px;
  }

  .coverage-input input {
    width: 100%;
  }

  .coverage-input .btn {
    width: 100%;
  }

  .score-value {
    font-size: 2rem;
  }

  .matched,
  .missing {
    padding: 3px 6px;
    font-size: 11px;
  }

  .loading {
    padding: 40px 16px;
  }
}

/* 平板端响应式样式 */
@media (min-width: 768px) and (max-width: 1023px) {
  .recipe-detail {
    padding: 16px;
  }

  .meta {
    gap: 12px;
  }

  .section h2 {
    font-size: 1.2rem;
  }
}
</style>
