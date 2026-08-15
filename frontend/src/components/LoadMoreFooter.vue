<template>
  <div v-if="show" class="load-more">
    <template v-if="loading">
      <span class="spinner" aria-hidden="true"></span>
      <span class="loading">正在加载...</span>
    </template>
    <template v-else-if="error">
      <span class="error">加载失败</span>
      <button class="btn btn-secondary btn-small" @click="$emit('retry')">点击重试</button>
    </template>
    <template v-else-if="finished">
      <span class="end">—— 全部加载完成 · 到底了 ——</span>
    </template>
    <span v-else class="hint">上拉加载更多</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  /** 是否显示（total > 每页数量，列表确实有多页） */
  show: boolean;
  /** 正在加载下一页 */
  loading: boolean;
  /** 加载下一页失败 */
  error: boolean;
  /** 全部加载完成 */
  finished: boolean;
}>();

defineEmits<{ retry: [] }>();
</script>

<style scoped>
.load-more {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  padding: 20px;
  color: #999;
  font-size: 13px;
}
.loading { color: #4a90d9; display: inline-flex; align-items: center; gap: 8px; }
.error { color: #f44336; display: inline-flex; align-items: center; gap: 8px; }
.end { color: #bbb; }
.hint { color: #ccc; }

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #e0e0e0;
  border-top-color: #4a90d9;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

.btn { padding: 8px 12px; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; min-height: 36px; }
.btn-secondary { background: #f0f0f0; color: #333; }
</style>
