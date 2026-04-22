import { defineStore } from "pinia";
import { ref, watch } from "vue";

import { STORAGE_VISITOR_KEY } from "@/constants";

export const useSessionStore = defineStore("session", () => {
  const visitorKey = ref<string>(typeof localStorage !== "undefined" ? localStorage.getItem(STORAGE_VISITOR_KEY) || "" : "");

  watch(visitorKey, (v) => {
    if (typeof localStorage === "undefined") return;
    if (v) localStorage.setItem(STORAGE_VISITOR_KEY, v);
    else localStorage.removeItem(STORAGE_VISITOR_KEY);
  });

  function setVisitorKey(key: string) {
    visitorKey.value = key;
  }

  function logout() {
    visitorKey.value = "";
    if (typeof localStorage !== "undefined") {
      localStorage.removeItem(STORAGE_VISITOR_KEY);
    }
  }

  const isLoggedIn = () => Boolean(visitorKey.value && visitorKey.value.length >= 8);

  return { visitorKey, setVisitorKey, logout, isLoggedIn };
});
