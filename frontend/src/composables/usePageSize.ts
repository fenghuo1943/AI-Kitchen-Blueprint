/** 按当前设备（电脑/手机）解析每页数量，来自服务端设置 */
import { computed } from 'vue';
import { useResponsive } from './useResponsive';
import { useSettingsStore } from '../stores/settings';

export function usePageSize() {
  const { isMobile } = useResponsive();
  const settingsStore = useSettingsStore();

  // 共享的加载 promise：视图首次 reset 前 await 它，确保取到的每页数量是服务端值
  const ready = settingsStore.ensureLoaded();
  const pageSize = computed(() => settingsStore.pageSize(isMobile.value));

  return { pageSize, ready, isMobile };
}
