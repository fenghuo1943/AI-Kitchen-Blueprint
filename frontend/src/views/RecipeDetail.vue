<template>
  <div class="recipe-detail" v-if="recipe">
    <div class="header">
      <button @click="$router.back()" class="btn btn-secondary">← 返回</button>
      <div class="actions">
        <button @click="toggleFavorite" :class="['btn', recipe.is_favorited ? 'btn-cancel' : 'btn-primary']">
          {{ recipe.is_favorited ? '♥ 已收藏' : '♡ 收藏' }}
        </button>
        <button @click="openAddMenu" class="btn btn-secondary">📅 加入菜单</button>
        <button v-if="recipe.status === 'draft'" @click="publishRecipe" class="btn btn-primary">发布</button>
        <button @click="goEdit" class="btn btn-secondary">✏️ 编辑</button>
        <button @click="deleteRecipe" class="btn btn-danger">🗑 删除</button>
      </div>
    </div>

    <div class="recipe-content">
      <h1>{{ recipe.title }}</h1>
      <p class="summary">{{ recipe.summary }}</p>

      <div class="meta">
        <span v-if="recipe.servings">👥 {{ recipe.servings }}人份</span>
        <span v-if="recipe.prep_minutes">⏱️ 准备 {{ recipe.prep_minutes }}分钟</span>
        <span v-if="recipe.cook_minutes">🔥 烹饪 {{ recipe.cook_minutes }}分钟</span>
        <span v-if="recipe.difficulty">📊 {{ recipe.difficulty }}</span>
        <span :class="['status-badge', recipe.status]">{{ recipe.status }}</span>
      </div>

      <div class="tags" v-if="recipe.tags.length > 0">
        <span v-for="tag in recipe.tags" :key="tag.id" class="tag">{{ tag.name }}</span>
      </div>

      <div class="categories" v-if="recipe.categories.length > 0">
        <span v-for="cat in recipe.categories" :key="cat.id" class="tag category-tag">📁 {{ cat.name }}</span>
      </div>

      <section class="section">
        <h2>🥬 食材清单</h2>
        <ul class="ingredient-list">
          <li v-for="ing in recipe.ingredients" :key="ing.id">
            <span class="ingredient-name">{{ ing.ingredient_name }}</span>
            <span class="ingredient-quantity">{{ ing.quantity }} {{ ing.unit }}</span>
            <span v-if="ing.preparation" class="ingredient-prep">({{ ing.preparation }})</span>
            <span v-if="ing.optional" class="optional-badge">可选</span>
          </li>
        </ul>
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
import { recipeApi, recommendationApi, favoriteApi, getHouseholdId } from '../services/api';
import { toast } from '../composables/useToast';
import type { Recipe } from '../types';

const route = useRoute();
const router = useRouter();

const recipe = ref<Recipe | null>(null);
const coverageInput = ref('');
const coverageResult = ref<any>(null);
const menuModal = ref();

async function loadRecipe() {
  try {
    const id = route.params.id as string;
    recipe.value = await recipeApi.get(id, getHouseholdId());
  } catch (error) {
    console.error('Failed to load recipe:', error);
  }
}

async function publishRecipe() {
  if (!recipe.value) return;
  try {
    await recipeApi.publish(recipe.value.id);
    toast('已发布');
    loadRecipe();
  } catch (error) {
    console.error('Failed to publish recipe:', error);
  }
}

async function toggleFavorite() {
  if (!recipe.value) return;
  const householdId = getHouseholdId();
  if (!householdId) {
    toast('请先创建/选择家庭（库存管理页）', 'error');
    return;
  }
  try {
    if (recipe.value.is_favorited) {
      await favoriteApi.remove(recipe.value.id, householdId);
      recipe.value.is_favorited = false;
      toast('已取消收藏');
    } else {
      await favoriteApi.add(recipe.value.id, householdId);
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

async function deleteRecipe() {
  if (!recipe.value) return;
  if (!window.confirm('确定删除该菜谱？将移入回收站，可恢复。')) return;
  try {
    await recipeApi.delete(recipe.value.id);
    toast('已移入回收站');
    router.push('/recipes');
  } catch (error) {
    console.error('Failed to delete recipe:', error);
  }
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
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.actions {
  display: flex;
  gap: 10px;
}

.recipe-content h1 {
  margin: 0 0 10px 0;
  color: #333;
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
  list-style: none;
  padding: 0;
  margin: 0;
}

.ingredient-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 8px;
  margin-bottom: 8px;
}

.ingredient-name {
  font-weight: 500;
  color: #333;
}

.ingredient-quantity {
  color: #666;
}

.ingredient-prep {
  color: #888;
  font-size: 13px;
}

.optional-badge {
  background: #e3f2fd;
  color: #1976d2;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
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

.btn-cancel {
  background: #f8d7da;
  color: #721c24;
}

.btn-danger {
  background: #f44336;
  color: white;
}

.btn-danger:hover {
  background: #d32f2f;
}

/* 移动端响应式样式 */
@media (max-width: 767px) {
  .recipe-detail {
    padding: 16px;
  }

  .header {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }

  .header .btn {
    width: 100%;
  }

  .actions {
    justify-content: stretch;
  }

  .actions .btn {
    flex: 1;
  }

  .recipe-content h1 {
    font-size: 1.5rem;
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

  .ingredient-list li {
    flex-wrap: wrap;
    gap: 8px;
    padding: 12px;
  }

  .ingredient-name {
    font-size: 0.95rem;
  }

  .ingredient-quantity {
    font-size: 0.9rem;
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
