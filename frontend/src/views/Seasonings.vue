<template>
  <div class="seasonings">
    <div class="header">
      <div class="header-left">
        <button @click="goBack" class="btn-back" aria-label="返回">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path d="M19 12H6" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
            <path d="M12 19L5 12L12 5" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
          </svg>
        </button>
        <h1>调料管理</h1>
      </div>
      <button @click="openCreate" class="btn btn-primary">添加调料</button>
    </div>

    <div class="filters">
      <input
        v-model="query"
        type="text"
        placeholder="搜索调料..."
        @input="debouncedSearch"
      />
      <select v-model="categoryFilter" @change="load">
        <option value="">全部分类</option>
        <option v-for="c in seaCategories" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
    </div>

    <div class="list" v-if="seasonings.length > 0">
      <div v-for="s in seasonings" :key="s.id" class="seasoning-card">
        <div class="card-main" @click="openEdit(s)">
          <div class="seasoning-header">
            <h3>{{ s.canonical_name }}</h3>
            <span class="category-badge">{{ s.category_name || '默认分类' }}</span>
          </div>
        </div>
        <div class="seasoning-actions">
          <button @click="remove(s)" class="btn-small btn-danger">删除</button>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>暂无调料</p>
      <button @click="openCreate" class="btn btn-primary">添加第一个调料</button>
    </div>

    <!-- 创建/编辑调料弹窗 -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <h2>{{ editingSeasoning ? '编辑调料' : '添加调料' }}</h2>
        <form @submit.prevent="saveSeasoning">
          <div class="form-group">
            <label>标准名称 *</label>
            <input v-model="seasoningForm.canonical_name" type="text" required />
          </div>
          <div class="form-group">
            <label>分类</label>
            <AppSelect
              v-model="seasoningForm.category_id"
              :options="seaCategoryOptions"
              placeholder="默认分类"
              search-placeholder="搜索分类..."
            />
          </div>
          <div class="modal-actions">
            <button type="button" @click="closeModal" class="btn btn-secondary">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="!seasoningForm.canonical_name.trim()">{{ editingSeasoning ? '保存' : '添加' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useGoBack } from '../composables/useGoBack';
import { seasoningApi, categoryApi } from '../services/api';
import { toast } from '../composables/useToast';
import AppSelect from '../components/AppSelect.vue';
import type { Seasoning, Category } from '../types';

const { goBack } = useGoBack('/me');

const seasonings = ref<Seasoning[]>([]);
const seaCategories = ref<Category[]>([]);

// 调料分类下拉选项，首项“默认分类”用于清空分类
const seaCategoryOptions = computed(() => [
  { value: '', label: '默认分类' },
  ...seaCategories.value.map(c => ({ value: c.id, label: c.name }))
]);
const query = ref('');
const categoryFilter = ref('');
const showModal = ref(false);
const editingSeasoning = ref<Seasoning | null>(null);

const seasoningForm = ref({
  canonical_name: '',
  category_id: ''
});

let timer: ReturnType<typeof setTimeout>;
function debouncedSearch() {
  clearTimeout(timer);
  timer = setTimeout(load, 400);
}

async function load() {
  try {
    const res = await seasoningApi.list({
      query: query.value || undefined,
      category_id: categoryFilter.value || undefined,
      page: 1,
      page_size: 100
    });
    seasonings.value = res.data;
  } catch (e) {
    console.error('load seasonings failed', e);
  }
}

async function loadCategories() {
  try {
    const res = await categoryApi.list('seasoning');
    seaCategories.value = res.data;
  } catch (e) {
    console.error('load sea categories failed', e);
  }
}

function openCreate() {
  editingSeasoning.value = null;
  seasoningForm.value = { canonical_name: '', category_id: '' };
  showModal.value = true;
}

function openEdit(s: Seasoning) {
  editingSeasoning.value = s;
  seasoningForm.value = {
    canonical_name: s.canonical_name,
    category_id: s.category_id || ''
  };
  showModal.value = true;
}

function closeModal() {
  showModal.value = false;
  editingSeasoning.value = null;
  seasoningForm.value = { canonical_name: '', category_id: '' };
}

async function saveSeasoning() {
  const name = seasoningForm.value.canonical_name.trim();
  if (!name) return;
  try {
    if (editingSeasoning.value) {
      await seasoningApi.update(editingSeasoning.value.id, {
        canonical_name: name,
        category_id: seasoningForm.value.category_id || undefined
      });
      toast('已保存');
    } else {
      await seasoningApi.create({
        canonical_name: name,
        category_id: seasoningForm.value.category_id || undefined
      });
      toast('已添加');
    }
    closeModal();
    load();
  } catch (e: any) {
    toast(e?.response?.data?.detail || '保存失败', 'error');
  }
}

async function remove(s: Seasoning) {
  if (!window.confirm(`确定删除调料「${s.canonical_name}」？`)) return;
  try {
    await seasoningApi.delete(s.id);
    toast('已删除');
    load();
  } catch (e: any) {
    toast(e?.response?.data?.detail || '删除失败', 'error');
  }
}

onMounted(() => { load(); loadCategories(); });
</script>

<style scoped>
.seasonings { padding: 0 20px 20px; }

.header {
  position: sticky;
  top: var(--navbar-height, 64px);
  z-index: 150;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 16px 0;
  margin-bottom: 16px;
  background: #f5f5f5;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.header h1 { margin: 0; }
.header-left { display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1; }
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
  flex-shrink: 0;
}
.btn-back:hover { background: rgba(7, 132, 255, 0.08); }

.filters { display: flex; gap: 10px; margin-bottom: 16px; }
.filters input,
.filters select { padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; min-height: 44px; box-sizing: border-box; }
.filters input { flex: 1; }
.filters select { flex-shrink: 0; }

.list { display: grid; gap: 12px; }
.seasoning-card {
  display: flex;
  gap: 12px;
  align-items: center;
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
.card-main { flex: 1; min-width: 0; cursor: pointer; }
.card-main:active { opacity: 0.75; }

.seasoning-header { display: flex; align-items: center; gap: 8px; }
.seasoning-header h3 { margin: 0; color: #333; font-size: 16px; }
.category-badge { background: #f0f0f0; padding: 4px 10px; border-radius: 12px; font-size: 12px; color: #666; }

.seasoning-actions { display: flex; gap: 8px; flex-shrink: 0; align-items: center; }

.empty-state { text-align: center; padding: 60px 20px; color: #888; }
.empty-state p { margin: 0 0 16px; }

.btn { padding: 10px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; min-height: 44px; text-decoration: none; display: inline-flex; align-items: center; }
.btn-primary { background: #4a90d9; color: white; }
.btn-primary:hover { background: #357abd; }
.btn-primary:disabled { background: #ccc; cursor: not-allowed; }
.btn-secondary { background: #e0e0e0; color: #333; }
.btn-secondary:hover { background: #d0d0d0; }
.btn-small { padding: 8px 12px; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; min-height: 36px; white-space: nowrap; }
.btn-danger { background: #dc3545; color: white; }
.btn-danger:hover { background: #c82333; }

.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
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
.modal h2 { margin: 0 0 20px 0; color: #333; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 6px; font-size: 14px; color: #555; }
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
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }

@media (max-width: 767px) {
  .seasonings { padding: 0 16px 16px; }
  .header { padding: 14px 0; }
  .header h1 { text-align: center; font-size: 1.5rem; }
  .header-left { justify-content: center; position: relative; width: 100%; }
  .btn-back { position: absolute; left: 0; }
  .filters { flex-direction: row; gap: 8px; align-items: center; }
  .filters input { flex: 1; min-width: 0; }
  .seasoning-card { padding: 12px; gap: 8px; }
  .seasoning-header { flex-wrap: wrap; }
  .modal-overlay { padding: 0; align-items: flex-end; }
  .modal { border-radius: 12px 12px 0 0; max-height: 95vh; padding: 24px 16px; }
  .modal-actions { flex-direction: column; gap: 8px; }
  .modal-actions .btn { width: 100%; }
}
</style>
