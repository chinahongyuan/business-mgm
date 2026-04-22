<template>
  <div class="login-root">
    <!-- 背景层：轻量 mesh，避免重绘与 CLS -->
    <div class="login-bg" aria-hidden="true">
      <div class="login-bg__mesh" />
      <div class="login-bg__glow login-bg__glow--a" />
      <div class="login-bg__glow login-bg__glow--b" />
    </div>

    <div class="login-shell">
      <!-- 左侧：品牌区（大屏展示） -->
      <aside class="login-hero" aria-hidden="true">
        <div class="login-hero__inner">
          <div class="login-hero__badge">
            <span class="login-hero__dot" />
            <span>安全访问</span>
          </div>
          <h1 class="login-hero__title">System Management</h1>
          <p class="login-hero__lead">
            帮助你更快完成日常运营与配置。
          </p>
          <ul class="login-hero__bullets">
            <li>账号密码仅用于后台登录</li>
            <li>建议在可信网络环境下访问</li>
          </ul>
        </div>
        <div class="login-hero__art" aria-hidden="true">
          <span class="login-hero__ring" />
          <span class="login-hero__ring login-hero__ring--delay" />
        </div>
      </aside>

      <!-- 右侧：表单 -->
      <main class="login-main">
        <div class="login-card">
          <header class="login-card__head">
            <div class="login-mark" aria-hidden="true">M</div>
            <div class="login-card__titles">
              <h2 id="login-heading" class="login-card__title">欢迎回来</h2>
              <p class="login-card__sub">请使用后台账号登录以继续</p>
            </div>
          </header>

          <el-form
            class="login-form"
            label-position="top"
            aria-labelledby="login-heading"
            @submit.prevent="onSubmit"
          >
            <el-form-item label="账号" required>
              <el-input
                v-model="form.username"
                size="large"
                autocomplete="username"
                placeholder="例如：admin"
                maxlength="64"
              >
                <template #prefix>
                  <el-icon class="login-input-icon"><User /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item label="密码" required>
              <el-input
                v-model="form.password"
                size="large"
                type="password"
                autocomplete="current-password"
                placeholder="请输入密码"
                show-password
              >
                <template #prefix>
                  <el-icon class="login-input-icon"><Lock /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-button
              class="login-submit"
              type="primary"
              size="large"
              native-type="submit"
              :loading="loading"
            >
              {{ loading ? "登录中…" : "登录" }}
            </el-button>
          </el-form>
        </div>

        <p class="login-foot">登录即表示你理解并遵守内部信息安全规范。</p>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Lock, User } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "@/store/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const loading = ref(false);
const form = reactive({
  username: "",
  password: "",
});

async function onSubmit() {
  if (!form.username.trim() || !form.password) {
    ElMessage.warning("请输入账号和密码");
    return;
  }
  loading.value = true;
  try {
    await auth.login(form.username.trim(), form.password);
    const raw = route.query.redirect;
    const redirect = (Array.isArray(raw) ? raw[0] : raw) || "/dashboard";
    await router.replace(redirect);
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "登录失败");
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-root {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  color: #0f172a;
}

.login-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.login-bg__mesh {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(900px 520px at 18% 12%, rgba(37, 99, 235, 0.16), transparent 60%),
    radial-gradient(760px 520px at 88% 18%, rgba(124, 58, 237, 0.14), transparent 58%),
    radial-gradient(700px 520px at 52% 92%, rgba(14, 165, 233, 0.12), transparent 58%),
    linear-gradient(180deg, #f8fafc 0%, #f1f5f9 55%, #eef2ff 100%);
}

.login-bg__glow {
  position: absolute;
  width: 520px;
  height: 520px;
  border-radius: 999px;
  filter: blur(40px);
  opacity: 0.55;
  transform: translateZ(0);
}
.login-bg__glow--a {
  left: -120px;
  top: -160px;
  background: radial-gradient(circle at 30% 30%, rgba(37, 99, 235, 0.35), transparent 62%);
}
.login-bg__glow--b {
  right: -160px;
  bottom: -200px;
  background: radial-gradient(circle at 60% 40%, rgba(124, 58, 237, 0.28), transparent 62%);
}

.login-shell {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr;
}

@media (min-width: 1024px) {
  .login-shell {
    grid-template-columns: minmax(360px, 1.05fr) minmax(420px, 0.95fr);
    align-items: stretch;
  }
}

.login-hero {
  display: none;
  position: relative;
  padding: clamp(28px, 4vw, 44px);
  color: #f8fafc;
  background:
    radial-gradient(900px 520px at 20% 10%, rgba(59, 130, 246, 0.55), transparent 60%),
    radial-gradient(760px 520px at 90% 30%, rgba(124, 58, 237, 0.45), transparent 58%),
    linear-gradient(145deg, #0b1220 0%, #0f172a 48%, #111827 100%);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
}

@media (min-width: 1024px) {
  .login-hero {
    display: flex;
    align-items: stretch;
    justify-content: center;
  }
}

.login-hero__inner {
  width: min(520px, 100%);
  padding: clamp(18px, 2.4vw, 28px) 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.login-hero__badge {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  width: fit-content;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(248, 250, 252, 0.92);
  font-size: 12px;
  letter-spacing: 0.2px;
}

.login-hero__dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: linear-gradient(135deg, #22c55e, #10b981);
  box-shadow: 0 0 0 6px rgba(34, 197, 94, 0.18);
}

.login-hero__title {
  margin: 6px 0 0;
  font-size: clamp(28px, 3.2vw, 40px);
  line-height: 1.12;
  font-weight: 820;
  letter-spacing: -0.02em;
}

.login-hero__lead {
  margin: 0;
  max-width: 46ch;
  font-size: 14px;
  line-height: 1.65;
  color: rgba(226, 232, 240, 0.78);
}

.login-hero__bullets {
  margin: 8px 0 0;
  padding-left: 18px;
  color: rgba(226, 232, 240, 0.72);
  font-size: 13px;
  line-height: 1.75;
}

.login-hero__art {
  position: absolute;
  inset: auto 10% 10% auto;
  width: min(360px, 46vw);
  aspect-ratio: 1;
  pointer-events: none;
  opacity: 0.9;
}

.login-hero__ring {
  position: absolute;
  inset: 0;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  transform: rotate(12deg);
  animation: login-float 9s ease-in-out infinite;
}
.login-hero__ring--delay {
  inset: 10%;
  opacity: 0.55;
  transform: rotate(-8deg);
  animation-delay: -1.2s;
}

@media (prefers-reduced-motion: reduce) {
  .login-hero__ring,
  .login-hero__ring--delay {
    animation: none;
  }
}

@keyframes login-float {
  0%,
  100% {
    transform: rotate(12deg) translateY(0);
  }
  50% {
    transform: rotate(12deg) translateY(-10px);
  }
}

.login-main {
  display: grid;
  place-items: center;
  padding: clamp(18px, 4vw, 34px);
}

.login-card {
  width: min(440px, 100%);
  padding: clamp(22px, 3vw, 30px);
  border-radius: 18px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.86);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.65) inset,
    0 24px 70px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(12px);
  transform: translateZ(0);
  animation: login-rise 420ms ease-out both;
}

@media (prefers-reduced-motion: reduce) {
  .login-card {
    animation: none;
  }
}

@keyframes login-rise {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.login-card__head {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.login-mark {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: #fff;
  font-weight: 900;
  letter-spacing: 0.5px;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  box-shadow: 0 18px 44px rgba(37, 99, 235, 0.28);
  flex: 0 0 auto;
}

.login-card__titles {
  min-width: 0;
}

.login-card__title {
  margin: 0;
  font-size: 22px;
  line-height: 1.2;
  font-weight: 850;
  letter-spacing: -0.01em;
  color: rgba(15, 23, 42, 0.94);
}

.login-card__sub {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.55;
  color: rgba(15, 23, 42, 0.55);
}

.login-form :deep(.el-form-item__label) {
  color: rgba(15, 23, 42, 0.72);
  font-weight: 650;
  font-size: 13px;
  padding-bottom: 6px;
}

.login-form :deep(.el-input__wrapper) {
  border-radius: 14px;
  padding-left: 12px;
  min-height: 46px;
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.08) inset;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 1px rgba(37, 99, 235, 0.35) inset,
    0 0 0 4px rgba(37, 99, 235, 0.12);
}

.login-input-icon {
  color: rgba(15, 23, 42, 0.45);
}

.login-submit {
  width: 100%;
  height: 46px;
  border-radius: 14px;
  margin-top: 6px;
  font-weight: 750;
  letter-spacing: 0.2px;
}

.login-foot {
  margin: 14px 0 0;
  max-width: 440px;
  width: 100%;
  text-align: center;
  font-size: 12px;
  line-height: 1.55;
  color: rgba(15, 23, 42, 0.45);
}

@media (max-width: 1023px) {
  .login-main {
    align-content: center;
  }
}
</style>
