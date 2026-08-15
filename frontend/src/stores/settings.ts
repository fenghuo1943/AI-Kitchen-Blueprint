/** 用户/家庭设置状态管理：每页数量（电脑端/手机端），保存至服务端 */
import { defineStore } from 'pinia';
import { ref } from 'vue';
import { settingsApi } from '../services/api';
import type { UserSettings } from '../types';

const DEFAULT_SETTINGS: UserSettings = {
  page_size_desktop: 30,
  page_size_mobile: 20
};

export const useSettingsStore = defineStore('settings', () => {
  const pageSizeDesktop = ref(DEFAULT_SETTINGS.page_size_desktop);
  const pageSizeMobile = ref(DEFAULT_SETTINGS.page_size_mobile);
  const loaded = ref(false);

  let loadPromise: Promise<void> | null = null;

  /** 确保设置已从服务端加载（并发调用只发一次请求；失败保留默认值，不阻塞列表） */
  function ensureLoaded(): Promise<void> {
    if (loaded.value) return Promise.resolve();
    if (!loadPromise) {
      loadPromise = settingsApi.get()
        .then((res) => {
          pageSizeDesktop.value = res.page_size_desktop;
          pageSizeMobile.value = res.page_size_mobile;
        })
        .catch((e) => {
          console.error('加载设置失败，使用默认值:', e);
        })
        .finally(() => {
          loaded.value = true;
          loadPromise = null;
        });
    }
    return loadPromise;
  }

  /** 更新设置并写回服务端，成功后同步本地 */
  async function update(patch: Partial<UserSettings>): Promise<UserSettings> {
    const res = await settingsApi.update(patch);
    pageSizeDesktop.value = res.page_size_desktop;
    pageSizeMobile.value = res.page_size_mobile;
    loaded.value = true;
    return res;
  }

  /** 按设备取每页数量 */
  function pageSize(isMobile: boolean): number {
    return isMobile ? pageSizeMobile.value : pageSizeDesktop.value;
  }

  return {
    pageSizeDesktop,
    pageSizeMobile,
    loaded,
    ensureLoaded,
    update,
    pageSize
  };
});
