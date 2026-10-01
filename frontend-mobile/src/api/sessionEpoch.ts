export const MOBILE_SESSION_INVALID = "MOBILE_SESSION_INVALID";

export function isMobileSessionInvalidError(err: unknown): boolean {
  return Boolean(
    err &&
      typeof err === "object" &&
      (err as { code?: unknown }).code === MOBILE_SESSION_INVALID,
  );
}

/**
 * 401 只允许清掉「发出该请求时」的那一代登录。
 * 封面图等慢请求占着连接时，上一轮会话的 401 可能在新登录和公告倒计时之后才返回。
 */
export function shouldInvalidateMobileSession(
  requestGeneration: number | undefined,
  currentGeneration: number,
): boolean {
  return typeof requestGeneration === "number" && requestGeneration === currentGeneration;
}
