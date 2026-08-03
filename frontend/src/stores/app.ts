/** 应用状态管理 */
import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useAppStore = defineStore('app', () => {
  // 当前家庭 ID
  const currentHouseholdId = ref<string | null>(null);

  // 加载状态
  const loading = ref(false);

  // 错误信息
  const error = ref<string | null>(null);

  // 设置当前家庭
  function setHousehold(id: string) {
    currentHouseholdId.value = id;
    localStorage.setItem('householdId', id);
  }

  // 初始化
  function init() {
    const savedId = localStorage.getItem('householdId');
    if (savedId) {
      currentHouseholdId.value = savedId;
    }
  }

  // 清除错误
  function clearError() {
    error.value = null;
  }

  return {
    currentHouseholdId,
    loading,
    error,
    setHousehold,
    init,
    clearError
  };
});
