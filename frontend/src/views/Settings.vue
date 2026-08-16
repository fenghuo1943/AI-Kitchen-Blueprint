<template>
  <div class="settings">
    <div class="header">
      <div class="header-left">
        <button @click="goBack" class="btn-back" aria-label="返回">返回</button>
        <h1>设置</h1>
      </div>
      <button @click="save" class="btn btn-primary" :disabled="saving">保存</button>
    </div>

    <div class="settings-card">
      <h2>列表每页数量</h2>
      <p class="desc">作用于菜谱库、收藏、历史等列表页的「无限滚动」分页，保存后对新加载的列表生效。</p>

      <div class="form-group">
        <label>电脑端每页数量</label>
        <input
          v-model.number="desktop"
          type="number"
          min="5"
          max="100"
          placeholder="30"
        />
      </div>

      <div class="form-group">
        <label>手机端每页数量</label>
        <input
          v-model.number="mobile"
          type="number"
          min="5"
          max="100"
          placeholder="20"
        />
      </div>

      <p class="device-hint">当前设备：{{ isMobile ? '手机端' : '电脑端' }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useGoBack } from '../composables/useGoBack';
import { useResponsive } from '../composables/useResponsive';
import { useSettingsStore } from '../stores/settings';
import { toast } from '../composables/useToast';

const { goBack } = useGoBack('/me');
const { isMobile } = useResponsive();
const settings = useSettingsStore();

const desktop = ref(30);
const mobile = ref(20);
const saving = ref(false);

function clamp(n: number): number {
  const v = Math.round(Number.isFinite(n) ? n : 0);
  return Math.min(100, Math.max(5, v));
}

onMounted(async () => {
  await settings.ensureLoaded();
  desktop.value = settings.pageSizeDesktop;
  mobile.value = settings.pageSizeMobile;
});

async function save() {
  saving.value = true;
  try {
    await settings.update({
      page_size_desktop: clamp(desktop.value),
      page_size_mobile: clamp(mobile.value)
    });
    toast('设置已保存');
    goBack();
  } catch (e) {
    console.error('保存设置失败:', e);
    toast('保存失败，请重试', 'error');
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.settings { padding: 0 20px 20px; }

.header {
  position: sticky;
  top: var(--navbar-height, 64px);
  z-index: 150;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 16px 0;
  margin-bottom: 20px;
  background: #f5f5f5;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.header-left { display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1; }
.header h1 { margin: 0; font-size: 1.3rem; }

.btn-back {
  height: 36px; padding: 0 12px;
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent; border: 1px solid #0784ff; border-radius: 8px; cursor: pointer; flex-shrink: 0;
  color: #0784ff; font-size: 14px; font-weight: 500;
}
.btn-back:hover { background: rgba(7, 132, 255, 0.08); }

.settings-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.settings-card h2 { margin: 0 0 8px; font-size: 1.1rem; }
.desc { margin: 0 0 20px; font-size: 13px; color: #888; }

.form-group { margin-bottom: 20px; }
.form-group label { display: block; margin-bottom: 8px; font-size: 14px; color: #555; }
.form-group input {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  box-sizing: border-box;
  min-height: 44px;
}
.form-group input:focus { outline: none; border-color: #4a90d9; }

.device-hint { margin: 0; font-size: 13px; color: #999; }

.btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; min-height: 44px; }
.btn-primary { background: #4a90d9; color: white; }
.btn-primary:hover { background: #357abd; }
.btn:disabled { opacity: 0.6; cursor: not-allowed; }

@media (max-width: 767px) {
  .settings { padding: 0 16px 16px; }
  .header { padding: 14px 0; }
}
</style>
