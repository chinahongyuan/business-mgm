import axios, { type InternalAxiosRequestConfig } from "axios";

import { MOBILE_SESSION_INVALID, shouldInvalidateMobileSession } from "@/api/sessionEpoch";
import { useSessionStore } from "@/stores/session";

type SessionConfig = InternalAxiosRequestConfig & { sessionGeneration?: number };

export const http = axios.create({
  baseURL: "/api",
  timeout: 120000,
});

/** 避免浏览器/中间层对 API 做 HTTP 缓存，保证列表/详情/筛选与后台数据一致 */
http.interceptors.request.use((config) => {
  const h = (config.headers ||= {}) as Record<string, string>;
  h["Cache-Control"] = "no-store";
  h["Pragma"] = "no-cache";
  try {
    (config as SessionConfig).sessionGeneration = useSessionStore().sessionGeneration;
  } catch {
    /* Pinia 未就绪时忽略 */
  }
  return config;
});

function rejectSessionInvalid(message: string): Promise<never> {
  const err = new Error(message);
  (err as Error & { code: string }).code = MOBILE_SESSION_INVALID;
  return Promise.reject(err);
}

http.interceptors.response.use(
  (res) => res,
  (err: unknown) => {
    const ax = err as {
      response?: { status?: number; data?: { code?: string; message?: string } };
      config?: SessionConfig;
      message?: string;
    };
    const status = ax?.response?.status;
    const url = String(ax?.config?.url || "");
    if (status === 401 && url.includes("/mobile/login")) {
      return Promise.reject(new Error("密码错误"));
    }
    if (
      status === 401 &&
      ax?.response?.data?.code === MOBILE_SESSION_INVALID &&
      /\/mobile\//.test(url) &&
      !/\/mobile\/login/.test(url)
    ) {
      const rawMessage = ax.response?.data?.message;
      const message =
        typeof rawMessage === "string" && rawMessage.trim() ? rawMessage.trim() : "登录已失效，请重新登录";
      try {
        const session = useSessionStore();
        if (shouldInvalidateMobileSession(ax.config?.sessionGeneration, session.sessionGeneration)) {
          session.logout();
          if (typeof sessionStorage !== "undefined") {
            sessionStorage.clear();
          }
          void import("@/router").then(({ router }) => {
            if (router.currentRoute.value.meta.requiresAuth) {
              void router.replace({ path: "/" });
            }
          });
        }
      } catch {
        /* Pinia 未就绪时忽略 */
      }
      return rejectSessionInvalid(message);
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
