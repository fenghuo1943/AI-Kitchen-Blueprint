<template>
  <div class="inventory">
    <div class="header">
      <div class="header-left">
        <button @click="goBack" class="btn-back" aria-label="返回">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path d="M19 12H6" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
            <path d="M12 19L5 12L12 5" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
          </svg>
        </button>
        <h1>🥬 库存管理</h1>
      </div>
      <button @click="showAddModal = true" class="btn btn-primary">添加库存</button>
    </div>

    <div class="expiring-alert" v-if="expiringItems.length > 0">
      <h3>⚠️ 即将过期</h3>
      <div class="expiring-list">
        <div v-for="item in expiringItems" :key="item.id" class="expiring-item">
          <span class="item-name">{{ item.ingredient_name }}</span>
          <span class="item-quantity">{{ item.quantity }} {{ item.unit }}</span>
          <span class="item-expiry">{{ formatDate(item.expires_at) }}</span>
        </div>
      </div>
    </div>

    <div class="inventory-list" v-if="inventoryItems.length > 0">
      <div v-for="item in inventoryItems" :key="item.id" class="inventory-card" :class="{ expired: item.is_expired }">
        <div class="item-header">
          <h3>{{ item.ingredient_name }}</h3>
          <span v-if="item.is_expired" class="expired-badge">已过期</span>
        </div>
        <div class="item-details">
          <span>数量: {{ item.quantity || '-' }} {{ item.unit || '' }}</span>
          <span v-if="item.expires_at">过期: {{ formatDate(item.expires_at) }}</span>
        </div>
        <div v-if="item.note" class="item-note">{{ item.note }}</div>
        <div class="item-actions">
          <button @click="editItem(item)" class="btn btn-small">编辑</button>
          <button @click="deleteItem(item.id)" class="btn btn-small btn-danger">删除</button>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>📦 库存为空</p>
      <button @click="showAddModal = true" class="btn btn-primary">添加第一个库存</button>
    </div>

    <div class="pagination" v-if="total > pageSize">
      <button @click="prevPage" :disabled="page === 1">上一页</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button @click="nextPage" :disabled="page === totalPages">下一页</button>
    </div>

    <!-- 添加库存弹窗 -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="closeAddModal">
      <div class="modal">
        <h2>{{ editingItem ? '编辑库存' : '添加库存' }}</h2>
        <form @submit.prevent="saveItem">
          <div class="form-group">
            <label>食材 *</label>
            <select v-model="itemForm.ingredient_id" required>
              <option value="">请选择食材</option>
              <option v-for="ing in availableIngredients" :key="ing.id" :value="ing.id">
                {{ ing.canonical_name }}
              </option>
            </select>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>数量</label>
              <input v-model="itemForm.quantity" type="text" />
            </div>
            <div class="form-group">
              <label>单位</label>
              <input v-model="itemForm.unit" type="text" />
            </div>
          </div>
          <div class="form-group">
            <label>过期时间</label>
            <input v-model="itemForm.expires_at" type="date" />
          </div>
          <div class="form-group">
            <label>备注</label>
            <textarea v-model="itemForm.note"></textarea>
          </div>
          <div class="modal-actions">
            <button type="button" @click="closeAddModal" class="btn btn-secondary">取消</button>
            <button type="submit" class="btn btn-primary">{{ editingItem ? '保存' : '添加' }}</button>
          </div>
        </form>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useGoBack } from '../composables/useGoBack';
import { inventoryApi, ingredientApi } from '../services/api';
import type { InventoryItem, Ingredient } from '../types';

const { goBack } = useGoBack('/me');

const inventoryItems = ref<InventoryItem[]>([]);
const expiringItems = ref<InventoryItem[]>([]);
const availableIngredients = ref<Ingredient[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;

const showAddModal = ref(false);
const editingItem = ref<InventoryItem | null>(null);

const itemForm = ref({
  ingredient_id: '',
  quantity: '',
  unit: '',
  expires_at: '',
  note: ''
});

const totalPages = computed(() => Math.ceil(total.value / pageSize));

function formatDate(dateStr?: string) {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('zh-CN');
}

async function loadInventory() {
  try {
    const response = await inventoryApi.listItems({
      page: page.value,
      page_size: pageSize
    });
    inventoryItems.value = response.data;
    total.value = response.total;
  } catch (error) {
    console.error('Failed to load inventory:', error);
  }
}

async function loadExpiringItems() {
  try {
    expiringItems.value = await inventoryApi.getExpiringSoon({ days: 7 });
  } catch (error) {
    console.error('Failed to load expiring items:', error);
  }
}

async function loadIngredients() {
  try {
    const response = await ingredientApi.list({ page_size: 100 });
    availableIngredients.value = response.data;
  } catch (error) {
    console.error('Failed to load ingredients:', error);
  }
}

function editItem(item: InventoryItem) {
  editingItem.value = item;
  itemForm.value = {
    ingredient_id: item.ingredient_id,
    quantity: item.quantity || '',
    unit: item.unit || '',
    expires_at: item.expires_at ? item.expires_at.split('T')[0] : '',
    note: item.note || ''
  };
  showAddModal.value = true;
}

async function saveItem() {
  try {
    if (editingItem.value) {
      await inventoryApi.updateItem(editingItem.value.id, {
        quantity: itemForm.value.quantity || undefined,
        unit: itemForm.value.unit || undefined,
        expires_at: itemForm.value.expires_at ? new Date(itemForm.value.expires_at).toISOString() : undefined,
        note: itemForm.value.note || undefined
      });
    } else {
      await inventoryApi.createItem({
        ingredient_id: itemForm.value.ingredient_id,
        quantity: itemForm.value.quantity || undefined,
        unit: itemForm.value.unit || undefined,
        expires_at: itemForm.value.expires_at ? new Date(itemForm.value.expires_at).toISOString() : undefined,
        note: itemForm.value.note || undefined
      });
    }
    closeAddModal();
    loadInventory();
    loadExpiringItems();
  } catch (error) {
    console.error('Failed to save item:', error);
  }
}

async function deleteItem(id: string) {
  if (!confirm('确定要删除这个库存物品吗？')) return;
  try {
    await inventoryApi.deleteItem(id);
    loadInventory();
  } catch (error) {
    console.error('Failed to delete item:', error);
  }
}

function closeAddModal() {
  showAddModal.value = false;
  editingItem.value = null;
  itemForm.value = {
    ingredient_id: '',
    quantity: '',
    unit: '',
    expires_at: '',
    note: ''
  };
}

function prevPage() {
  if (page.value > 1) {
    page.value--;
    loadInventory();
  }
}

function nextPage() {
  if (page.value < totalPages.value) {
    page.value++;
    loadInventory();
  }
}

onMounted(() => {
  loadInventory();
  loadExpiringItems();
  loadIngredients();
});
</script>

<style scoped>
.inventory {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

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

.btn-back:hover {
  background: rgba(7, 132, 255, 0.08);
}

.expiring-alert {
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 20px;
}

.expiring-alert h3 {
  margin: 0 0 12px 0;
  color: #856404;
}

.expiring-list {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.expiring-item {
  background: white;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
}

.item-name {
  font-weight: 500;
  margin-right: 8px;
}

.item-quantity {
  color: #666;
  margin-right: 8px;
}

.item-expiry {
  color: #dc3545;
}

.inventory-list {
  display: grid;
  gap: 16px;
}

.inventory-card {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.inventory-card.expired {
  opacity: 0.6;
  border-left: 4px solid #dc3545;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.item-header h3 {
  margin: 0;
  color: #333;
}

.expired-badge {
  background: #dc3545;
  color: white;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
}

.item-details {
  display: flex;
  gap: 16px;
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.item-note {
  font-size: 13px;
  color: #888;
  margin-bottom: 8px;
}

.item-actions {
  display: flex;
  gap: 8px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #888;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  margin-top: 20px;
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

.btn-small {
  padding: 8px 12px;
  font-size: 12px;
  min-height: 36px;
}

.btn-primary {
  background: #4a90d9;
  color: white;
}

.btn-primary:hover {
  background: #357abd;
}

.btn-secondary {
  background: #e0e0e0;
  color: #333;
}

.btn-secondary:hover {
  background: #d0d0d0;
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-danger:hover {
  background: #c82333;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
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

.modal h2 {
  margin: 0 0 20px 0;
  color: #333;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  color: #555;
}

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  box-sizing: border-box;
  min-height: 44px;
}

.form-row {
  display: flex;
  gap: 12px;
}

.form-row .form-group {
  flex: 1;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

/* 移动端响应式样式 */
@media (max-width: 767px) {
  .inventory {
    padding: 16px;
  }

  .header {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }

  .header h1 {
    font-size: 1.5rem;
    margin: 0;
    text-align: center;
  }

  .header-left {
    justify-content: center;
    position: relative;
    width: 100%;
  }

  .btn-back {
    position: absolute;
    left: 0;
  }

  .header .btn {
    width: 100%;
  }

  .expiring-list {
    flex-direction: column;
    gap: 8px;
  }

  .expiring-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .item-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .item-header h3 {
    font-size: 1.1rem;
  }

  .item-details {
    flex-direction: column;
    gap: 4px;
  }

  .item-actions {
    flex-wrap: wrap;
    gap: 8px;
  }

  .item-actions .btn {
    flex: 1;
    min-width: calc(50% - 4px);
  }

  .pagination {
    gap: 12px;
  }

  .pagination button {
    min-height: 44px;
    padding: 8px 16px;
  }

  /* 移动端模态框 */
  .modal-overlay {
    padding: 0;
    align-items: flex-end;
  }

  .modal {
    border-radius: 12px 12px 0 0;
    max-height: 95vh;
    padding: 24px 16px;
  }

  .form-row {
    flex-direction: column;
    gap: 0;
  }

  .modal-actions {
    flex-direction: column;
    gap: 8px;
  }

  .modal-actions .btn {
    width: 100%;
  }
}

</style>
