import axios from "axios";

import { useSessionStore } from "@/stores/session";

export const http = axios.create({
  baseURL: "/api",
  timeout: 120000,
});

/** 避免浏览器/中间层对 API 做 HTTP 缓存，保证列表/详情/筛选与后台数据一致 */
http.interceptors.request.use((config) => {
  const h = (config.headers ||= {}) as Record<string, string>;
  h["Cache-Control"] = "no-store";
  h["Pragma"] = "no-cache";
  return config;
});

http.interceptors.response.use(
  (res) => res,
  (err: unknown) => {
    const ax = err as {
      response?: { status?: number; data?: { message?: string } };
      config?: { url?: string };
      message?: string;
    };
    const status = ax?.response?.status;
    const url = String(ax?.config?.url || "");
    if (status === 401 && url.includes("/mobile/login")) {
      return Promise.reject(new Error("密码错误"));
    }
    if (status === 401 && /\/mobile\//.test(url) && !/\/mobile\/login/.test(url)) {
      try {
        const session = useSessionStore();
        session.logout();
      } catch {
        /* Pinia 未就绪时忽略 */
      }
      void import("@/router").then(({ router }) => {
        if (router.currentRoute.value.meta.requiresAuth) {
          void router.replace({ path: "/" });
        }
      });
    }
    const msg = ax?.response?.data?.message;
    if (typeof msg === "string" && msg.trim()) {
      return Promise.reject(new Error(msg));
    }
    if (ax?.message === "Network Error") {
      return Promise.reject(new Error("网络异常"));
    }
    if (status != null) {
      return Promise.reject(new Error("请求失败"));
    }
    return Promise.reject(err instanceof Error ? err : new Error("请求失败"));
  },
);
