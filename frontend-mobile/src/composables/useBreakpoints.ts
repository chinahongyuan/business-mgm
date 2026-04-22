import { onMounted, onUnmounted, ref } from "vue";

/**
 * 与管理后台一致：以视口宽度断点驱动布局（非 UA）。
 * 与 `base.css` / `App.vue` 中 `@media (min-width: 1024px)` 对齐。
 */
export const MWEB_DESKTOP_MIN_PX = 1024;

function getInitialDesktop(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia(`(min-width: ${MWEB_DESKTOP_MIN_PX}px)`).matches;
}

export function useBreakpoints() {
  const isDesktopLayout = ref(getInitialDesktop());
  let mql: MediaQueryList | null = null;

  function onMatchChange() {
    isDesktopLayout.value = mql?.matches ?? getInitialDesktop();
  }

  onMounted(() => {
    mql = window.matchMedia(`(min-width: ${MWEB_DESKTOP_MIN_PX}px)`);
    isDesktopLayout.value = mql.matches;
    mql.addEventListener("change", onMatchChange);
  });

  onUnmounted(() => {
    mql?.removeEventListener("change", onMatchChange);
  });

  return { isDesktopLayout, desktopMinPx: MWEB_DESKTOP_MIN_PX };
}
