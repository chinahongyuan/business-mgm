import { defineStore } from "pinia";

import { http } from "@/api/http";
import { BM_TOKEN_KEY } from "@/constants";
import type { MenuNode } from "@/types/menu";

export type AuthUser = { id: number; username: string };

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: (typeof localStorage !== "undefined" && localStorage.getItem(BM_TOKEN_KEY)) || "",
    user: null as AuthUser | null,
    menus: [] as MenuNode[],
  }),
  actions: {
    clearSession() {
      this.token = "";
      this.user = null;
      this.menus = [];
      localStorage.removeItem(BM_TOKEN_KEY);
    },
    setToken(token: string) {
      this.token = token;
      localStorage.setItem(BM_TOKEN_KEY, token);
    },
    async login(username: string, password: string) {
      const { data } = await http.post("/auth/login", { username, password });
      const payload = data?.data;
      if (!payload?.token) throw new Error("登录响应无效");
      this.setToken(payload.token);
      this.user = payload.user;
      this.menus = payload.menus || [];
    },
    async fetchMe() {
      const { data } = await http.get("/auth/me");
      const payload = data?.data;
      this.user = payload?.user || null;
      this.menus = payload?.menus || [];
    },
    logout() {
      this.clearSession();
    },
  },
});
