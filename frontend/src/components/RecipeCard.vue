<template>
  <div class="recipe-card" @click="openDetail">
    <div class="recipe-cover" v-if="recipe.cover">
      <img :src="recipe.cover" :alt="recipe.title" />
    </div>
    <div class="recipe-body">
      <div class="recipe-title-row">
        <h3 class="recipe-title">{{ recipe.title }}</h3>
        <span v-if="recipe.is_in_today_menu" class="in-menu-badge">今日菜单</span>
      </div>
      <p v-if="recipe.summary" class="recipe-summary">{{ recipe.summary }}</p>
      <div class="recipe-meta">
        <span v-if="totalMinutes">⏱️ {{ totalMinutes }}分钟</span>
        <span v-if="recipe.difficulty">📊 {{ recipe.difficulty }}</span>
        <span v-if="recipe.cooked_count">🔥 做过{{ recipe.cooked_count }}次</span>
      </div>
      <div class="recipe-actions" @click.stop>
        <button
          :class="['btn-small', recipe.is_favorited ? 'btn-cancel' : 'btn-confirm']"
          @click="toggleFavorite"
        >
          {{ recipe.is_favorited ? '♥ 已收藏' : '♡ 收藏' }}
        </button>
        <button class="btn-small btn-confirm" @click="openAddMenu">
          📅 加入菜单
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import type { Recipe, DiscoverRecipe } from '../types';

type RecipeCardItem = Recipe | DiscoverRecipe;

const props = defineProps<{ recipe: RecipeCardItem }>();
const emit = defineEmits<{
  (e: 'favorite', recipe: RecipeCardItem): void;
  (e: 'menu', recipe: RecipeCardItem): void;
}>();

const router = useRouter();
const totalMinutes = computed(() => {
  const r = props.recipe as any;
  if (r.cook_time != null) return r.cook_time;
  const total = (r.prep_minutes || 0) + (r.cook_minutes || 0);
  return total || undefined;
});

function openDetail() {
  router.push(`/recipes/${props.recipe.id}`);
}

function toggleFavorite() {
  emit('favorite', props.recipe);
}

function openAddMenu() {
  emit('menu', props.recipe);
}
</script>

<style scoped>
.recipe-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
}

.recipe-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.recipe-cover {
  width: 100%;
  height: 140px;
  background: #f0f0f0;
}

.recipe-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.recipe-body {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.recipe-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.recipe-title {
  margin: 0;
  font-size: 1rem;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.in-menu-badge {
  background: #d4edda;
  color: #155724;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  flex-shrink: 0;
}

.recipe-summary {
  margin: 0;
  color: #888;
  font-size: 13px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.recipe-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #999;
  flex-wrap: wrap;
}

.recipe-actions {
  display: flex;
  gap: 8px;
  margin-top: auto;
}

.btn-small {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  min-height: 36px;
}

.btn-confirm {
  background: #4a90d9;
  color: white;
}

.btn-cancel {
  background: #f8d7da;
  color: #721c24;
}

@media (max-width: 767px) {
  .recipe-cover {
    height: 120px;
  }
}
</style>
