import { defineStore } from "pinia";
import { ref, watch } from "vue";

import { STORAGE_VISITOR_KEY } from "@/constants";

export const useSessionStore = defineStore("session", () => {
  const visitorKey = ref<string>(typeof localStorage !== "undefined" ? localStorage.getItem(STORAGE_VISITOR_KEY) || "" : "");
  /** 登录/退出各加一代。在途请求记下发出时的代际，过期 401 不能清掉更新的登录。 */
  const sessionGeneration = ref(0);

  watch(visitorKey, (v) => {
    if (typeof localStorage === "undefined") return;
    if (v) localStorage.setItem(STORAGE_VISITOR_KEY, v);
    else localStorage.removeItem(STORAGE_VISITOR_KEY);
  });

  function setVisitorKey(key: string) {
    sessionGeneration.value += 1;
    visitorKey.value = key;
  }

  function logout() {
    sessionGeneration.value += 1;
    visitorKey.value = "";
    if (typeof localStorage !== "undefined") {
      localStorage.removeItem(STORAGE_VISITOR_KEY);
    }
  }

  const isLoggedIn = () => Boolean(visitorKey.value && visitorKey.value.length >= 8);

  return { visitorKey, sessionGeneration, setVisitorKey, logout, isLoggedIn };
});
