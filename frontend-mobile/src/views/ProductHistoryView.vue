<template>
  <div class="phist">
    <div class="phist__bg" aria-hidden="true" />

    <div class="phist__inner">
      <header class="phist__bar">
        <button type="button" class="phist__back" @click="goBack">← 返回</button>
        <h1 class="phist__title">浏览历史</h1>
      </header>

      <section v-if="loading && !items.length" class="phist__loading">
        <span class="phist__spinner" />
        加载中…
      </section>

      <template v-else>
        <ul v-if="items.length" class="phist__list">
          <li
            v-for="p in items"
            :key="p.id"
            class="hrow"
            :class="p.status === 'on' ? 'hrow--on' : 'hrow--off'"
            @click="goDetail(p.id)"
          >
            <div class="hrow__cover">
              <img v-if="p.coverImage" :src="p.coverImage" alt="" loading="lazy" />
              <span v-else class="hrow__noimg">无图</span>
            </div>
            <div class="hrow__body">
              <div class="hrow__top">
                <h3 class="hrow__name">{{ p.name }}</h3>
                <span
                  v-if="p.status === 'on'"
                  class="hrow__status hrow__status--on"
                  aria-label="在岗"
                >
                  <MobileIcon name="sun" size="md" class="hrow__statusIco" />
                </span>
                <span v-else class="hrow__status hrow__status--off" aria-label="休息">
                  <MobileIcon name="moon" size="md" class="hrow__statusIco" />
                </span>
              </div>
              <div v-if="(p.starRating ?? 0) > 0" class="hrow__stars">
                <StarRating :rating="p.starRating" />
              </div>
              <p class="hrow__addr">
                <MobileIcon name="mapPin" size="sm" class="hrow__addrIcon" />
                <span>{{ p.address || "—" }}</span>
              </p>
              <time class="hrow__time" :datetime="p.viewedAt">
                <MobileIcon name="history" size="sm" class="hrow__timeIcon" />
                {{ formatDateTimeZh(p.viewedAt) }}
              </time>
            </div>
          </li>
        </ul>

        <div ref="sentinelRef" class="phist__sentinel" aria-hidden="true" />

        <div v-if="loadingMore" class="phist__more">加载更多…</div>

        <div v-if="!items.length && !loading" class="phist__empty">
          <MobileIcon name="history" size="lg" class="phist__emptyIcon" />
          <p>暂无浏览记录</p>
          <p class="phist__emptyHint">浏览过的商品会出现在这里</p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { http } from "@/api/http";
import MobileIcon from "@/components/MobileIcon.vue";
import StarRating from "@/components/StarRating.vue";
import { useSessionStore } from "@/stores/session";
import { formatDateTimeZh } from "@/utils/formatDateTime";

type HistoryRow = {
  id: number;
  name: string;
  coverImage?: string | null;
  starRating: number;
  status: string;
  address?: string | null;
  viewedAt: string;
};

const router = useRouter();
const session = useSessionStore();

const items = ref<HistoryRow[]>([]);
const loading = ref(true);
const loadingMore = ref(false);
const page = ref(1);
const pageSize = 20;
const total = ref(0);
const sentinelRef = ref<HTMLElement | null>(null);
let scrollObserver: IntersectionObserver | null = null;

function goBack() {
  void router.push({ name: "products" });
}

function goDetail(id: number) {
  void router.push({ name: "product-detail", params: { id: String(id) }, query: { from: "history" } });
}

async function loadHistory(append: boolean) {
  if (!session.visitorKey) return;
  if (!append) {
    page.value = 1;
    loading.value = true;
  } else {
    loadingMore.value = true;
  }
  try {
    const { data } = await http.get<{
      data: { items: HistoryRow[]; total: number; page: number; pageSize: number };
    }>("/mobile/product-history", {
      params: {
        visitorKey: session.visitorKey,
        page: page.value,
        pageSize,
      },
    });
    const batch = data.data.items || [];
    total.value = data.data.total ?? 0;
    if (append) {
      items.value = [...items.value, ...batch];
    } else {
      items.value = batch;
    }
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
}

async function loadMore() {
  if (loading.value || loadingMore.value) return;
  if (items.value.length >= total.value) return;
  page.value += 1;
  await loadHistory(true);
}

function setupInfiniteScroll() {
  scrollObserver?.disconnect();
  scrollObserver = null;
  const el = sentinelRef.value;
  if (!el || typeof IntersectionObserver === "undefined") return;
  scrollObserver = new IntersectionObserver(
    (entries) => {
      if (!entries[0]?.isIntersecting) return;
      void loadMore();
    },
    { root: null, rootMargin: "200px", threshold: 0 },
  );
  scrollObserver.observe(el);
}

watch(sentinelRef, () => {
  void nextTick(() => setupInfiniteScroll());
});

watch(
  () => items.value.length,
  () => {
    void nextTick(() => setupInfiniteScroll());
  },
);

onMounted(async () => {
  document.title = "浏览历史";
  await loadHistory(false);
  await nextTick(() => setupInfiniteScroll());
});

onUnmounted(() => {
  scrollObserver?.disconnect();
  scrollObserver = null;
});
</script>

<style scoped>
.phist {
  position: relative;
  min-height: 100vh;
  min-height: 100dvh;
  padding-bottom: calc(24px + env(safe-area-inset-bottom, 0px));
}

.phist__bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(ellipse 120% 80% at 50% -20%, rgba(14, 165, 233, 0.12), transparent 55%),
    linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
}

.phist__inner {
  position: relative;
  z-index: 1;
  max-width: 32rem;
  margin: 0 auto;
  padding: calc(0.65rem + env(safe-area-inset-top, 0px)) 0.9rem 0;
}

.phist__bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  padding: 4px 0 8px;
}

.phist__back {
  flex-shrink: 0;
  padding: 8px 4px;
  border: none;
  background: none;
  color: #0369a1;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  min-height: 44px;
}

.phist__title {
  flex: 1;
  min-width: 0;
  margin: 0;
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: 0.01em;
}

.phist__loading,
.phist__more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 2rem 1rem;
  color: #64748b;
  font-size: 0.9rem;
}

.phist__spinner {
  width: 22px;
  height: 22px;
  border: 2px solid rgba(14, 165, 233, 0.2);
  border-top-color: #0ea5e9;
  border-radius: 50%;
  animation: phist-spin 0.7s linear infinite;
}

@keyframes phist-spin {
  to {
    transform: rotate(360deg);
  }
}

.phist__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hrow {
  display: flex;
  gap: 12px;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: linear-gradient(165deg, #ffffff 0%, #fafbfc 100%);
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
  cursor: pointer;
  transition:
    transform 0.12s ease,
    box-shadow 0.15s ease;
  touch-action: manipulation;
}

.hrow:active {
  transform: scale(0.985);
}

.hrow--on {
  border-color: rgba(34, 197, 94, 0.22);
}

.hrow--off {
  border-color: rgba(148, 163, 184, 0.35);
  opacity: 0.92;
}

.hrow__cover {
  flex-shrink: 0;
  width: 72px;
  height: 72px;
  border-radius: 12px;
  overflow: hidden;
  background: linear-gradient(145deg, #f1f5f9 0%, #e2e8f0 100%);
}

.hrow__cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.hrow__noimg {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  font-size: 0.75rem;
  color: #94a3b8;
}

.hrow__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.hrow__top {
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

.hrow__name {
  flex: 1;
  min-width: 0;
  margin: 0;
  font-size: 0.9375rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.hrow__status {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
}

.hrow__status--on {
  color: #16a34a;
  background: rgba(34, 197, 94, 0.12);
}

.hrow__status--off {
  color: #64748b;
  background: rgba(100, 116, 139, 0.1);
}

.hrow__stars {
  margin-top: 2px;
}

.hrow__addr {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  margin: 0;
  font-size: 0.8125rem;
  color: #64748b;
  line-height: 1.4;
}

.hrow__addrIcon {
  flex-shrink: 0;
  margin-top: 2px;
  color: #94a3b8;
}

.hrow__addr span {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.hrow__time {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 2px;
  font-size: 0.75rem;
  color: #0369a1;
  font-weight: 500;
}

.hrow__timeIcon {
  color: #0ea5e9;
  opacity: 0.85;
}

.phist__sentinel {
  height: 1px;
  margin-top: 8px;
}

.phist__empty {
  padding: 3rem 1.5rem 2rem;
  text-align: center;
  color: #64748b;
}

.phist__emptyIcon {
  margin: 0 auto 12px;
  color: #cbd5e1;
}

.phist__empty p {
  margin: 0;
  font-size: 0.9375rem;
}

.phist__emptyHint {
  margin-top: 6px !important;
  font-size: 0.8125rem !important;
  color: #94a3b8;
}

@media (min-width: 1024px) {
  .hrow:hover {
    box-shadow: 0 6px 20px rgba(15, 23, 42, 0.08);
    border-color: rgba(14, 165, 233, 0.35);
  }

  .phist__back:hover {
    color: #0284c7;
  }
}
</style>
