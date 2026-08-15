/** 无限滚动列表：滑动到底自动加载下一页，末尾显示加载中/到底了
 *
 * - pageSize 在 reset() 时快照一次，本次流固定（后端按 offset 分页，中途改 size 会错位）
 * - 内部序号守卫丢弃过期响应（替代各页面手写 loadSeq）
 * - KeepAlive 安全：onMounted/onActivated 幂等绑定滚动监听，onDeactivated/onUnmounted 解绑
 */
import { computed, onActivated, onDeactivated, onMounted, onUnmounted, ref } from 'vue';
import type { ComputedRef, Ref } from 'vue';
import type { PaginatedResponse } from '../types';

export interface UseInfiniteListOptions<T> {
  /** 拉取一页数据，page 从 1 起 */
  fetcher: (page: number, pageSize: number) => Promise<PaginatedResponse<T>>;
  /** 仅在 reset() 时读取一次，作为本次流的固定每页数量 */
  getPageSize: () => number;
  /** 可选去重键（如菜谱 random 排序跨页乱序，按 id 去重） */
  dedupeKey?: (item: T) => string;
  /** 距底部多远触发加载下一页（px） */
  loadMoreThreshold?: number;
  /** 首屏剩余多少内触发补载（px） */
  fillViewportThreshold?: number;
}

export interface UseInfiniteListReturn<T> {
  items: Ref<T[]>;
  total: Ref<number>;
  /** 首屏加载中（列表为空时显示「加载中」） */
  loading: Ref<boolean>;
  /** 追加下一页加载中 */
  loadingMore: Ref<boolean>;
  loadError: Ref<boolean>;
  /** 首屏请求是否已完成（用于空态/首屏失败判断） */
  loaded: Ref<boolean>;
  /** 是否还有下一页：items.length < total */
  hasMore: ComputedRef<boolean>;
  /** 从第 1 页重新加载（清空列表，重拍 pageSize 快照） */
  reset: () => Promise<void>;
  /** 追加下一页（自带重试语义：开头清 loadError） */
  loadMore: () => Promise<void>;
}

const EMPTY_STREAK_LIMIT = 3; // 连续 N 页净增为 0 则视为到底（random 排序防无限补载）

export function useInfiniteList<T>(options: UseInfiniteListOptions<T>): UseInfiniteListReturn<T> {
  const {
    fetcher,
    getPageSize,
    dedupeKey,
    loadMoreThreshold = 100,
    fillViewportThreshold = 200
  } = options;

  const items = ref<T[]>([]) as Ref<T[]>;
  const total = ref(0);
  const loading = ref(false);
  const loadingMore = ref(false);
  const loadError = ref(false);
  const loaded = ref(false);

  const hasMore = computed(() => items.value.length < total.value);

  // 本次流的固定每页数量（reset 时快照）
  let pageSize = 0;
  let nextPage = 1;
  let seq = 0; // reset 时递增，用于丢弃过期响应
  let emptyStreak = 0;

  // ---- 滚动监听（KeepAlive 幂等绑定）----
  let scrollBound = false;

  function onScroll() {
    if (loading.value || loadingMore.value || !hasMore.value || loadError.value) return;
    const scrollBottom = document.documentElement.scrollHeight - window.innerHeight - window.scrollY;
    if (scrollBottom < loadMoreThreshold) {
      loadMore();
    }
  }

  function fillViewportIfNeeded() {
    if (loading.value || loadingMore.value || !hasMore.value || loadError.value) return;
    const remaining = document.documentElement.scrollHeight - window.innerHeight - window.scrollY;
    if (remaining <= fillViewportThreshold) {
      loadMore();
    }
  }

  function ensureBound() {
    if (scrollBound) return;
    window.addEventListener('scroll', onScroll, { passive: true });
    scrollBound = true;
  }

  function ensureUnbound() {
    if (!scrollBound) return;
    window.removeEventListener('scroll', onScroll);
    scrollBound = false;
  }

  async function loadMore(): Promise<void> {
    if (loading.value || loadingMore.value || !hasMore.value) return;
    const mySeq = seq;
    loadingMore.value = true;
    loadError.value = false;
    try {
      const res = await fetcher(nextPage, pageSize);
      if (mySeq !== seq) return; // reset 已发生，丢弃过期响应
      total.value = res.total;
      let fresh: T[] = res.data;
      if (dedupeKey) {
        const seen = new Set(items.value.map(dedupeKey));
        fresh = res.data.filter((item) => !seen.has(dedupeKey(item)));
      }
      items.value.push(...fresh);
      if (res.data.length === 0) {
        // 返回空也视为到底
        total.value = items.value.length;
      } else if (dedupeKey && fresh.length === 0) {
        // random 排序可能整页都是已见过的：连续多页净增为 0 则终止，避免无限补载
        emptyStreak += 1;
        if (emptyStreak >= EMPTY_STREAK_LIMIT) total.value = items.value.length;
      } else {
        emptyStreak = 0;
      }
      nextPage += 1;
    } catch (e) {
      if (mySeq === seq) {
        console.error('加载下一页失败:', e);
        loadError.value = true;
      }
    } finally {
      loadingMore.value = false;
      if (mySeq === seq) fillViewportIfNeeded();
    }
  }

  async function reset(): Promise<void> {
    seq += 1; // 使在途的 reset/loadMore 响应全部过期
    loadingMore.value = false;
    loadError.value = false;
    pageSize = getPageSize();
    nextPage = 1;
    emptyStreak = 0;
    // 不清空现有列表：筛选/增删改后的重载期间保留旧列表，避免闪烁（与改造前行为一致）

    const mySeq = seq;
    loading.value = true;
    try {
      const res = await fetcher(nextPage, pageSize);
      if (mySeq !== seq) return;
      items.value = res.data;
      total.value = res.total;
      nextPage += 1;
    } catch (e) {
      if (mySeq === seq) {
        console.error('加载失败:', e);
        loadError.value = true;
      }
    } finally {
      if (mySeq === seq) {
        loading.value = false;
        loaded.value = true;
        fillViewportIfNeeded();
      }
    }
  }

  onMounted(ensureBound);
  onActivated(() => {
    ensureBound();
    fillViewportIfNeeded();
  });
  onDeactivated(ensureUnbound);
  onUnmounted(ensureUnbound);

  return {
    items,
    total,
    loading,
    loadingMore,
    loadError,
    loaded,
    hasMore,
    reset,
    loadMore
  };
}
