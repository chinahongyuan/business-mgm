import axios from "axios";

import { BM_TOKEN_KEY } from "@/constants";

export const http = axios.create({
  baseURL: "/api",
  // CMS 富文本、上传等可能较慢；过短易在弱网下表现为 Network Error
  timeout: 120000,
});

http.interceptors.request.use((config) => {
  const token = typeof localStorage !== "undefined" ? localStorage.getItem(BM_TOKEN_KEY) : null;
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (res) => res,
  async (err) => {
    const status = err?.response?.status;
    if (status === 401) {
      if (typeof localStorage !== "undefined") {
        localStorage.removeItem(BM_TOKEN_KEY);
      }
      const loc = typeof window !== "undefined" ? window.location : null;
      const fullPath = loc ? `${loc.pathname || ""}${loc.search || ""}` : "";
      const base = (import.meta.env.BASE_URL || "/").replace(/\/$/, "");
      const loginPath = `${base}/login`;
      if (!fullPath.startsWith(loginPath)) {
        const qs = fullPath ? `?redirect=${encodeURIComponent(fullPath)}` : "";
        window.location.assign(`${loginPath}${qs}`);
      }
    }
    const rawMsg = err?.message;
    const code = (err as { code?: string })?.code;
    if (code === "ECONNABORTED") {
      return Promise.reject(new Error("请求超时，请稍后重试（富文本较大时可能需要更长时间）。"));
    }
    if (rawMsg === "Network Error") {
      return Promise.reject(
        new Error(
          "网络异常：请确认本页与后端同源、后端已启动，且 /api 可访问（开发环境需同时运行 Flask 与前端代理）。",
        ),
      );
    }
    const msg =
      err?.response?.data?.message ||
      err?.response?.data?.error ||
      rawMsg ||
      "请求失败";
    return Promise.reject(new Error(typeof msg === "string" ? msg : JSON.stringify(msg)));
  },
);
