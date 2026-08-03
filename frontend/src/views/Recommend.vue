<template>
  <div class="recommend">
    <h1>✨ 智能推荐</h1>
    <p class="subtitle">根据您现有的食材，为您推荐合适的菜谱</p>

    <div class="recommend-form">
      <div class="form-section">
        <h2>🥘 您的食材</h2>
        <div class="ingredient-input">
          <input
            v-model="ingredientInput"
            placeholder="输入食材名称，按回车添加"
            @keydown.enter.prevent="addIngredient"
          />
          <button @click="addIngredient" class="btn btn-secondary">添加</button>
        </div>
        <div class="selected-ingredients" v-if="selectedIngredients.length > 0">
          <span
            v-for="(ing, index) in selectedIngredients"
            :key="index"
            class="ingredient-tag"
          >
            {{ ing }}
            <button @click="removeIngredient(index)" class="remove-btn">×</button>
          </span>
        </div>
      </div>

      <div class="form-section">
        <h2>⚙️ 筛选条件</h2>
        <div class="form-row">
          <div class="form-group">
            <label>当前季节</label>
            <select v-model="filters.season_month">
              <option value="">不限</option>
              <option v-for="m in 12" :key="m" :value="String(m)">{{ m }}月</option>
            </select>
          </div>
          <div class="form-group">
            <label>最大烹饪时间(分钟)</label>
            <input v-model.number="filters.max_minutes" type="number" min="1" placeholder="不限" />
          </div>
          <div class="form-group">
            <label>用餐人数</label>
            <input v-model.number="filters.people_count" type="number" min="1" placeholder="不限" />
          </div>
        </div>

        <div class="form-group">
          <label>设备限制</label>
          <div class="checkbox-group">
            <label v-for="equip in equipmentOptions" :key="equip" class="checkbox-label">
              <input type="checkbox" :value="equip" v-model="filters.equipment" />
              {{ equip }}
            </label>
          </div>
        </div>

        <div class="form-group">
          <label>忌口/过敏原</label>
          <div class="checkbox-group">
            <label v-for="diet in dietOptions" :key="diet" class="checkbox-label">
              <input type="checkbox" :value="diet" v-model="filters.diet_restrictions" />
              {{ diet }}
            </label>
          </div>
        </div>

        <div class="form-group">
          <label>烹饪目标</label>
          <div class="checkbox-group">
            <label v-for="goal in goalOptions" :key="goal" class="checkbox-label">
              <input type="checkbox" :value="goal" v-model="filters.goals" />
              {{ goal }}
            </label>
          </div>
        </div>

        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="filters.allow_missing" />
            允许缺少部分食材
          </label>
        </div>
      </div>

      <button @click="getRecommendations" class="btn btn-primary btn-large" :disabled="loading">
        {{ loading ? '推荐中...' : '获取推荐' }}
      </button>
    </div>

    <div v-if="recommendationResults.length > 0" class="results">
      <h2>📋 推荐结果 ({{ recommendationResults.length }})</h2>
      <div class="result-list">
        <div v-for="result in recommendationResults" :key="result.recipe_id" class="result-card">
          <div class="result-header">
            <h3>{{ result.recipe_title }}</h3>
            <div class="score-badge">{{ Math.round(result.overall_score * 100) }}分</div>
          </div>
          <p class="result-summary">{{ result.recipe_summary || '暂无简介' }}</p>
          <div class="result-meta">
            <span v-if="result.servings">👥 {{ result.servings }}人份</span>
            <span v-if="result.total_minutes">⏱️ {{ result.total_minutes }}分钟</span>
            <span v-if="result.difficulty">📊 {{ result.difficulty }}</span>
          </div>
          <div class="result-ingredients">
            <div v-if="result.matched_ingredients.length > 0" class="matched">
              <h4>✅ 已有食材</h4>
              <span v-for="ing in result.matched_ingredients" :key="ing" class="tag tag-success">{{ ing }}</span>
            </div>
            <div v-if="result.missing_ingredients.length > 0" class="missing">
              <h4>❌ 缺少食材</h4>
              <span v-for="ing in result.missing_ingredients" :key="ing" class="tag tag-danger">{{ ing }}</span>
            </div>
          </div>
          <div class="result-reason">
            <strong>推荐理由：</strong>{{ result.reason }}
          </div>
          <div class="result-coverage">
            <span>食材覆盖率: {{ Math.round(result.coverage_score * 100) }}%</span>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="searched" class="empty-state">
      <p>😔 没有找到符合条件的菜谱</p>
      <p v-if="fallbackReason" class="fallback-reason">{{ fallbackReason }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { recommendationApi } from '../services/api';
import type { RecommendationResult } from '../types';

const ingredientInput = ref('');
const selectedIngredients = ref<string[]>([]);
const loading = ref(false);
const searched = ref(false);
const recommendationResults = ref<RecommendationResult[]>([]);
const fallbackReason = ref('');

const filters = reactive({
  season_month: '',
  max_minutes: undefined as number | undefined,
  people_count: undefined as number | undefined,
  equipment: [] as string[],
  diet_restrictions: [] as string[],
  goals: [] as string[],
  allow_missing: true
});

const equipmentOptions = ['快炒', '炖煮', '烤箱', '微波炉', '空气炸锅', '蒸锅'];
const dietOptions = ['gluten', 'dairy', 'eggs', 'nuts', 'soy', 'seafood'];
const goalOptions = ['简单', '快速', '控脂', '低卡', '高蛋白', '暖胃'];

function addIngredient() {
  const ing = ingredientInput.value.trim();
  if (ing && !selectedIngredients.value.includes(ing)) {
    selectedIngredients.value.push(ing);
    ingredientInput.value = '';
  }
}

function removeIngredient(index: number) {
  selectedIngredients.value.splice(index, 1);
}

async function getRecommendations() {
  loading.value = true;
  searched.value = true;
  try {
    const response = await recommendationApi.getRecommendations({
      ingredients: selectedIngredients.value,
      season_month: filters.season_month || undefined,
      max_minutes: filters.max_minutes,
      people_count: filters.people_count,
      equipment: filters.equipment.length > 0 ? filters.equipment : undefined,
      diet_restrictions: filters.diet_restrictions.length > 0 ? filters.diet_restrictions : undefined,
      goals: filters.goals.length > 0 ? filters.goals : undefined,
      allow_missing: filters.allow_missing
    });
    recommendationResults.value = response.results;
    fallbackReason.value = response.fallback_reason || '';
  } catch (error) {
    console.error('Failed to get recommendations:', error);
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.recommend {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

h1 {
  text-align: center;
  color: #333;
  margin-bottom: 8px;
}

.subtitle {
  text-align: center;
  color: #666;
  margin-bottom: 30px;
}

.recommend-form {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  margin-bottom: 30px;
}

.form-section {
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid #eee;
}

.form-section:last-of-type {
  border-bottom: none;
  margin-bottom: 20px;
  padding-bottom: 0;
}

.form-section h2 {
  font-size: 1.1rem;
  color: #333;
  margin: 0 0 16px 0;
}

.ingredient-input {
  display: flex;
  gap: 10px;
}

.ingredient-input input {
  flex: 1;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  min-height: 44px;
}

.selected-ingredients {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.ingredient-tag {
  background: #e3f2fd;
  color: #1976d2;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.remove-btn {
  background: none;
  border: none;
  color: #1976d2;
  cursor: pointer;
  font-size: 16px;
  padding: 0;
  line-height: 1;
}

.form-row {
  display: flex;
  gap: 16px;
}

.form-group {
  flex: 1;
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  color: #555;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  box-sizing: border-box;
  min-height: 44px;
}

.checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #555;
  cursor: pointer;
  min-height: 44px;
  padding: 8px 0;
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

.btn-large {
  width: 100%;
  padding: 14px;
  font-size: 16px;
}

.results h2 {
  font-size: 1.2rem;
  color: #333;
  margin-bottom: 16px;
}

.result-list {
  display: grid;
  gap: 16px;
}

.result-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.result-header h3 {
  margin: 0;
  color: #333;
}

.score-badge {
  background: #4a90d9;
  color: white;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 14px;
  font-weight: 500;
}

.result-summary {
  color: #666;
  font-size: 14px;
  margin: 0 0 12px 0;
}

.result-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #888;
  margin-bottom: 12px;
}

.result-ingredients {
  margin-bottom: 12px;
}

.result-ingredients h4 {
  margin: 0 0 8px 0;
  font-size: 13px;
  color: #555;
}

.tag {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  margin: 0 4px 4px 0;
}

.tag-success {
  background: #d4edda;
  color: #155724;
}

.tag-danger {
  background: #f8d7da;
  color: #721c24;
}

.result-reason {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
  line-height: 1.5;
}

.result-coverage {
  font-size: 13px;
  color: #888;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.empty-state p {
  margin: 0 0 8px 0;
  color: #888;
  font-size: 1.1rem;
}

.fallback-reason {
  font-size: 14px;
  color: #666;
}

/* 移动端响应式样式 */
@media (max-width: 767px) {
  .recommend {
    padding: 16px;
  }

  h1 {
    font-size: 1.5rem;
  }

  .subtitle {
    font-size: 0.95rem;
    margin-bottom: 20px;
  }

  .recommend-form {
    padding: 16px;
    margin-bottom: 20px;
  }

  .form-section {
    margin-bottom: 20px;
    padding-bottom: 20px;
  }

  .form-section h2 {
    font-size: 1rem;
  }

  .ingredient-input {
    flex-direction: column;
    gap: 8px;
  }

  .ingredient-input input {
    width: 100%;
  }

  .ingredient-input .btn {
    width: 100%;
  }

  .form-row {
    flex-direction: column;
    gap: 0;
  }

  .checkbox-group {
    gap: 8px;
  }

  .checkbox-label {
    min-height: 40px;
    padding: 6px 0;
  }

  .btn-large {
    padding: 16px;
    font-size: 16px;
  }

  .result-card {
    padding: 16px;
  }

  .result-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .result-header h3 {
    font-size: 1.1rem;
  }

  .result-meta {
    flex-wrap: wrap;
    gap: 8px;
  }

  .result-ingredients h4 {
    font-size: 12px;
  }

  .empty-state {
    padding: 40px 16px;
  }

  .empty-state p {
    font-size: 1rem;
  }
}

/* 平板端响应式样式 */
@media (min-width: 768px) and (max-width: 1023px) {
  .recommend-form {
    padding: 20px;
  }

  .form-row {
    gap: 12px;
  }
}
</style>
