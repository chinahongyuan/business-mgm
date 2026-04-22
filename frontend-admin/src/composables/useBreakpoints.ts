import { onMounted, onUnmounted, ref } from "vue";

/** 与样式中 @media (max-width: 768px) 对齐：窄屏使用抽屉导航 */
export const BM_NARROW_MAX_PX = 768;

function getInitialNarrow(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia(`(max-width: ${BM_NARROW_MAX_PX}px)`).matches;
}

/**
 * 响应式断点（视口宽度，非 UA）。
 * ui-ux-pro-max：以断点驱动布局，避免误判设备类型。
 */
export function useBreakpoints() {
  const isNarrowLayout = ref(getInitialNarrow());
  let mql: MediaQueryList | null = null;

  function onMatchChange() {
    isNarrowLayout.value = mql?.matches ?? getInitialNarrow();
  }

  onMounted(() => {
    mql = window.matchMedia(`(max-width: ${BM_NARROW_MAX_PX}px)`);
    isNarrowLayout.value = mql.matches;
    mql.addEventListener("change", onMatchChange);
  });

  onUnmounted(() => {
    mql?.removeEventListener("change", onMatchChange);
  });

  return { isNarrowLayout, narrowMaxPx: BM_NARROW_MAX_PX };
}
