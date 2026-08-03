import { ref, computed, onMounted, onUnmounted } from 'vue';

// 断点定义
const BREAKPOINTS = {
  mobile: 768,
  tablet: 1024,
};

export function useResponsive() {
  const windowWidth = ref(window.innerWidth);

  // 响应式状态
  const isMobile = computed(() => windowWidth.value < BREAKPOINTS.mobile);
  const isTablet = computed(() =>
    windowWidth.value >= BREAKPOINTS.mobile &&
    windowWidth.value < BREAKPOINTS.tablet
  );
  const isDesktop = computed(() => windowWidth.value >= BREAKPOINTS.tablet);

  // 更新窗口宽度
  function updateWidth() {
    windowWidth.value = window.innerWidth;
  }

  // 监听窗口大小变化
  onMounted(() => {
    window.addEventListener('resize', updateWidth);
    updateWidth();
  });

  onUnmounted(() => {
    window.removeEventListener('resize', updateWidth);
  });

  return {
    windowWidth,
    isMobile,
    isTablet,
    isDesktop,
    BREAKPOINTS,
  };
}

// 媒体查询工具函数
export function useMediaQuery(query: string) {
  const matches = ref(false);

  function updateMatches() {
    matches.value = window.matchMedia(query).matches;
  }

  onMounted(() => {
    updateMatches();
    window.matchMedia(query).addEventListener('change', updateMatches);
  });

  onUnmounted(() => {
    window.matchMedia(query).removeEventListener('change', updateMatches);
  });

  return matches;
}
