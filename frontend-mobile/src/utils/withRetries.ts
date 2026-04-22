/** 弱网：对同一异步操作做有限次重试（指数退避基数）。 */
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
      if (i < attempts - 1) {
        await new Promise((r) => setTimeout(r, baseDelayMs * (i + 1)));
      }
    }
  }
  throw lastErr instanceof Error ? lastErr : new Error("请求失败");
}
