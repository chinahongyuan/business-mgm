import { defineStore } from "pinia";
import { ref } from "vue";

const STORAGE_KEY = "bm-theme";

export type ThemeMode = "light" | "dark";

export const useThemeStore = defineStore("theme", () => {
  const isDark = ref(false);

  function apply() {
    const html = document.documentElement;
    if (isDark.value) {
      html.classList.add("dark");
      html.style.colorScheme = "dark";
    } else {
      html.classList.remove("dark");
      html.style.colorScheme = "light";
    }
  }

  function setDark(value: boolean) {
    isDark.value = value;
    try {
      localStorage.setItem(STORAGE_KEY, value ? "dark" : "light");
    } catch {
      /* 隐私模式等可能无法写入，仍应用当前页主题 */
    }
    apply();
  }

  function toggle() {
    setDark(!isDark.value);
  }

  /**
   * 应用启动时调用：默认暗色；若 localStorage 中有 bm-theme=light 则使用明亮。
   * 与 index.html 内联脚本一致，避免首屏闪烁。
   */
  function init() {
    let saved: string | null = null;
    try {
      saved = localStorage.getItem(STORAGE_KEY);
    } catch {
      saved = null;
    }
    isDark.value = saved !== "light";
    apply();
  }

  return { isDark, setDark, toggle, init };
});
