<template>
  <div class="pd">
    <div class="pd__bg" aria-hidden="true" />

    <div class="pd__inner">
      <header class="pd__bar">
        <button type="button" class="pd__back" @click="goBack">← 返回</button>
      </header>

      <div v-if="loading" class="pd__loading">
        <span class="pd__spinner" />
        加载中…
      </div>

      <template v-else-if="detail">
        <section class="pd__surface pd__surface--hero" :class="detail.status === 'on' ? 'pd__surface--on' : 'pd__surface--off'">
          <h1 class="pd__title">{{ detail.name }}</h1>
          <div class="pd__row">
            <span class="pd__status" :class="detail.status === 'on' ? 'pd__status--on' : 'pd__status--off'">
              {{ detail.status === "on" ? "在岗" : "休息" }}
            </span>
            <div class="pd__priceBlock" aria-label="价格">
              <span class="pd__priceYuan">¥</span>
              <span class="pd__priceInt">{{ priceParts(detail.price).int }}</span>
              <span class="pd__priceFrac">.{{ priceParts(detail.price).frac }}</span>
            </div>
            <StarRating v-if="(detail.starRating ?? 0) > 0" :rating="detail.starRating" />
          </div>
          <p class="pd__addr">
            <MobileIcon name="mapPin" size="sm" class="pd__addrIcon" />
            <span>{{ detail.address || "—" }}</span>
          </p>
          <div v-if="detail.tagNames?.length" class="pd__tags">
            <span v-for="t in detail.tagNames" :key="t" class="tagpill">{{ t }}</span>
          </div>
          <div class="pd__flags">
            <span v-if="detail.hasHotReview" class="badge badge--review">
              <MobileIcon name="chatFill" size="xs" class="badge__ico" />
              <span>热评</span>
            </span>
            <span v-if="detail.hot" class="badge badge--hot">
              <MobileIcon name="fireFill" size="xs" class="badge__ico" />
              <span>热门</span>
            </span>
            <span v-if="detail.recommend" class="badge badge--rec">
              <MobileIcon name="starFill" size="xs" class="badge__ico" />
              <span>推荐</span>
            </span>
          </div>
        </section>

        <section class="pd__surface pd__surface--block">
          <div class="pd__blockHead">
            <span class="pd__dot pd__dot--sky" aria-hidden="true" />
            <span class="pd__blockTitle">商品详情</span>
          </div>
          <div ref="htmlRoot" class="pd__html ck-content" v-html="safeHtml" />
        </section>

        <section class="pd__surface pd__surface--block">
          <div class="pd__blockHead">
            <span class="pd__dot pd__dot--violet" aria-hidden="true" />
            <span class="pd__blockTitle">用户评价</span>
            <span v-if="reviews.length" class="pd__reviewCount">{{ reviews.length }} 条</span>
          </div>

          <div v-if="reviewsLoading" class="pd__reviewsHint">加载评价中…</div>
          <div v-else-if="!reviews.length" class="pd__reviewsEmpty">暂无评价，欢迎发表第一条～</div>
          <ul v-else class="pd__reviewList">
            <li v-for="r in reviews" :key="r.id" class="pd__review">
              <div class="pd__reviewAvatar" aria-hidden="true">
                <svg class="pd__reviewAvatarSvg" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="20" cy="20" r="20" fill="#e0f2fe" />
                  <circle cx="20" cy="16" r="5" fill="#0284c7" />
                  <path
                    d="M8 33c2.2-5.2 5.5-8 12-8s9.8 2.8 12 8"
                    stroke="#0284c7"
                    stroke-width="2"
                    stroke-linecap="round"
                    fill="none"
                  />
                </svg>
              </div>
              <div class="pd__reviewMain">
                <div class="pd__reviewMeta">
                  <span class="pd__reviewName">{{ r.displayName }}</span>
                  <time class="pd__reviewTime" :datetime="r.createdAt">{{ formatDateTimeZh(r.createdAt) }}</time>
                </div>
                <p class="pd__reviewText">{{ r.content }}</p>
              </div>
            </li>
          </ul>

          <div class="pd__compose">
            <label class="pd__composeLabel" for="pd-review-input">写评价</label>
            <textarea
              id="pd-review-input"
              v-model="reviewDraft"
              class="pd__textarea"
              rows="4"
              maxlength="2000"
              placeholder="提交后需管理员审核通过方可展示"
              :disabled="submitting"
            />
            <p v-if="submitTip" class="pd__submitTip" :class="{ 'pd__submitTip--ok': submitOk }">{{ submitTip }}</p>
            <button
              type="button"
              class="pd__submitBtn"
              :disabled="submitting || !reviewDraft.trim()"
              @click="submitReview"
            >
              <span v-if="submitting" class="pd__btnSpin" />
              {{ submitting ? "提交中…" : "提交评价" }}
            </button>
          </div>
        </section>
      </template>

      <div v-else class="pd__empty">商品不存在或已下架</div>
    </div>

    <Teleport to="body">
      <div
        v-if="lightboxSrc"
        class="pd-lightbox"
        role="dialog"
        aria-modal="true"
        aria-label="图片预览"
        @click.self="closeLightbox"
      >
        <button type="button" class="pd-lightbox__close" aria-label="关闭" @click="closeLightbox">×</button>
        <img class="pd-lightbox__img" :src="lightboxSrc" alt="" @click.stop />
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { onBeforeRouteLeave, useRoute, useRouter } from "vue-router";

import { http } from "@/api/http";
import MobileIcon from "@/components/MobileIcon.vue";
import StarRating from "@/components/StarRating.vue";
import { useSessionStore } from "@/stores/session";
import { attachDetailImageClicks, attachExclusiveVideoPlayback, enhanceDetailHtml } from "@/utils/detailHtml";
import { formatDateTimeZh } from "@/utils/formatDateTime";

const route = useRoute();
const router = useRouter();
const session = useSessionStore();

const loading = ref(true);
const htmlRoot = ref<HTMLElement | null>(null);
let detachDetailMedia: () => void = () => {};

const lightboxSrc = ref("");

function openLightbox(url: string) {
  const u = (url || "").trim();
  if (!u) return;
  lightboxSrc.value = u;
}

function closeLightbox() {
  lightboxSrc.value = "";
}

function onLightboxKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") {
    closeLightbox();
  }
}

const mobileTitle = ref("");

const detail = ref<{
  id: number;
  name: string;
  coverImage?: string | null;
  status: string;
  price: number;
  starRating: number;
  address?: string | null;
  tagNames?: string[];
  hasHotReview?: boolean;
  hot?: boolean;
  recommend?: boolean;
  detailHtml?: string;
} | null>(null);

type ReviewRow = { id: number; content: string; displayName: string; createdAt: string };
const reviews = ref<ReviewRow[]>([]);
const reviewsLoading = ref(false);
const reviewDraft = ref("");
const submitting = ref(false);
const submitTip = ref("");
const submitOk = ref(false);

const safeHtml = computed(() => enhanceDetailHtml(detail.value?.detailHtml || ""));

function priceParts(n: number) {
  const s = Number(n).toFixed(2);
  const [a, b] = s.split(".");
  return { int: a, frac: b || "00" };
}

function applyDocumentTitle() {
  const name = (detail.value?.name || "").trim();
  const mt = mobileTitle.value.trim();
  if (name && mt) {
    document.title = `${mt} · ${name}`;
  } else if (name) {
    document.title = name;
  } else {
    document.title = mobileTitle.value.trim() || "商品详情";
  }
}

watch(
  safeHtml,
  async () => {
    await nextTick();
    detachDetailMedia();
    detachDetailMedia = () => {};
    if (htmlRoot.value && safeHtml.value) {
      const d1 = attachExclusiveVideoPlayback(htmlRoot.value);
      const d2 = attachDetailImageClicks(htmlRoot.value, (url) => openLightbox(url));
      detachDetailMedia = () => {
        d1();
        d2();
      };
    }
  },
  { flush: "post" },
);

watch(lightboxSrc, (src) => {
  if (typeof document === "undefined") return;
  if (src) {
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", onLightboxKeydown);
  } else {
    document.body.style.overflow = "";
    document.removeEventListener("keydown", onLightboxKeydown);
  }
});

watch([() => detail.value?.name, mobileTitle], () => applyDocumentTitle());

function goBack() {
  void router.push({ name: "products" });
}

onBeforeRouteLeave((to) => {
  if (to.name === "products" && typeof sessionStorage !== "undefined") {
    sessionStorage.setItem("bmgm_skip_list_ann", "1");
  }
});

async function loadProductPage(productId: number) {
  loading.value = true;
  detail.value = null;
  reviews.value = [];
  submitTip.value = "";
  document.title = mobileTitle.value.trim() || "商品详情";

  try {
    const [homeRes, detailRes] = await Promise.all([
      http.get<{ data: { mobileTitle?: string } }>("/mobile/home-page").catch(() => ({ data: {} })),
      http.get<{
        data: {
          id: number;
          name: string;
          coverImage?: string | null;
          status: string;
          price: number;
          starRating: number;
          address?: string | null;
          tagNames?: string[];
          hasHotReview?: boolean;
          hot?: boolean;
          recommend?: boolean;
          detailHtml?: string;
        };
      }>(`/mobile/products/${productId}`, { params: { visitorKey: session.visitorKey } }),
    ]);

    const mt = (homeRes.data?.data?.mobileTitle || "").trim();
    mobileTitle.value = mt;

    const d = detailRes.data?.data;
    if (!d) {
      detail.value = null;
      return;
    }
    detail.value = d;
    applyDocumentTitle();

    reviewsLoading.value = true;
    try {
      const msgRes = await http.get<{ data: { items: ReviewRow[] } }>(`/mobile/products/${productId}/messages`);
      const items = msgRes.data?.data?.items || [];
      reviews.value = items.map((it) => ({
        id: it.id,
        content: it.content,
        displayName: it.displayName || `游客${String(it.id % 10000).padStart(4, "0")}`,
        createdAt: it.createdAt,
      }));
    } catch {
      reviews.value = [];
    } finally {
      reviewsLoading.value = false;
    }
  } catch {
    detail.value = null;
  } finally {
    loading.value = false;
  }
}

async function submitReview() {
  const pid = detail.value?.id;
  if (!pid || !session.visitorKey) return;
  const content = reviewDraft.value.trim();
  if (!content) return;
  submitting.value = true;
  submitTip.value = "";
  submitOk.value = false;
  try {
    await http.post("/mobile/product-messages", {
      visitorKey: session.visitorKey,
      productId: pid,
      content,
      ipRegion: "H5",
    });
    reviewDraft.value = "";
    submitOk.value = true;
    submitTip.value = "提交成功，审核通过后将公开展示";
  } catch (e: unknown) {
    submitTip.value = e instanceof Error ? e.message : "提交失败";
  } finally {
    submitting.value = false;
  }
}

watch(
  () => route.params.id,
  (id) => {
    const num = Number(id);
    if (!Number.isFinite(num)) return;
    void loadProductPage(num);
  },
);

onMounted(async () => {
  const id = Number(route.params.id);
  if (!Number.isFinite(id)) {
    void router.replace({ name: "products" });
    return;
  }
  await loadProductPage(id);
});

onUnmounted(() => {
  detachDetailMedia();
  lightboxSrc.value = "";
  if (typeof document !== "undefined") {
    document.body.style.overflow = "";
    document.removeEventListener("keydown", onLightboxKeydown);
  }
});
</script>

<style scoped>
.pd {
  position: relative;
  min-height: 100vh;
  min-height: 100dvh;
  padding-bottom: calc(28px + env(safe-area-inset-bottom, 0px));
}

/* 与商品列表页 plist__bg 一致 */
.pd__bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(120% 70% at 85% 0%, rgba(99, 102, 241, 0.12), transparent 50%),
    radial-gradient(100% 55% at 10% 15%, rgba(14, 165, 233, 0.14), transparent 48%),
    radial-gradient(80% 40% at 50% 100%, rgba(244, 114, 182, 0.06), transparent 45%),
    linear-gradient(165deg, #f0f9ff 0%, #f8fafc 38%, #f1f5f9 100%);
}

.pd__inner {
  position: relative;
  z-index: 1;
  max-width: 32rem;
  margin: 0 auto;
  padding: 0 0.9rem;
}

.pd__bar {
  position: sticky;
  top: 0;
  z-index: 5;
  margin: 0 -0.9rem;
  padding: 10px 0.9rem env(safe-area-inset-top, 10px);
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
}

.pd__back {
  border: none;
  background: none;
  color: #0284c7;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  touch-action: manipulation;
}

.pd__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 3rem 1rem;
  color: #64748b;
}

.pd__spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(148, 163, 184, 0.45);
  border-top-color: #0284c7;
  border-radius: 50%;
  animation: spin 0.65s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.pd__surface {
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.99) 0%, rgba(248, 250, 252, 0.96) 100%);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.95) inset,
    0 10px 32px rgba(15, 23, 42, 0.07);
  margin-bottom: 12px;
  overflow: hidden;
}

.pd__surface--hero {
  padding: 18px 14px 15px;
  margin-top: 2px;
}

.pd__surface--on {
  border-color: rgba(34, 197, 94, 0.42);
  box-shadow:
    0 0 0 2px rgba(34, 197, 94, 0.28),
    0 1px 0 rgba(255, 255, 255, 0.95) inset,
    0 12px 32px rgba(34, 197, 94, 0.12);
}

.pd__surface--off {
  border-color: rgba(148, 163, 184, 0.45);
  box-shadow:
    0 0 0 2px rgba(148, 163, 184, 0.2),
    0 8px 24px rgba(15, 23, 42, 0.06);
}

.pd__surface--block {
  padding: 0;
}

.pd__blockHead {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px 8px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.95) 0%, rgba(255, 255, 255, 0.5) 100%);
}

.pd__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.pd__dot--sky {
  background: #0ea5e9;
}

.pd__dot--violet {
  background: #8b5cf6;
}

.pd__blockTitle {
  font-size: 0.8125rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: 0.02em;
}

.pd__reviewCount {
  margin-left: auto;
  font-size: 0.6875rem;
  font-weight: 600;
  color: #64748b;
}

.pd__title {
  margin: 0 0 10px;
  font-size: 1.125rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.35;
}

.pd__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.pd__row :deep(.star-rating) {
  vertical-align: middle;
}

.pd__status {
  font-size: 0.65rem;
  font-weight: 800;
  padding: 3px 8px;
  border-radius: 6px;
  letter-spacing: 0.02em;
}

.pd__status--on {
  background: rgba(34, 197, 94, 0.15);
  color: #15803d;
}

.pd__status--off {
  background: rgba(148, 163, 184, 0.2);
  color: #64748b;
}

.pd__priceBlock {
  display: inline-flex;
  flex-direction: row;
  align-items: baseline;
  gap: 0;
  line-height: 1.15;
}

.pd__priceYuan {
  font-size: 0.8125rem;
  font-weight: 700;
  color: #dc2626;
  margin-right: 1px;
}

.pd__priceInt {
  font-size: 1.25rem;
  font-weight: 800;
  color: #b91c1c;
  letter-spacing: -0.02em;
}

.pd__priceFrac {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #dc2626;
}

.pd__addr {
  margin: 0 0 10px;
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 0.8125rem;
  color: #64748b;
  line-height: 1.5;
}

.pd__addrIcon {
  color: #0ea5e9;
  flex-shrink: 0;
  margin-top: 2px;
}

.pd__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.tagpill {
  font-size: 0.75rem;
  padding: 4px 8px;
  border-radius: 6px;
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #e2e8f0;
}

.pd__flags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.625rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  line-height: 1;
  padding: 5px 9px 5px 7px;
  border-radius: 999px;
  border: 1px solid transparent;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.08);
}

.badge__ico {
  flex-shrink: 0;
}

.badge--review {
  color: #fff;
  background: linear-gradient(135deg, #fb7185 0%, #e11d48 55%, #be123c 100%);
  border-color: rgba(255, 255, 255, 0.35);
  text-shadow: 0 1px 0 rgba(0, 0, 0, 0.12);
}

.badge--review .badge__ico {
  opacity: 0.95;
}

.badge--hot {
  color: #fff;
  background: linear-gradient(135deg, #fbbf24 0%, #f97316 45%, #ea580c 100%);
  border-color: rgba(255, 255, 255, 0.35);
}

.badge--rec {
  color: #fff;
  background: linear-gradient(135deg, #a5b4fc 0%, #6366f1 50%, #4f46e5 100%);
  border-color: rgba(255, 255, 255, 0.35);
}

.pd__html {
  padding: 14px 14px 18px;
  font-size: 0.9375rem;
  line-height: 1.65;
  color: #334155;
}

.pd__html :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  cursor: zoom-in;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.pd__html :deep(video) {
  max-width: 100%;
  border-radius: 8px;
  background: #000;
}

.pd__reviewsHint,
.pd__reviewsEmpty {
  padding: 12px 14px 16px;
  font-size: 0.8125rem;
  color: #64748b;
  text-align: center;
}

.pd__reviewList {
  list-style: none;
  margin: 0;
  padding: 4px 10px 12px;
}

.pd__review {
  display: flex;
  gap: 12px;
  padding: 12px 8px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.85);
}

.pd__review:last-child {
  border-bottom: none;
}

.pd__reviewAvatar {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
}

.pd__reviewAvatarSvg {
  width: 40px;
  height: 40px;
  display: block;
  border-radius: 50%;
  box-shadow: 0 2px 8px rgba(14, 165, 233, 0.2);
}

.pd__reviewMain {
  flex: 1;
  min-width: 0;
}

.pd__reviewMeta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.pd__reviewName {
  font-size: 0.8125rem;
  font-weight: 700;
  color: #0f172a;
}

.pd__reviewTime {
  font-size: 0.6875rem;
  color: #94a3b8;
  font-variant-numeric: tabular-nums;
}

.pd__reviewText {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: #475569;
  white-space: pre-wrap;
  word-break: break-word;
}

.pd__compose {
  position: relative;
  z-index: 10;
  padding: 12px 14px 16px;
  border-top: 1px solid rgba(226, 232, 240, 0.95);
  background: rgba(248, 250, 252, 0.5);
}

.pd__composeLabel {
  display: block;
  font-size: 0.75rem;
  font-weight: 700;
  color: #475569;
  margin-bottom: 8px;
}

.pd__textarea {
  position: relative;
  z-index: 11;
  width: 100%;
  box-sizing: border-box;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  font-size: 0.875rem;
  line-height: 1.5;
  color: #0f172a;
  background: #fff;
  resize: vertical;
  min-height: 96px;
  touch-action: manipulation;
  -webkit-appearance: none;
}

.pd__textarea:focus {
  outline: none;
  border-color: #38bdf8;
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.18);
}

.pd__textarea:disabled {
  opacity: 0.65;
}

.pd__submitTip {
  margin: 8px 0 0;
  font-size: 0.75rem;
  color: #dc2626;
}

.pd__submitTip--ok {
  color: #15803d;
}

.pd__submitBtn {
  margin-top: 12px;
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  border: none;
  border-radius: 12px;
  font-size: 0.9375rem;
  font-weight: 700;
  cursor: pointer;
  color: #fff;
  background: linear-gradient(120deg, #0ea5e9 0%, #0284c7 50%, #6366f1 100%);
  box-shadow: 0 6px 20px rgba(14, 165, 233, 0.25);
  touch-action: manipulation;
}

.pd__submitBtn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.pd__btnSpin {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.45);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

.pd__empty {
  padding: 3rem 1rem;
  text-align: center;
  color: #64748b;
  font-size: 0.9rem;
}

/* 宽屏：居中阅读宽度，避免去掉封面后出现空洞双列 */
@media (min-width: 1024px) {
  .pd__inner {
    max-width: 44rem;
    padding: 0 1.25rem 2rem;
  }

  .pd__bar {
    margin: 0 -1.25rem;
    padding: 14px 1.25rem calc(10px + env(safe-area-inset-top, 0px));
    border-radius: 0 0 14px 14px;
  }

  .pd__surface--hero {
    padding: 22px 18px 18px;
    margin-top: 6px;
  }

  .pd__title {
    font-size: 1.3rem;
    margin-bottom: 12px;
  }

  .pd__surface--block {
    border-radius: 18px;
  }

  /* 宽屏访问移动端：详情内视频略缩小，避免占满栏宽 */
  .pd__html :deep(video) {
    max-width: min(100%, 28rem);
    margin-left: auto;
    margin-right: auto;
    display: block;
  }
}

@media (min-width: 1280px) {
  .pd__inner {
    max-width: 48rem;
    padding: 0 1.5rem 2.25rem;
  }

  .pd__bar {
    margin: 0 -1.5rem;
    padding-left: 1.5rem;
    padding-right: 1.5rem;
  }
}

@media (min-width: 1024px) and (prefers-reduced-motion: no-preference) {
  .pd__back:hover {
    color: #0369a1;
    text-decoration: underline;
    text-underline-offset: 3px;
  }
}

/* 全屏大图预览（Teleport → body） */
.pd-lightbox {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: env(safe-area-inset-top, 0) 12px calc(12px + env(safe-area-inset-bottom, 0));
  background: rgba(15, 23, 42, 0.88);
  backdrop-filter: blur(10px);
}

.pd-lightbox__close {
  position: absolute;
  top: calc(8px + env(safe-area-inset-top, 0));
  right: 12px;
  width: 44px;
  height: 44px;
  border: none;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.14);
  color: #f8fafc;
  font-size: 1.75rem;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  touch-action: manipulation;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

.pd-lightbox__close:active {
  opacity: 0.85;
}

.pd-lightbox__img {
  max-width: 100%;
  max-height: min(88vh, 920px);
  width: auto;
  height: auto;
  object-fit: contain;
  border-radius: 12px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.4);
}
</style>
