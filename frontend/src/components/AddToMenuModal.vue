<template>
  <div v-if="visible" class="modal-overlay" @click.self="close">
    <div class="modal">
      <h3>📅 加入菜单</h3>
      <div class="date-options">
        <button
          v-for="opt in options"
          :key="opt.label"
          :class="['date-option', selected === opt.value ? 'active' : '']"
          @click="selected = opt.value"
        >
          {{ opt.label }}
        </button>
      </div>
      <div class="form-group">
        <label>或选择日期</label>
        <input type="date" v-model="customDate" class="date-input" />
      </div>
      <div class="modal-actions">
        <button class="btn btn-secondary" @click="close">取消</button>
        <button class="btn btn-primary" :disabled="!effectiveDate" @click="confirm">确认加入</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { menuApi } from '../services/api';
import { toast } from '../composables/useToast';

const props = defineProps<{ recipeId: string }>();
const visible = ref(false);
const selected = ref('');
const customDate = ref('');

function fmt(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

const options = computed(() => {
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  const dayAfter = new Date(today);
  dayAfter.setDate(today.getDate() + 2);
  return [
    { label: '今天', value: fmt(today) },
    { label: '明天', value: fmt(tomorrow) },
    { label: '后天', value: fmt(dayAfter) }
  ];
});

const effectiveDate = computed(() => customDate.value || selected.value);

function open() {
  visible.value = true;
  selected.value = options.value[0].value;
  customDate.value = '';
}

function close() {
  visible.value = false;
}

async function confirm() {
  try {
    await menuApi.add(props.recipeId, effectiveDate.value);
    toast('已加入菜单');
    close();
  } catch (e: any) {
    toast(e?.response?.data?.detail || '加入失败', 'error');
  }
}

defineExpose({ open, close });
</script>

<style scoped>
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
  padding: 24px;
  width: 100%;
  max-width: 420px;
}

.modal h3 {
  margin: 0 0 16px 0;
}

.date-options {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.date-option {
  padding: 8px 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  font-size: 14px;
}

.date-option.active {
  background: #4a90d9;
  color: white;
  border-color: #4a90d9;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  color: #666;
}

.date-input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  min-height: 44px;
  font-size: 16px;
  box-sizing: border-box;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  min-height: 44px;
}

.btn-primary { background: #4a90d9; color: white; }
.btn-primary:disabled { background: #ccc; cursor: not-allowed; }
.btn-secondary { background: #e0e0e0; color: #333; }

@media (max-width: 767px) {
  .modal-overlay { padding: 0; align-items: flex-end; }
  .modal { border-radius: 12px 12px 0 0; max-height: 90vh; overflow-y: auto; }
}
</style>
