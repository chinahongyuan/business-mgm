import { isMobileSessionInvalidError } from "@/api/sessionEpoch";

/** 弱网：对同一异步操作做有限次重试（指数退避基数）。会话 401 不重试，避免旧口令请求拖过重新登录。 */
export async function withRetries<T>(
  operation: () => Promise<T>,
  opts?: { attempts?: number; baseDelayMs?: number },
): Promise<T> {
  const attempts = Math.max(1, opts?.attempts ?? 3);
  const baseDelayMs = opts?.baseDelayMs ?? 450;
  let lastErr: unknown;
  for (let i = 0; i < attempts; i++) {
    try {
      return await operation();
    } catch (e) {
      lastErr = e;
      if (isMobileSessionInvalidError(e) || i >= attempts - 1) break;
      await new Promise((r) => setTimeout(r, baseDelayMs * (i + 1)));
    }
  }
  throw lastErr instanceof Error ? lastErr : new Error("请求失败");
}
