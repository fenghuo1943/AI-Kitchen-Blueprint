<template>
  <div class="recipe-form">
    <div class="header">
      <div class="header-left">
        <button @click="goBack" class="btn-back" aria-label="返回">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path d="M19 12H6" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
            <path d="M12 19L5 12L12 5" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
          </svg>
        </button>
        <h1>{{ isEdit ? '✏️ 编辑菜谱' : '🍳 新建菜谱' }}</h1>
      </div>
    </div>

    <form @submit.prevent="save">
      <!-- 基础信息 -->
      <div class="card">
        <h2>基本信息</h2>
        <div class="form-group">
          <label>菜谱名称 *</label>
          <input v-model="form.title" type="text" required />
        </div>
        <div class="form-group">
          <label>简介</label>
          <textarea v-model="form.summary" rows="3"></textarea>
        </div>
        <div class="form-group">
          <label>封面图 URL</label>
          <input v-model="form.cover" type="url" placeholder="https://..." />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>份量</label>
            <input v-model.number="form.servings" type="number" min="1" />
          </div>
          <div class="form-group">
            <label>准备时间(分钟)</label>
            <input v-model.number="form.prep_minutes" type="number" min="0" />
          </div>
          <div class="form-group">
            <label>烹饪时间(分钟)</label>
            <input v-model.number="form.cook_minutes" type="number" min="0" />
          </div>
        </div>
        <div class="form-group">
          <label>难度</label>
          <select v-model="form.difficulty">
            <option value="">请选择</option>
            <option value="简单">简单</option>
            <option value="中等">中等</option>
            <option value="困难">困难</option>
          </select>
        </div>
        <div class="form-group">
          <label>状态</label>
          <select v-model="form.status">
            <option value="draft">草稿</option>
            <option value="published">已发布</option>
            <option value="archived">已归档</option>
          </select>
        </div>
      </div>

      <!-- 分类 -->
      <div class="card">
        <h2>分类</h2>
        <div class="chips">
          <span
            v-for="c in recipeCategories"
            :key="c.id"
            :class="['chip', isCatSelected(c.id) ? 'selected' : '']"
            @click="toggleCategory(c.id)"
          >{{ c.name }}</span>
        </div>
      </div>

      <!-- 食材 -->
      <div class="card">
        <h2>🥬 食材</h2>
        <button type="button" class="btn btn-secondary" @click="showIngPicker = true">＋ 添加食材</button>
        <div v-if="form.ingredients.length" class="ing-rows">
          <div v-for="(ing, idx) in form.ingredients" :key="ing.ingredient_id" class="ing-row">
            <span class="ing-name">{{ ingName(ing.ingredient_id) }}</span>
            <input v-model="ing.quantity" type="text" placeholder="数量" class="ing-quantity" />
            <input v-model="ing.unit" type="text" placeholder="单位" class="ing-unit" />
            <button type="button" class="row-remove" @click="form.ingredients.splice(idx, 1)">×</button>
          </div>
        </div>
      </div>

      <!-- 调料 -->
      <div class="card">
        <h2>🧂 调料</h2>
        <button type="button" class="btn btn-secondary" @click="showSeaPicker = true">＋ 添加调料</button>
        <div v-if="form.seasonings.length" class="ing-rows">
          <div v-for="(sea, idx) in form.seasonings" :key="sea.seasoning_id" class="ing-row">
            <span class="ing-name">{{ seaName(sea.seasoning_id) }}</span>
            <input v-model="sea.quantity" type="text" placeholder="用量" class="ing-quantity" />
            <button type="button" class="row-remove" @click="form.seasonings.splice(idx, 1)">×</button>
          </div>
        </div>
      </div>

      <!-- 步骤 -->
      <div class="card">
        <h2>📝 步骤</h2>
        <button type="button" class="btn btn-secondary" @click="addStep">＋ 添加步骤</button>
        <div v-for="(step, idx) in form.steps" :key="idx" class="step-row">
          <div class="step-head">
            <span class="step-no">第 {{ idx + 1 }} 步</span>
            <button type="button" class="row-remove" @click="form.steps.splice(idx, 1)">×</button>
          </div>
          <textarea v-model="step.instruction" rows="2" placeholder="操作说明"></textarea>
          <input v-model.number="step.duration_minutes" type="number" min="0" placeholder="预计分钟（可选）" />
        </div>
      </div>

      <div class="actions">
        <button type="button" class="btn btn-secondary" @click="goBack">取消</button>
        <button type="submit" class="btn btn-primary" :disabled="!form.title || saving">
          {{ saving ? '保存中...' : (isEdit ? '保存修改' : '创建菜谱') }}
        </button>
      </div>
    </form>

    <!-- 食材选择器 -->
    <div v-if="showIngPicker" class="modal-overlay" @click.self="showIngPicker = false">
      <div class="modal">
        <h3>选择食材</h3>
        <input v-model="ingSearch" type="text" placeholder="搜索食材" class="modal-search" />
        <select v-model="ingCatFilter" class="modal-select">
          <option value="">全部分类</option>
          <option v-for="c in ingCategories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <div class="pick-list">
          <span
            v-for="ing in filteredIngs"
            :key="ing.id"
            :class="['item-pick', isIngPicked(ing.id) ? 'picked' : '']"
            @click="pickIngredient(ing)"
          >{{ ing.canonical_name }}</span>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn btn-primary" @click="showIngPicker = false">完成</button>
        </div>
      </div>
    </div>

    <!-- 调料选择器 -->
    <div v-if="showSeaPicker" class="modal-overlay" @click.self="showSeaPicker = false">
      <div class="modal">
        <h3>选择调料</h3>
        <input v-model="seaSearch" type="text" placeholder="搜索调料" class="modal-search" />
        <div class="pick-list">
          <span
            v-for="sea in filteredSeas"
            :key="sea.id"
            :class="['item-pick', isSeaPicked(sea.id) ? 'picked' : '']"
            @click="pickSeasoning(sea)"
          >{{ sea.canonical_name }}</span>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn btn-primary" @click="showSeaPicker = false">完成</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { recipeApi, ingredientApi, seasoningApi, categoryApi } from '../services/api';
import { useAppStore } from '../stores/app';
import { toast } from '../composables/useToast';
import { useGoBack } from '../composables/useGoBack';
import type { Category, Ingredient, Seasoning, Recipe } from '../types';

const route = useRoute();
const router = useRouter();
const appStore = useAppStore();
const { goBack } = useGoBack();
const isEdit = computed(() => !!route.params.id);

const form = ref({
  title: '',
  summary: '',
  cover: '',
  servings: undefined as number | undefined,
  prep_minutes: undefined as number | undefined,
  cook_minutes: undefined as number | undefined,
  difficulty: '',
  status: 'draft',
  category_ids: [] as string[],
  ingredients: [] as { ingredient_id: string; ingredient_name?: string; quantity: string; unit: string; preparation?: string }[],
  seasonings: [] as { seasoning_id: string; quantity: string }[],
  steps: [] as { instruction: string; duration_minutes?: number }[]
});

const recipeCategories = ref<Category[]>([]);
const ingCategories = ref<Category[]>([]);
const allIngredients = ref<Ingredient[]>([]);
const allSeasonings = ref<Seasoning[]>([]);

const showIngPicker = ref(false);
const showSeaPicker = ref(false);
const ingSearch = ref('');
const ingCatFilter = ref('');
const seaSearch = ref('');
const saving = ref(false);

const filteredIngs = computed(() => allIngredients.value.filter(i =>
  (!ingCatFilter.value || i.category_id === ingCatFilter.value) &&
  (!ingSearch.value || i.canonical_name.includes(ingSearch.value))
));
const filteredSeas = computed(() => allSeasonings.value.filter(s =>
  !seaSearch.value || s.canonical_name.includes(seaSearch.value)
));

function isCatSelected(id: string) { return form.value.category_ids.includes(id); }
function toggleCategory(id: string) {
  const idx = form.value.category_ids.indexOf(id);
  if (idx >= 0) form.value.category_ids.splice(idx, 1);
  else form.value.category_ids.push(id);
}

function isIngPicked(id: string) { return form.value.ingredients.some(i => i.ingredient_id === id); }
function isSeaPicked(id: string) { return form.value.seasonings.some(s => s.seasoning_id === id); }

function ingName(id: string) {
  // 优先用菜谱接口带回的食材名（对第 100 个之后的食材、AI 采集新食材等不在下拉列表里的也有效）
  return form.value.ingredients.find(i => i.ingredient_id === id)?.ingredient_name
    || allIngredients.value.find(i => i.id === id)?.canonical_name
    || id;
}
function seaName(id: string) {
  return allSeasonings.value.find(s => s.id === id)?.canonical_name || id;
}

function pickIngredient(ing: Ingredient) {
  if (isIngPicked(ing.id)) {
    form.value.ingredients = form.value.ingredients.filter(i => i.ingredient_id !== ing.id);
  } else {
    form.value.ingredients.push({ ingredient_id: ing.id, ingredient_name: ing.canonical_name, quantity: '', unit: '' });
  }
}
function pickSeasoning(sea: Seasoning) {
  if (isSeaPicked(sea.id)) {
    form.value.seasonings = form.value.seasonings.filter(s => s.seasoning_id !== sea.id);
  } else {
    form.value.seasonings.push({ seasoning_id: sea.id, quantity: '' });
  }
}

function addStep() {
  form.value.steps.push({ instruction: '', duration_minutes: undefined });
}

async function loadData() {
  try {
    const [rc, ic, ings, seas] = await Promise.all([
      categoryApi.list('recipe'),
      categoryApi.list('ingredient'),
      ingredientApi.list({ page: 1, page_size: 100 }),
      seasoningApi.getAll()
    ]);
    recipeCategories.value = rc.data;
    ingCategories.value = ic.data;
    allIngredients.value = ings.data;
    allSeasonings.value = seas.data;
  } catch (e) {
    console.error('Failed to load form data:', e);
  }

  if (isEdit.value) {
    const recipe = await recipeApi.get(route.params.id as string);
    form.value.title = recipe.title;
    form.value.summary = recipe.summary || '';
    form.value.cover = recipe.cover || '';
    form.value.servings = recipe.servings;
    form.value.prep_minutes = recipe.prep_minutes;
    form.value.cook_minutes = recipe.cook_minutes;
    form.value.difficulty = recipe.difficulty || '';
    form.value.status = recipe.status;
    form.value.category_ids = recipe.categories.map(c => c.id);
    form.value.ingredients = recipe.ingredients.map(i => ({
      ingredient_id: i.ingredient_id, ingredient_name: i.ingredient_name,
      quantity: i.quantity || '', unit: i.unit || ''
    }));
    form.value.seasonings = recipe.seasonings.map(s => ({ seasoning_id: s.seasoning_id, quantity: s.quantity || '' }));
    form.value.steps = recipe.steps.map(s => ({ instruction: s.instruction, duration_minutes: s.duration_minutes }));
  }
}

async function save() {
  if (!form.value.title.trim()) return;
  saving.value = true;
  try {
    const payload = {
      title: form.value.title,
      summary: form.value.summary || undefined,
      cover: form.value.cover || undefined,
      servings: form.value.servings,
      prep_minutes: form.value.prep_minutes,
      cook_minutes: form.value.cook_minutes,
      difficulty: form.value.difficulty || undefined,
      status: form.value.status,
      category_ids: form.value.category_ids,
      ingredients: form.value.ingredients.map((ing, idx) => ({
        ingredient_id: ing.ingredient_id,
        quantity: ing.quantity || undefined,
        unit: ing.unit || undefined,
        sort_order: idx
      })),
      seasonings: form.value.seasonings.map(s => ({ seasoning_id: s.seasoning_id, quantity: s.quantity || undefined })),
      steps: form.value.steps.filter(s => s.instruction.trim()).map((s, idx) => ({
        step_no: idx + 1, instruction: s.instruction, duration_minutes: s.duration_minutes
      }))
    };
    if (isEdit.value) {
      await recipeApi.update(route.params.id as string, payload);
      appStore.bumpRecipeVersion('update'); // 通知缓存的菜谱库列表需要刷新
      toast('保存成功');
      // 用 replace 替换编辑页历史记录：详情页按返回时回到编辑前的页面，而非已保存的编辑页
      router.replace(`/recipes/${route.params.id}`);
    } else {
      const recipe = await recipeApi.create(payload);
      appStore.bumpRecipeVersion('create'); // 通知缓存的菜谱库列表需要刷新
      toast('创建成功');
      // 同上：新建页不留在历史栈，详情页按返回时回到新建前的页面
      router.replace(`/recipes/${recipe.id}`);
    }
  } catch (e: any) {
    toast(e?.response?.data?.detail || '保存失败', 'error');
  } finally {
    saving.value = false;
  }
}

onMounted(loadData);
</script>

<style scoped>
.recipe-form { padding: 20px; max-width: 800px; margin: 0 auto; }
.header-left { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.header-left h1 { margin: 0; }
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
.btn-back:hover { background: rgba(7, 132, 255, 0.08); }
.card {
  background: white; border-radius: 12px; padding: 20px; margin-bottom: 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.card h2 { margin: 0 0 12px 0; font-size: 1.1rem; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; margin-bottom: 6px; font-size: 14px; color: #555; }
.form-group input, .form-group textarea, .form-group select {
  width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 16px;
  box-sizing: border-box; min-height: 44px;
}
.form-group textarea { resize: vertical; }
.form-row { display: flex; gap: 12px; }
.form-row .form-group { flex: 1; }

.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip { padding: 8px 14px; border: 1px solid #ddd; border-radius: 16px; cursor: pointer; font-size: 14px; }
.chip.selected { background: #4a90d9; color: white; border-color: #4a90d9; }

.ing-rows { margin-top: 12px; display: flex; flex-direction: column; gap: 8px; }
.ing-row { display: flex; gap: 8px; align-items: center; background: #f9f9f9; padding: 10px; border-radius: 8px; }
.ing-name { flex: 1; font-weight: 500; color: #333; }
.ing-quantity { width: 70px; padding: 8px; border: 1px solid #ddd; border-radius: 6px; }
.ing-unit { width: 60px; padding: 8px; border: 1px solid #ddd; border-radius: 6px; }
.row-remove { border: none; background: none; color: #f44336; font-size: 20px; cursor: pointer; }

.step-row { background: #f9f9f9; border-radius: 8px; padding: 12px; margin-top: 12px; }
.step-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.step-no { font-weight: 500; color: #555; }
.step-row textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; margin-bottom: 8px; }
.step-row input { width: 140px; padding: 8px; border: 1px solid #ddd; border-radius: 6px; }

.actions { display: flex; justify-content: flex-end; gap: 10px; }
.btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; min-height: 44px; }
.btn-primary { background: #4a90d9; color: white; }
.btn-primary:disabled { background: #ccc; cursor: not-allowed; }
.btn-secondary { background: #f0f0f0; color: #333; }

.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 16px;
}
.modal { background: white; border-radius: 12px; padding: 24px; width: 100%; max-width: 480px; max-height: 80vh; display: flex; flex-direction: column; }
.modal h3 { margin: 0 0 12px 0; }
.modal-search, .modal-select { padding: 10px; border: 1px solid #ddd; border-radius: 6px; min-height: 44px; margin-bottom: 10px; width: 100%; box-sizing: border-box; }
.pick-list { display: flex; flex-wrap: wrap; gap: 8px; overflow-y: auto; flex: 1; padding: 4px; }
.item-pick { padding: 8px 14px; border: 1px solid #ddd; border-radius: 16px; cursor: pointer; font-size: 14px; }
.item-pick.picked { background: #4a90d9; color: white; border-color: #4a90d9; }
.modal-actions { display: flex; justify-content: flex-end; margin-top: 16px; }

@media (max-width: 767px) {
  .recipe-form { padding: 16px; }
  .form-row { flex-direction: column; gap: 0; }
  .ing-row { flex-wrap: wrap; }
  .ing-quantity { width: 100%; }
  .ing-unit { width: 100%; }
  .modal-overlay { padding: 0; align-items: flex-end; }
  .modal { border-radius: 12px 12px 0 0; max-height: 90vh; }
  .actions { flex-direction: column; }
  .actions .btn { width: 100%; }
}
</style>
