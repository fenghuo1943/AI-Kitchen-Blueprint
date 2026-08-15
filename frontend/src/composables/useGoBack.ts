import { useRouter } from 'vue-router';

/** 返回上一页；无历史记录（如直接打开 URL 或刷新进入页面）时回退到指定页面，避免返回时退出应用 */
export function useGoBack(fallback = '/recipes') {
  const router = useRouter();

  function goBack() {
    // vue-router 会把上一页地址写入 history.state.back，无历史时为 null
    if (window.history.state?.back) {
      router.back();
    } else {
      router.push(fallback);
    }
  }

  return { goBack };
}
