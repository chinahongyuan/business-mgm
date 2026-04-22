<template>
  <div class="home">
    <div class="home__bg" aria-hidden="true" />

    <div class="home__inner">
      <header class="home__hero">
        <!-- 显示标题仅用于浏览器标签（document.title），不在此重复展示 -->
        <div v-if="homeHtml" class="home__cms ck-content" v-html="homeHtml" />
        <p v-else class="home__muted">首页内容暂未发布</p>
      </header>

      <section class="home__login">
        <div class="home__loginCard">
          <input
            v-model="password"
            class="home__input"
            type="password"
            autocomplete="off"
            placeholder="请输入密码"
            @keyup.enter="submit"
          />
          <button type="button" class="home__btn" :disabled="loading || !password.trim()" @click="submit">
            <span v-if="loading" class="home__btnSpin" />
            <span>{{ loading ? "验证中…" : "登录" }}</span>
          </button>
          <p v-if="errorMsg" class="home__err">{{ errorMsg }}</p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { http } from "@/api/http";
import { useSessionStore } from "@/stores/session";

const router = useRouter();
const session = useSessionStore();

const homeHtml = ref("");
const password = ref("");
const loading = ref(false);
const errorMsg = ref("");

async function loadHome() {
  try {
    const { data } = await http.get<{ data: { published?: boolean; contentHtml?: string; mobileTitle?: string } }>(
      "/mobile/home-page",
    );
    const d = data?.data;
    if (d?.published && d.contentHtml) {
      homeHtml.value = d.contentHtml;
    }
    const mt = (d?.mobileTitle || "").trim();
    if (mt) {
      document.title = mt;
    } else {
      document.title = "登录";
    }
  } catch {
    document.title = "登录";
  }
}

onMounted(async () => {
  await loadHome();
});

async function submit() {
  errorMsg.value = "";
  const plain = password.value.trim();
  if (!plain) return;
  loading.value = true;
  try {
    const { data } = await http.post<{ data: { visitorKey: string } }>("/mobile/login", {
      password: plain,
      visitorKey: session.visitorKey || undefined,
      ipRegion: "H5",
    });
    const vk = data?.data?.visitorKey;
    if (!vk) {
      errorMsg.value = "登录失败";
      return;
    }
    session.setVisitorKey(vk);
    password.value = "";
    if (typeof sessionStorage !== "undefined") {
      sessionStorage.setItem("bmgm_from_login", Date.now().toString());
    }
    await router.push({ name: "products" });
  } catch (e: unknown) {
    errorMsg.value = e instanceof Error ? e.message : "登录失败";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.home {
  position: relative;
  min-height: 100vh;
  min-height: 100dvh;
  overflow: hidden;
}

.home__bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(100% 70% at 50% -15%, rgba(56, 189, 248, 0.12), transparent 55%),
    radial-gradient(80% 50% at 100% 0%, rgba(167, 139, 250, 0.08), transparent 50%),
    linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
}

.home__inner {
  position: relative;
  z-index: 1;
  max-width: 26rem;
  margin: 0 auto;
  padding: 0.75rem 1rem calc(1.25rem + env(safe-area-inset-bottom, 0px));
}

.home__hero {
  margin-bottom: 1rem;
}

.home__cms {
  padding: 1rem 1.05rem;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.22);
  backdrop-filter: blur(8px);
  box-shadow: 0 4px 24px rgba(15, 23, 42, 0.06);
  font-size: 0.9375rem;
  line-height: 1.55;
  color: #334155;
}

.home__cms :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
}

.home__muted {
  margin: 0;
  font-size: 0.875rem;
  color: #64748b;
}

.home__hint {
  margin: 12px 0 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: #64748b;
  text-align: center;
}

.home__login {
  margin-top: 0.25rem;
}

.home__loginCard {
  padding: 1.1rem 1rem;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(148, 163, 184, 0.22);
  backdrop-filter: blur(8px);
  box-shadow: 0 4px 24px rgba(15, 23, 42, 0.07);
}

.home__input {
  width: 100%;
  box-sizing: border-box;
  padding: 14px 16px;
  margin-bottom: 12px;
  font-size: 1rem;
  text-align: center;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 12px;
  background: #fff;
  color: #0f172a;
}

.home__input::placeholder {
  color: #94a3b8;
  text-align: center;
}

.home__input:focus {
  outline: none;
  border-color: #38bdf8;
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2);
}

.home__btn {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 16px;
  border: none;
  border-radius: 12px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  color: #fff;
  background: linear-gradient(120deg, #0ea5e9 0%, #0284c7 50%, #6366f1 100%);
  box-shadow: 0 6px 20px rgba(14, 165, 233, 0.28);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.home__btn:active:not(:disabled) {
  transform: scale(0.98);
}

.home__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.home__btnSpin {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.45);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.home__err {
  margin: 10px 0 0;
  font-size: 0.8125rem;
  color: #dc2626;
}

/* 宽屏：单列纵向；高度与 App.vue app-shell 上下留白对齐，避免整页再叠一层 100dvh 出现浏览器右侧滚动条 */
@media (min-width: 1024px) {
  .home {
    /* app-shell: padding-top 12px + padding-bottom 28px（border-box 内已含） */
    height: calc(100dvh - 40px);
    max-height: calc(100dvh - 40px);
    min-height: 0;
    overflow: hidden;
  }

  .home__inner {
    max-width: none;
    width: 100%;
    height: 100%;
    max-height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: 1.25rem;
    padding-bottom: calc(1.75rem + env(safe-area-inset-bottom, 0px));
    gap: 0;
    box-sizing: border-box;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
  }

  .home__hero {
    width: 100%;
    max-width: min(52rem, 100%);
    margin-bottom: 1.75rem;
    min-width: 0;
  }

  .home__cms {
    padding: 1.15rem 1.25rem;
    border-radius: 16px;
    font-size: 0.96875rem;
  }

  .home__login {
    width: 100%;
    max-width: 440px;
    margin-top: 0;
    min-width: 0;
  }

  .home__loginCard {
    border-radius: 18px;
    box-shadow:
      0 1px 0 rgba(255, 255, 255, 0.9) inset,
      0 12px 40px rgba(15, 23, 42, 0.08);
  }
}

@media (min-width: 1024px) and (prefers-reduced-motion: no-preference) {
  .home__btn:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 8px 26px rgba(14, 165, 233, 0.32);
  }
}
</style>
