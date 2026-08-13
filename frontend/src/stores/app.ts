/** 应用状态管理 */
import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useAppStore = defineStore('app', () => {
  // 加载状态
  const loading = ref(false);

  // 错误信息
  const error = ref<string | null>(null);

  // 菜谱数据版本：菜谱增删改后递增，供缓存的菜谱库页面判断返回时是否需要重新拉取
  const recipeVersion = ref(0);

  // source：版本递增的来源（create/update/publish/...），便于在控制台追踪版本号变化链路
  function bumpRecipeVersion(source?: string) {
    const old = recipeVersion.value;
    recipeVersion.value += 1;
    console.log(`[recipeVersion] 递增 ${old} → ${recipeVersion.value}（来源: ${source ?? 'unknown'}）`);
  }

  // 清除错误
  function clearError() {
    error.value = null;
  }

  return {
    loading,
    error,
    recipeVersion,
    bumpRecipeVersion,
    clearError
  };
});
