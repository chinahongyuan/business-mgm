<template>
  <div class="plist">
    <div class="plist__bg" aria-hidden="true" />

    <AnnouncementModal
      v-model="showAnnSimple"
      :content-html="announcementHtml"
      :mode="annModalMode"
      title="娱乐指南"
    />
    <AnnouncementModal
      v-model="showBulletinModal"
      :content-html="bulletinHtml"
      mode="simple"
      title="公告"
    />
    <GeoHelpModal v-model="showGeoHelpModal" @retry="onGeoHelpRetry" />

    <div class="plist__inner">
      <div class="plist__search">
        <div class="plist__searchField">
          <MobileIcon name="search" size="sm" class="plist__searchIcon" />
          <input
            v-model="keyword"
            class="plist__input"
            type="search"
            placeholder="搜索商品名称或地址"
            @keyup.enter="reload"
          />
        </div>
        <button type="button" class="plist__searchBtn" @click="reload">搜索</button>
      </div>

      <div
        v-if="activeFilterChips.length"
        class="filterStrip"
        aria-label="当前已选筛选条件，可点击 × 移除单项"
      >
        <div class="filterStrip__scroll">
          <button
            v-for="c in activeFilterChips"
            :key="c.key"
            type="button"
            class="filterChip"
            :aria-label="`移除条件：${c.label}`"
            @click="c.remove"
          >
            <span class="filterChip__text">{{ c.label }}</span>
            <span class="filterChip__x" aria-hidden="true">×</span>
          </button>
        </div>
        <button
          v-if="activeFilterChips.length >= 2"
          type="button"
          class="filterStrip__clear"
          @click="clearAllFilters"
        >
          清空
        </button>
      </div>

      <section v-if="loading && !items.length" class="plist__loading">
        <span class="plist__spinner" />
        加载中…
      </section>

      <template v-else>
        <section class="filterDeck" aria-label="筛选与排序（含商品状态）">
          <div class="filterDeck__surface">
            <div class="filterDeck__block filterDeck__block--sort">
              <div class="filterDeck__blockHead">
                <span class="filterDeck__dot filterDeck__dot--violet" aria-hidden="true" />
                <MobileIcon name="sort" size="sm" class="filterDeck__headIcon" />
                <span class="filterDeck__blockTitle">排序</span>
              </div>
              <div class="filterSeg" role="group" aria-label="排序方式">
                <button
                  type="button"
                  class="filterSeg__btn"
                  :class="{ 'filterSeg__btn--on': sort === 'default' }"
                  @click="setSort('default')"
                >
                  默认
                </button>
                <button
                  type="button"
                  class="filterSeg__btn"
                  :class="{ 'filterSeg__btn--on': sort === 'distance' }"
                  @click="setSort('distance')"
                >
                  距离
                </button>
                <button
                  type="button"
                  class="filterSeg__btn"
                  :class="{ 'filterSeg__btn--on': sort === 'latest' }"
                  @click="setSort('latest')"
                >
                  最新
                </button>
              </div>
              <!-- 定位中/失败时 sort 尚未切到 distance，仍需展示提示，否则用户以为按钮无响应 -->
              <p v-if="geoStatus" class="filterDeck__hint">{{ geoStatus }}</p>
            </div>

            <div class="filterAcc" role="presentation">
              <div class="filterAcc__item filterAcc__item--city">
                <button
                  type="button"
                  class="filterAcc__head"
                  :class="{ 'filterAcc__head--active': !!city.trim() }"
                  :aria-expanded="openFilterPanel === 'city'"
                  @click="toggleFilterPanel('city')"
                >
                  <span class="filterDeck__dot filterDeck__dot--sky" aria-hidden="true" />
                  <span class="filterAcc__title">城市</span>
                  <span class="filterAcc__value" :title="filterSummaryCity">{{ filterSummaryCity }}</span>
                  <span class="filterAcc__chev" :class="{ 'filterAcc__chev--open': openFilterPanel === 'city' }" aria-hidden="true" />
                </button>
                <div v-show="openFilterPanel === 'city'" class="filterAcc__body">
                  <div class="optGrid">
                    <button type="button" class="opt opt--city" :class="{ 'opt--on': !city }" @click="onCityAll">全部</button>
                    <button
                      v-for="c in meta.cities"
                      :key="c"
                      type="button"
                      class="opt opt--city"
                      :class="{ 'opt--on': city === c }"
                      @click="onCityPick(c)"
                    >
                      {{ c }}
                    </button>
                  </div>
                </div>
              </div>

              <div class="filterAcc__item filterAcc__item--district">
                <button
                  type="button"
                  class="filterAcc__head"
                  :class="{ 'filterAcc__head--active': !!district.trim() }"
                  :aria-expanded="openFilterPanel === 'district'"
                  @click="toggleFilterPanel('district')"
                >
                  <span class="filterDeck__dot filterDeck__dot--cyan" aria-hidden="true" />
                  <span class="filterAcc__title">区域</span>
                  <span class="filterAcc__value" :title="filterSummaryDistrict">{{ filterSummaryDistrict }}</span>
                  <span
                    class="filterAcc__chev"
                    :class="{ 'filterAcc__chev--open': openFilterPanel === 'district' }"
                    aria-hidden="true"
                  />
                </button>
                <div v-show="openFilterPanel === 'district'" class="filterAcc__body">
                  <div class="optGrid">
                    <button type="button" class="opt opt--district" :class="{ 'opt--on': !district }" @click="district = ''; reload()">
                      全部
                    </button>
                    <button
                      v-for="d in meta.districts"
                      :key="d"
                      type="button"
                      class="opt opt--district"
                      :class="{ 'opt--on': district === d }"
                      @click="
                        district = d;
                        reload();
                      "
                    >
                      {{ d }}
                    </button>
                  </div>
                </div>
              </div>

              <div class="filterAcc__item filterAcc__item--tags">
                <button
                  type="button"
                  class="filterAcc__head"
                  :class="{ 'filterAcc__head--active': tagIds.length > 0 }"
                  :aria-expanded="openFilterPanel === 'tags'"
                  @click="toggleFilterPanel('tags')"
                >
                  <span class="filterDeck__dot filterDeck__dot--amber" aria-hidden="true" />
                  <span class="filterAcc__title">特点</span>
                  <span class="filterAcc__value" :title="filterSummaryTagsFull">{{ filterSummaryTags }}</span>
                  <span class="filterAcc__chev" :class="{ 'filterAcc__chev--open': openFilterPanel === 'tags' }" aria-hidden="true" />
                </button>
                <div v-show="openFilterPanel === 'tags'" class="filterAcc__body">
                  <div class="optGrid">
                    <button type="button" class="opt opt--tags" :class="{ 'opt--on': !tagIds.length }" @click="clearTagFilters">
                      全部
                    </button>
                    <button
                      v-for="t in meta.tags"
                      :key="t.id"
                      type="button"
                      class="opt opt--tags"
                      :class="{ 'opt--on': tagIds.includes(t.id) }"
                      @click="toggleTag(t.id)"
                    >
                      {{ t.name }}
                    </button>
                  </div>
                </div>
              </div>

              <div class="filterAcc__item filterAcc__item--categories">
                <button
                  type="button"
                  class="filterAcc__head"
                  :class="{ 'filterAcc__head--active': categoryId != null }"
                  :aria-expanded="openFilterPanel === 'categories'"
                  @click="toggleFilterPanel('categories')"
                >
                  <span class="filterDeck__dot filterDeck__dot--purple" aria-hidden="true" />
                  <span class="filterAcc__title">分类</span>
                  <span class="filterAcc__value" :title="filterSummaryCategory">{{ filterSummaryCategory }}</span>
                  <span
                    class="filterAcc__chev"
                    :class="{ 'filterAcc__chev--open': openFilterPanel === 'categories' }"
                    aria-hidden="true"
                  />
                </button>
                <div v-show="openFilterPanel === 'categories'" class="filterAcc__body">
                  <div class="optGrid">
                    <button
                      type="button"
                      class="opt opt--category"
                      :class="{ 'opt--on': categoryId === null }"
                      @click="categoryId = null; reload()"
                    >
                      全部
                    </button>
                    <button
                      v-for="c in meta.categories"
                      :key="c.id"
                      type="button"
                      class="opt opt--category"
                      :class="{ 'opt--on': categoryId === c.id }"
                      @click="
                        categoryId = c.id;
                        reload();
                      "
                    >
                      {{ c.name }}
                    </button>
                  </div>
                </div>
              </div>

              <div class="filterAcc__item filterAcc__item--status filterAcc__item--last">
                <button
                  type="button"
                  class="filterAcc__head"
                  :class="{ 'filterAcc__head--active': productStatusFilter !== '' }"
                  :aria-expanded="openFilterPanel === 'status'"
                  @click="toggleFilterPanel('status')"
                >
                  <span class="filterDeck__dot filterDeck__dot--emerald" aria-hidden="true" />
                  <span class="filterAcc__title">状态</span>
                  <span class="filterAcc__value" :title="filterSummaryStatus">{{ filterSummaryStatus }}</span>
                  <span
                    class="filterAcc__chev"
                    :class="{ 'filterAcc__chev--open': openFilterPanel === 'status' }"
                    aria-hidden="true"
                  />
                </button>
                <div v-show="openFilterPanel === 'status'" class="filterAcc__body">
                  <div class="optGrid">
                    <button
                      type="button"
                      class="opt opt--status"
                      :class="{ 'opt--on': productStatusFilter === '' }"
                      @click="
                        productStatusFilter = '';
                        reload();
                      "
                    >
                      全部
                    </button>
                    <button
                      type="button"
                      class="opt opt--status"
                      :class="{ 'opt--on': productStatusFilter === 'on' }"
                      @click="
                        productStatusFilter = 'on';
                        reload();
                      "
                    >
                      在岗
                    </button>
                    <button
                      type="button"
                      class="opt opt--status"
                      :class="{ 'opt--on': productStatusFilter === 'off' }"
                      @click="
                        productStatusFilter = 'off';
                        reload();
                      "
                    >
                      休息
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <ul class="plist__list">
          <li
            v-for="p in items"
            :key="p.id"
            class="prow"
            :data-plist-pid="p.id"
            :class="[p.status === 'on' ? 'prow--on' : 'prow--off', desktopProwHeightClass(p)]"
            @click="goDetail(p.id)"
          >
            <div class="prow__media">
              <div class="prow__cover">
                <img v-if="p.coverImage" :src="p.coverImage" alt="" loading="lazy" />
                <span v-else class="prow__noimg">无图</span>
              </div>
              <div v-if="isDesktopLayout && hasProwFlags(p)" class="prow__flags prow__flags--underCover">
                <span v-if="p.hasHotReview" class="badge badge--review">
                  <MobileIcon name="chatFill" size="xs" class="badge__ico" />
                  <span>热评</span>
                </span>
                <span v-if="p.hot" class="badge badge--hot">
                  <MobileIcon name="fireFill" size="xs" class="badge__ico" />
                  <span>热门</span>
                </span>
                <span v-if="p.recommend" class="badge badge--rec">
                  <MobileIcon name="starFill" size="xs" class="badge__ico" />
                  <span>推荐</span>
                </span>
              </div>
            </div>
            <div class="prow__body">
              <div class="prow__top">
                <div class="prow__titleRow">
                  <h3 class="prow__name">{{ p.name }}</h3>
                  <span
                    v-if="p.status === 'on'"
                    class="prow__status prow__status--on"
                    aria-label="在岗"
                  >
                    <MobileIcon name="sun" size="md" class="prow__statusIco" />
                    <span class="prow__statusLbl">在岗</span>
                  </span>
                  <span v-else class="prow__status prow__status--off" aria-label="休息">
                    <MobileIcon name="moon" size="md" class="prow__statusIco" />
                    <span class="prow__statusLbl">休息</span>
                  </span>
                </div>
                <div class="prow__metaStack">
                  <div v-if="(p.starRating ?? 0) > 0" class="prow__row2">
                    <StarRating :rating="p.starRating" />
                  </div>
                  <div class="prow__visits" :aria-label="`浏览量 ${formatVisitCount(p.visitCount)}`">
                    <span class="prow__visitsLabel">浏览量：</span>
                    <span class="prow__visitsVal">{{ formatVisitCount(p.visitCount) }}</span>
                  </div>
                </div>
                <div class="prow__rowPrice">
                  <div class="prow__priceBlock" aria-label="价格">
                    <span class="prow__priceYuan">¥</span>
                    <span class="prow__priceInt">{{ listPriceInteger(p.price) }}</span>
                  </div>
                </div>
              </div>
              <p class="prow__addr">
                <span class="prow__addrInner">
                  <MobileIcon name="mapPin" size="sm" class="prow__addrIcon" />
                  <span class="prow__addrText">{{ p.address || "—" }}</span>
                </span>
              </p>
              <div class="prow__bottom">
                <div v-if="p.tagNames?.length" class="prow__tags">
                  <span v-for="t in p.tagNames" :key="t" class="tagpill">{{ t }}</span>
                </div>
                <div v-if="!isDesktopLayout && hasProwFlags(p)" class="prow__flags">
                  <span v-if="p.hasHotReview" class="badge badge--review">
                    <MobileIcon name="chatFill" size="xs" class="badge__ico" />
                    <span>热评</span>
                  </span>
                  <span v-if="p.hot" class="badge badge--hot">
                    <MobileIcon name="fireFill" size="xs" class="badge__ico" />
                    <span>热门</span>
                  </span>
                  <span v-if="p.recommend" class="badge badge--rec">
                    <MobileIcon name="starFill" size="xs" class="badge__ico" />
                    <span>推荐</span>
                  </span>
                </div>
                <div v-if="sort === 'distance'" class="prow__dist">
                  <span class="prow__distChip" aria-label="与您的距离">
                    <MobileIcon name="nearMe" size="sm" class="prow__distChip__ico" />
                    <template v-if="p.distanceKm != null">
                      <span class="prow__distChip__label">距您</span>
                      <span class="prow__distChip__val">{{ formatDistanceKm(p.distanceKm) }}</span>
                      <span class="prow__distChip__unit">km</span>
                    </template>
                    <span v-else class="prow__distChip--na">暂无距离</span>
                  </span>
                </div>
              </div>
            </div>
          </li>
        </ul>

        <div ref="sentinelRef" class="plist__sentinel" aria-hidden="true" />

        <div v-if="loadingMore" class="plist__more">加载更多…</div>

        <div v-if="!items.length && !loading" class="plist__empty">暂无商品</div>
      </template>
    </div>

    <button
      v-if="showBulletinFab"
      type="button"
      class="fab fab--bulletin"
      :class="{ 'fab--bulletin--stacked': showAnnFab }"
      aria-label="查看公告"
      @click="openBulletin"
    >
      <span class="fab__text fab__text--single">公告</span>
    </button>
    <button
      v-if="showAnnFab"
      type="button"
      class="fab fab--guide"
      aria-label="查看娱乐指南"
      @click="openAnnSimple"
    >
      <span class="fab__text" aria-hidden="true">
        <span class="fab__line">娱乐</span>
        <span class="fab__line">指南</span>
      </span>
    </button>
  </div>
</template>

<script lang="ts">
export default { name: "ProductListView" };
</script>

<script setup lang="ts">
import { computed, nextTick, onActivated, onDeactivated, onMounted, onUnmounted, ref, watch } from "vue";
import { onBeforeRouteLeave, useRouter } from "vue-router";

import { http } from "@/api/http";
import AnnouncementModal from "@/components/AnnouncementModal.vue";
import GeoHelpModal from "@/components/GeoHelpModal.vue";
import { requestUserGeo } from "@/utils/requestUserGeo";
import MobileIcon from "@/components/MobileIcon.vue";
import StarRating from "@/components/StarRating.vue";
import { useSessionStore } from "@/stores/session";
import { useBreakpoints } from "@/composables/useBreakpoints";
import { withRetries } from "@/utils/withRetries";

type ProductRow = {
  id: number;
  name: string;
  coverImage?: string | null;
  starRating: number;
  status: string;
  price: number;
  address?: string | null;
  city?: string | null;
  district?: string | null;
  tagNames?: string[];
  hot?: boolean;
  recommend?: boolean;
  distanceKm?: number | null;
  /** 留言板存在审核通过的留言 */
  hasHotReview?: boolean;
  visitCount?: number;
};

const router = useRouter();
const session = useSessionStore();
const { isDesktopLayout } = useBreakpoints();

/** 列表 → 详情 → 返回列表时恢复滚动；配合 keep-alive 保留列表状态 */
const PLIST_SCROLL_KEY = "bmgm_plist_scroll";
const PLIST_SCROLL_TS_KEY = "bmgm_plist_scroll_ts";
/** 从列表进入详情前记下商品 id，返回后与保存的视口偏移一起用于滚动纠偏 */
const PLIST_FOCUS_PID_KEY = "bmgm_plist_focus_pid";
/** 点击进入详情时该商品行相对视口的 getBoundingClientRect().top（px）；恢复时用 docY − savedTop 算出 scrollY */
const PLIST_FOCUS_ROW_VTOP_KEY = "bmgm_plist_focus_row_vtop";
/** 与后端口令会话 MOBILE_PASSWORD_SESSION_TTL（24h）同量级，避免仅因超时放弃恢复、却又不回顶 */
const PLIST_SCROLL_MAX_AGE_MS = 24 * 60 * 60 * 1000;
/** 懒加载等因素导致布局后继续微调；次数少，避免与其它逻辑抢滚动 */
const PLIST_ANCHOR_RECHECK_MS = [100, 280] as const;

function getWindowScrollY(): number {
  if (typeof window === "undefined") return 0;
  const d = typeof document !== "undefined" ? document.documentElement?.scrollTop : undefined;
  const b = typeof document !== "undefined" ? document.body?.scrollTop : undefined;
  return window.scrollY ?? window.pageYOffset ?? d ?? b ?? 0;
}

/** 满足 elementTop = savedViewportTop ⇒ scrollTop = docY − savedViewportTop（docY 为行顶相对于文档的布局坐标近似值） */
function applyPlistRowViewportAnchor(focusPid: string, savedViewportTop: number): boolean {
  if (typeof window === "undefined") return false;
  const el = document.querySelector(`[data-plist-pid="${focusPid}"]`) as HTMLElement | null;
  if (!el) return false;
  const docY = el.getBoundingClientRect().top + getWindowScrollY();
  const target = docY - savedViewportTop;
  window.scrollTo({ top: Math.max(0, target), left: 0, behavior: "auto" });
  return true;
}

function restoreScrollPosition() {
  if (typeof window === "undefined" || typeof sessionStorage === "undefined") return;
  const raw = sessionStorage.getItem(PLIST_SCROLL_KEY);
  const tsRaw = sessionStorage.getItem(PLIST_SCROLL_TS_KEY);
  const focusPid = sessionStorage.getItem(PLIST_FOCUS_PID_KEY) || "";
  const savedVtopRaw = sessionStorage.getItem(PLIST_FOCUS_ROW_VTOP_KEY);

  sessionStorage.removeItem(PLIST_SCROLL_KEY);
  sessionStorage.removeItem(PLIST_SCROLL_TS_KEY);
  sessionStorage.removeItem(PLIST_FOCUS_PID_KEY);
  sessionStorage.removeItem(PLIST_FOCUS_ROW_VTOP_KEY);

  let savedViewportTop: number | null = null;
  if (savedVtopRaw != null && savedVtopRaw.length > 0) {
    const n = Number.parseInt(savedVtopRaw, 10);
    if (!Number.isNaN(n)) savedViewportTop = n;
  }

  const hasAnchor = focusPid.length > 0 && /^\d+$/.test(focusPid) && savedViewportTop != null;

  let warmY: number | null = null;
  if (raw != null && tsRaw != null) {
    const ts = Number.parseInt(tsRaw, 10);
    if (!Number.isNaN(ts) && Date.now() - ts <= PLIST_SCROLL_MAX_AGE_MS) {
      const y = Number.parseInt(raw, 10);
      if (!Number.isNaN(y)) warmY = y;
    }
  }

  const runAnchorPasses = () => {
    if (!hasAnchor || savedViewportTop == null) return;
    applyPlistRowViewportAnchor(focusPid, savedViewportTop);
    requestAnimationFrame(() => {
      applyPlistRowViewportAnchor(focusPid, savedViewportTop!);
      for (const ms of PLIST_ANCHOR_RECHECK_MS) {
        window.setTimeout(() => applyPlistRowViewportAnchor(focusPid, savedViewportTop!), ms);
      }
    });
  };

  if (!hasAnchor) {
    if (warmY != null) {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          window.scrollTo({ top: Math.max(0, warmY!), left: 0, behavior: "auto" });
        });
      });
    } else if (focusPid && /^\d+$/.test(focusPid)) {
      void tryScrollToProductRow(focusPid);
    }
    return;
  }

  /** 双 rAF：等合帧；先 Warm Y 拉回大致页位再按几何锚对齐（修正上一版 delta 正负反了的问题） */
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      if (warmY != null) {
        window.scrollTo({ top: Math.max(0, warmY), left: 0, behavior: "auto" });
      }
      void nextTick(() => {
        runAnchorPasses();
      });
    });
  });
}

function tryScrollToProductRow(focusPid: string) {
  if (!focusPid || !/^\d+$/.test(focusPid)) return;
  void nextTick(() => {
    requestAnimationFrame(() => {
      const el = document.querySelector(`[data-plist-pid="${focusPid}"]`) as HTMLElement | null;
      if (el && typeof el.scrollIntoView === "function") {
        el.scrollIntoView({ block: "nearest", behavior: "auto" });
      }
    });
  });
}

function saveScrollPosition() {
  if (typeof window !== "undefined" && typeof sessionStorage !== "undefined") {
    sessionStorage.setItem(PLIST_SCROLL_KEY, String(getWindowScrollY()));
    sessionStorage.setItem(PLIST_SCROLL_TS_KEY, String(Date.now()));
  }
}

const PLIST_FILTER_KEY = "bmgm_plist_filters";

function saveFilters() {
  if (typeof sessionStorage === "undefined") return;
  const filters = {
    keyword: keyword.value,
    city: city.value,
    district: district.value,
    tagIds: tagIds.value,
    categoryId: categoryId.value,
    productStatusFilter: productStatusFilter.value,
    sort: sort.value,
  };
  sessionStorage.setItem(PLIST_FILTER_KEY, JSON.stringify(filters));
}

function restoreFilters() {
  if (typeof sessionStorage === "undefined") return;
  const raw = sessionStorage.getItem(PLIST_FILTER_KEY);
  if (!raw) return;
  try {
    const filters = JSON.parse(raw);
    keyword.value = filters.keyword || "";
    city.value = filters.city || "";
    district.value = filters.district || "";
    tagIds.value = filters.tagIds || [];
    categoryId.value = filters.categoryId ?? null;
    productStatusFilter.value = filters.productStatusFilter || "";
    sort.value = filters.sort || "default";
  } catch {
    // ignore
  }
}

const keyword = ref("");
const city = ref("");
const district = ref("");
/** 标签多选（与后端 tagIds 对应，OR 关系） */
const tagIds = ref<number[]>([]);
const categoryId = ref<number | null>(null);
/** 上架/下架筛选；空字符串表示不筛选 */
const productStatusFilter = ref<"" | "on" | "off">("");
const sort = ref<"default" | "distance" | "latest">("default");
const userLat = ref<number | null>(null);
const userLng = ref<number | null>(null);
const geoStatus = ref("");
const showGeoHelpModal = ref(false);
/** 用户曾拒绝定位后，下一次点「距离」先弹出说明（与再次点击逻辑一致） */
const showGeoHelpOnNextDistanceClick = ref(false);

const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const items = ref<ProductRow[]>([]);
const loading = ref(false);
const loadingMore = ref(false);

const meta = ref<{
  cities: string[];
  districts: string[];
  tags: { id: number; name: string }[];
  categories: { id: number; name: string; typeCode: number }[];
  baiduMapAk?: string;
}>({ cities: [], districts: [], tags: [], categories: [], baiduMapAk: "" });

const showAnnSimple = ref(false);
/** 首次进入列表：strict（倒数 5 秒 + 勾选已知晓）；悬浮按钮重开：simple */
const annModalMode = ref<"strict" | "simple">("strict");

/** loadMeta 防抖定时器 */
let loadMetaTimer: ReturnType<typeof setTimeout> | null = null;

function debouncedLoadMeta() {
  if (loadMetaTimer) {
    clearTimeout(loadMetaTimer);
  }
  loadMetaTimer = setTimeout(() => {
    void loadMeta();
  }, 300);
}
const announcementHtml = ref("");
const bulletinHtml = ref("");
const showBulletinModal = ref(false);

const sentinelRef = ref<HTMLElement | null>(null);
let scrollObserver: IntersectionObserver | null = null;

/** 管理后台已发布娱乐指南时为 true */
const showAnnFab = ref(false);
/** 管理后台公告管理已发布时为 true */
const showBulletinFab = ref(false);

/** 手风琴：城市 / 区域 / 标签 / 分类 / 商品状态 同时只展开一项 */
type FilterPanelId = "city" | "district" | "tags" | "categories" | "status";
const openFilterPanel = ref<FilterPanelId | null>("city");

function toggleFilterPanel(id: FilterPanelId) {
  openFilterPanel.value = openFilterPanel.value === id ? null : id;
}

const hasMore = computed(() => items.value.length < total.value);

/** 手风琴标题右侧：当前选中摘要（折叠时也能看到） */
const filterSummaryCity = computed(() => {
  const c = city.value.trim();
  return c || "未选";
});

const filterSummaryDistrict = computed(() => {
  const d = district.value.trim();
  return d || "未选";
});

const filterSummaryTagsFull = computed(() => {
  if (!tagIds.value.length) return "未选";
  const names = tagIds.value
    .map((id) => meta.value.tags.find((t) => t.id === id)?.name)
    .filter((n): n is string => !!n);
  return names.length ? names.join("、") : `${tagIds.value.length} 项`;
});

const filterSummaryTags = computed(() => {
  if (!tagIds.value.length) return "未选";
  const names = tagIds.value
    .map((id) => meta.value.tags.find((t) => t.id === id)?.name)
    .filter((n): n is string => !!n);
  if (!names.length) return `${tagIds.value.length} 项`;
  if (names.length <= 2) return names.join("、");
  return `${names.slice(0, 2).join("、")}…共${tagIds.value.length}项`;
});

const filterSummaryCategory = computed(() => {
  if (categoryId.value == null) return "未选";
  return meta.value.categories.find((c) => c.id === categoryId.value)?.name ?? "已选";
});

const filterSummaryStatus = computed(() => {
  if (productStatusFilter.value === "on") return "在岗";
  if (productStatusFilter.value === "off") return "休息";
  return "未选";
});

/** 搜索框下方芯片：非默认条件一目了然，可点整颗芯片移除 */
const activeFilterChips = computed(() => {
  const chips: { key: string; label: string; remove: () => void }[] = [];
  const kw = keyword.value.trim();
  if (kw) {
    chips.push({
      key: "keyword",
      label: `搜索 · ${kw.length > 14 ? `${kw.slice(0, 14)}…` : kw}`,
      remove: () => {
        keyword.value = "";
        reload();
      },
    });
  }
  if (sort.value === "distance") {
    chips.push({
      key: "sort-distance",
      label: "排序 · 距离",
      remove: () => {
        sort.value = "default";
        geoStatus.value = "";
        reload();
      },
    });
  } else if (sort.value === "latest") {
    chips.push({
      key: "sort-latest",
      label: "排序 · 最新",
      remove: () => {
        sort.value = "default";
        reload();
      },
    });
  }
  const c = city.value.trim();
  if (c) {
    chips.push({
      key: "city",
      label: `城市 · ${c}`,
      remove: () => {
        city.value = "";
        district.value = "";
        debouncedLoadMeta();
        reload();
      },
    });
  }
  const d = district.value.trim();
  if (d) {
    chips.push({
      key: "district",
      label: `区域 · ${d}`,
      remove: () => {
        district.value = "";
        reload();
      },
    });
  }
  for (const tid of tagIds.value) {
    const name = meta.value.tags.find((t) => t.id === tid)?.name ?? `#${tid}`;
    chips.push({
      key: `tag-${tid}`,
      label: `特点 · ${name}`,
      remove: () => {
        tagIds.value = tagIds.value.filter((x) => x !== tid);
        reload();
      },
    });
  }
  if (categoryId.value != null) {
    const cn = meta.value.categories.find((x) => x.id === categoryId.value)?.name ?? "";
    chips.push({
      key: "category",
      label: `分类 · ${cn || "—"}`,
      remove: () => {
        categoryId.value = null;
        reload();
      },
    });
  }
  if (productStatusFilter.value === "on") {
    chips.push({
      key: "status-on",
      label: "状态 · 在岗",
      remove: () => {
        productStatusFilter.value = "";
        reload();
      },
    });
  } else if (productStatusFilter.value === "off") {
    chips.push({
      key: "status-off",
      label: "状态 · 休息",
      remove: () => {
        productStatusFilter.value = "";
        reload();
      },
    });
  }
  return chips;
});

function clearAllFilters() {
  keyword.value = "";
  city.value = "";
  district.value = "";
  tagIds.value = [];
  categoryId.value = null;
  productStatusFilter.value = "";
  sort.value = "default";
  geoStatus.value = "";
  debouncedLoadMeta();
  reload();
}

function goDetail(id: number) {
  if (typeof sessionStorage !== "undefined") {
    sessionStorage.setItem(PLIST_FOCUS_PID_KEY, String(id));
    if (typeof document !== "undefined") {
      const el = document.querySelector(`[data-plist-pid="${id}"]`) as HTMLElement | null;
      if (el) {
        sessionStorage.setItem(PLIST_FOCUS_ROW_VTOP_KEY, String(Math.round(el.getBoundingClientRect().top)));
      } else {
        sessionStorage.removeItem(PLIST_FOCUS_ROW_VTOP_KEY);
      }
    }
  }
  void router.push({ name: "product-detail", params: { id: String(id) } });
}

/** 宽屏：有封面或有商品标签的一类统一 min-height，两者皆无的另一类统一（仅桌面样式使用类名） */
function desktopProwHeightClass(p: ProductRow) {
  const hasCover = !!p.coverImage;
  const hasTags = (p.tagNames?.length ?? 0) > 0;
  return hasCover || hasTags ? "prow--deskH-rich" : "prow--deskH-plain";
}

function hasProwFlags(p: ProductRow) {
  return !!(p.hasHotReview || p.hot || p.recommend);
}

/** 列表价：仅展示整数（四舍五入） */
function listPriceInteger(n: number) {
  return String(Math.round(Number(n) || 0));
}

/** 列表浏览量：千分位，易扫读 */
function formatVisitCount(n: number | undefined) {
  const v = Math.max(0, Math.floor(Number(n) || 0));
  try {
    return v.toLocaleString("zh-CN");
  } catch {
    return String(v);
  }
}

/** 距离排序下列表展示（后端为 km，三位小数） */
function formatDistanceKm(km: number) {
  if (!Number.isFinite(km)) return "—";
  if (km >= 100) return String(Math.round(km));
  if (km >= 10) return km.toFixed(1);
  return km.toFixed(2);
}

async function postGeo(lat: number, lng: number) {
  try {
    await http.post("/mobile/geo", {
      visitorKey: session.visitorKey,
      latitude: lat,
      longitude: lng,
    });
  } catch {
    /* ignore */
  }
}

function toggleTag(id: number) {
  const cur = tagIds.value;
  const i = cur.indexOf(id);
  if (i >= 0) {
    tagIds.value = cur.filter((x) => x !== id);
  } else {
    tagIds.value = [...cur, id];
  }
  reload();
}

function clearTagFilters() {
  tagIds.value = [];
  reload();
}

async function loadListTitle() {
  try {
    const { data } = await http.get<{ data: { mobileTitle?: string } }>("/mobile/home-page");
    const t = (data?.data?.mobileTitle || "").trim();
    document.title = t || "商品列表";
  } catch {
    document.title = "商品列表";
  }
}

function onCityAll() {
  city.value = "";
  district.value = "";
  reload();
}

function onCityPick(c: string) {
  city.value = c;
  district.value = "";
  reload();
}

async function loadMeta() {
  try {
    await withRetries(
      async () => {
        const { data } = await http.get<{
          data: {
            cities: string[];
            districts: string[];
            tags: { id: number; name: string }[];
            categories: { id: number; name: string; typeCode: number }[];
            baiduMapAk?: string;
          };
        }>("/mobile/meta", { params: { city: city.value || undefined, visitorKey: session.visitorKey } });
        meta.value = {
          cities: data?.data?.cities || [],
          districts: data?.data?.districts || [],
          tags: data?.data?.tags || [],
          categories: data?.data?.categories || [],
          baiduMapAk: data?.data?.baiduMapAk || "",
        };
      },
      { attempts: 3, baseDelayMs: 500 },
    );
  } catch {
    /* 弱网：保留已有 meta，避免整页中断 */
  }
}

type CmsMobilePayload = { published?: boolean; contentHtml?: string };

async function loadBulletin(recordView: boolean): Promise<{ published: boolean; html: string }> {
  try {
    return await withRetries(
      async () => {
        const { data } = await http.get<{ data: CmsMobilePayload }>("/mobile/bulletin", {
          params: {
            visitorKey: session.visitorKey,
            recordView: recordView ? "1" : "0",
            ipRegion: "H5",
          },
        });
        const d = data?.data;
        const published = !!d?.published;
        const html = published ? (d?.contentHtml || "").trim() : "";
        if (recordView) {
          bulletinHtml.value = html;
        }
        return { published, html };
      },
      { attempts: 3, baseDelayMs: 500 },
    );
  } catch {
    if (recordView) {
      bulletinHtml.value = "";
    }
    return { published: false, html: "" };
  }
}

/** 仅更新公告浮标显隐，不弹窗 */
async function refreshBulletinFab() {
  if (!session.isLoggedIn()) {
    showBulletinFab.value = false;
    return;
  }
  const { published, html } = await loadBulletin(false);
  showBulletinFab.value = published && !!html;
}

async function openBulletin() {
  const { published, html } = await loadBulletin(true);
  if (published && html) {
    bulletinHtml.value = html;
    showBulletinModal.value = true;
  }
}

async function loadAnnouncement(recordView: boolean): Promise<{ published: boolean; html: string }> {
  try {
    return await withRetries(
      async () => {
        const { data } = await http.get<{ data: CmsMobilePayload }>("/mobile/announcement", {
          params: {
            visitorKey: session.visitorKey,
            recordView: recordView ? "1" : "0",
            ipRegion: "H5",
          },
        });
        const d = data?.data;
        const published = !!d?.published;
        const html = published ? (d?.contentHtml || "").trim() : "";
        announcementHtml.value = html;
        return { published, html };
      },
      { attempts: 3, baseDelayMs: 500 },
    );
  } catch {
    announcementHtml.value = "";
    return { published: false, html: "" };
  }
}

/**
 * 刷新整页进入列表：弹一次公告（可关）；从详情返回则跳过（见 ProductDetailView 置位 bmgm_skip_list_ann）。
 * 已发布公告时展示悬浮图标，未发布则不展示。
 * 仅已登录用户可查看公告，未登录时跳过。
 */
async function runListAnnouncement() {
  if (!session.isLoggedIn()) {
    showAnnFab.value = false;
    announcementHtml.value = "";
    return;
  }
  const skip =
    typeof sessionStorage !== "undefined" && sessionStorage.getItem("bmgm_skip_list_ann") === "1";
  if (skip) {
    sessionStorage.removeItem("bmgm_skip_list_ann");
    const { published, html } = await loadAnnouncement(false);
    showAnnFab.value = published && !!html;
    return;
  }
  const { published, html } = await loadAnnouncement(true);
  showAnnFab.value = published && !!html;
  if (published && html) {
    let fromLogin = false;
    if (typeof sessionStorage !== "undefined") {
      const loginTs = sessionStorage.getItem("bmgm_from_login");
      if (loginTs) {
        const ts = parseInt(loginTs, 10);
        fromLogin = !Number.isNaN(ts) && Date.now() - ts < 5 * 60 * 1000;
        if (fromLogin) {
          sessionStorage.removeItem("bmgm_from_login");
        }
      }
    }
    annModalMode.value = fromLogin ? "strict" : "simple";
    showAnnSimple.value = true;
  }
}

async function openAnnSimple() {
  const { published, html } = await loadAnnouncement(false);
  if (published && html) {
    annModalMode.value = "simple";
    showAnnSimple.value = true;
  }
}

async function loadProducts(append: boolean) {
  if (!append) {
    page.value = 1;
    loading.value = true;
  } else {
    loadingMore.value = true;
  }
  try {
    const params: Record<string, string | number | undefined> = {
      page: page.value,
      pageSize: pageSize.value,
      keyword: keyword.value.trim() || undefined,
      city: city.value || undefined,
      district: district.value || undefined,
      tagIds: tagIds.value.length ? tagIds.value.join(",") : undefined,
      categoryId: categoryId.value ?? undefined,
      productStatus: productStatusFilter.value || undefined,
      sort: sort.value,
      visitorKey: session.visitorKey,
    };
    if (sort.value === "distance" && userLat.value != null && userLng.value != null) {
      params.userLat = userLat.value;
      params.userLng = userLng.value;
    }
    await withRetries(
      async () => {
        const { data } = await http.get<{ data: { items: ProductRow[]; total: number } }>("/mobile/products", { params });
        const newItems = data?.data?.items || [];
        total.value = data?.data?.total ?? 0;
        if (append) {
          items.value = items.value.concat(newItems);
        } else {
          items.value = newItems;
        }
      },
      { attempts: 3, baseDelayMs: 550 },
    );
  } catch {
    if (!append) {
      items.value = [];
      total.value = 0;
    }
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
}

function reload() {
  void loadProducts(false);
}

async function loadMore() {
  if (loading.value || loadingMore.value || !hasMore.value) return;
  page.value += 1;
  await loadProducts(true);
}

async function onGeoHelpRetry() {
  showGeoHelpModal.value = false;
  showGeoHelpOnNextDistanceClick.value = false;
  geoStatus.value = "正在获取位置…";
  sort.value = "distance";
  const r = await requestUserGeo({ baiduAk: meta.value.baiduMapAk, forceRefresh: true });
  if (r.success && r.lat != null && r.lng != null) {
    userLat.value = r.lat;
    userLng.value = r.lng;
    geoStatus.value = r.hint || "已定位，按距离排序";
    await postGeo(r.lat, r.lng);
    reload();
  } else {
    sort.value = "default";
    geoStatus.value = r.hint || "定位失败";
    showGeoHelpOnNextDistanceClick.value = true;
  }
}

async function setSort(mode: "default" | "distance" | "latest") {
  if (mode === "distance") {
    if (showGeoHelpOnNextDistanceClick.value) {
      showGeoHelpOnNextDistanceClick.value = false;
      showGeoHelpModal.value = true;
      return;
    }
    geoStatus.value = "正在获取位置…";
    sort.value = "distance";
    const r = await requestUserGeo({ baiduAk: meta.value.baiduMapAk });
    if (!r.success) {
      sort.value = "default";
      geoStatus.value = r.hint || "定位失败";
      showGeoHelpOnNextDistanceClick.value = true;
      return;
    }
    if (r.lat == null || r.lng == null) {
      sort.value = "default";
      geoStatus.value = "定位返回数据异常，请重试";
      showGeoHelpOnNextDistanceClick.value = true;
      return;
    }
    userLat.value = r.lat;
    userLng.value = r.lng;
    geoStatus.value = r.hint || "已定位，按距离排序";
    showGeoHelpOnNextDistanceClick.value = false;
    await postGeo(r.lat, r.lng);
    reload();
    return;
  }
  sort.value = mode;
  geoStatus.value = "";
  reload();
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
    { root: null, rootMargin: "240px", threshold: 0 },
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

onBeforeRouteLeave((to) => {
  if (to.name === "product-detail") {
    saveScrollPosition();
    saveFilters();
  }
});

onActivated(() => {
  void loadListTitle().catch(() => {});
  void nextTick(() => {
    setupInfiniteScroll();
    restoreScrollPosition();
  });
});

onDeactivated(() => {
  scrollObserver?.disconnect();
  scrollObserver = null;
});

onMounted(async () => {
  restoreFilters();
  loading.value = true;
  try {
    void loadListTitle().catch(() => {});
    await loadMeta();
    await Promise.all([
      runListAnnouncement().catch(() => {
        showAnnFab.value = false;
      }),
      refreshBulletinFab().catch(() => {
        showBulletinFab.value = false;
      }),
      loadProducts(false),
    ]);
  } finally {
    await nextTick(() => {
      setupInfiniteScroll();
      restoreScrollPosition();
    });
  }
});

onUnmounted(() => {
  if (loadMetaTimer) {
    clearTimeout(loadMetaTimer);
    loadMetaTimer = null;
  }
  scrollObserver?.disconnect();
  scrollObserver = null;
});

watch(city, () => {
  debouncedLoadMeta();
});
</script>

<style scoped>
.plist {
  position: relative;
  min-height: 100vh;
  min-height: 100dvh;
  padding-bottom: calc(88px + env(safe-area-inset-bottom, 0px));
}

.plist__bg {
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

.plist__inner {
  position: relative;
  z-index: 1;
  max-width: 32rem;
  margin: 0 auto;
  padding: calc(0.65rem + env(safe-area-inset-top, 0px)) 0.9rem 0;
}

.plist__search {
  display: flex;
  gap: 8px;
  padding: 0 0 14px;
  align-items: stretch;
}

.plist__searchField {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 4px 0 12px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.plist__searchField:focus-within {
  border-color: #38bdf8;
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.18);
}

.plist__searchIcon {
  color: #94a3b8;
  flex-shrink: 0;
}

.plist__input {
  flex: 1;
  min-width: 0;
  padding: 12px 10px 12px 0;
  border: none;
  border-radius: 0;
  font-size: 0.9375rem;
  background: transparent;
  color: #0f172a;
}

.plist__input::placeholder {
  color: #94a3b8;
}

.plist__input:focus {
  outline: none;
}

.plist__searchBtn {
  flex-shrink: 0;
  padding: 12px 18px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(180deg, #0ea5e9 0%, #0284c7 100%);
  color: #fff;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35);
}

/* 已选条件：横向滚动芯片 + 清空（解决手风琴收起后「忘了选了啥」） */
.filterStrip {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 12px;
}

.filterStrip__scroll {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
  overflow-x: auto;
  padding: 2px 0 4px;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
}

.filterStrip__scroll::-webkit-scrollbar {
  height: 4px;
}

.filterStrip__scroll::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.45);
  border-radius: 4px;
}

.filterChip {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: min(220px, 72vw);
  padding: 9px 12px 9px 14px;
  border: 1px solid rgba(148, 163, 184, 0.38);
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.94) 100%);
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
  font-size: 0.75rem;
  font-weight: 700;
  color: #334155;
  letter-spacing: 0.01em;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.filterChip:active {
  transform: scale(0.98);
}

.filterChip:focus-visible {
  outline: 2px solid #0284c7;
  outline-offset: 2px;
}

.filterChip__text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.filterChip__x {
  flex-shrink: 0;
  font-size: 1.05rem;
  line-height: 1;
  opacity: 0.5;
  font-weight: 700;
}

.filterStrip__clear {
  flex-shrink: 0;
  padding: 9px 14px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 12px;
  background: rgba(248, 250, 252, 0.95);
  color: #475569;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.02em;
  cursor: pointer;
  touch-action: manipulation;
}

.filterStrip__clear:focus-visible {
  outline: 2px solid #0284c7;
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .filterChip:active {
    transform: none;
  }
}

.plist__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 2.5rem 1rem;
  color: #64748b;
  font-size: 0.9rem;
}

.plist__spinner {
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

/* —— 筛选区：单卡片 + 分段排序 + 横向滚动标签（无动画，静态排版） —— */
.filterDeck {
  padding: 0 0 14px;
}

.filterDeck__surface {
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.99) 0%, rgba(248, 250, 252, 0.96) 100%);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.95) inset,
    0 10px 32px rgba(15, 23, 42, 0.07);
  overflow: hidden;
}

.filterDeck__block {
  padding: 12px 12px 10px;
  border-bottom: 1px solid #e2e8f0;
}

.filterDeck__block--sort {
  padding-bottom: 12px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.9) 0%, rgba(255, 255, 255, 0.5) 100%);
  border-bottom: 1px solid #e2e8f0;
}

.filterDeck__blockHead {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.filterDeck__headIcon {
  color: #8b5cf6;
  flex-shrink: 0;
}

.filterDeck__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.filterDeck__dot--violet {
  background: #8b5cf6;
}

.filterDeck__dot--sky {
  background: #0ea5e9;
}

.filterDeck__dot--cyan {
  background: #06b6d4;
}

.filterDeck__dot--amber {
  background: #f59e0b;
}

.filterDeck__dot--purple {
  background: #a855f7;
}

.filterDeck__dot--emerald {
  background: #10b981;
}

.filterDeck__blockTitle {
  font-size: 0.8125rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: 0.02em;
}

.filterDeck__hint {
  margin: 8px 0 0;
  font-size: 0.75rem;
  color: #64748b;
  line-height: 1.4;
}

/* 排序：矩形分段，非胶囊 */
.filterSeg {
  display: flex;
  gap: 2px;
  padding: 3px;
  border-radius: 8px;
  background: #e2e8f0;
  border: 1px solid #cbd5e1;
}

.filterSeg__btn {
  flex: 1;
  min-width: 0;
  padding: 10px 8px;
  border: none;
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 600;
  color: #64748b;
  background: transparent;
  cursor: pointer;
  touch-action: manipulation;
}

.filterSeg__btn--on {
  color: #0f172a;
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
}

/* 手风琴：城市 / 区域 / 标签 / 分类 */
.filterAcc {
  border-top: 1px solid #e2e8f0;
}

.filterAcc__item {
  border-bottom: 1px solid #e2e8f0;
}

.filterAcc__item--last {
  border-bottom: none;
}

.filterAcc__head {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 12px;
  margin: 0;
  border: none;
  background: #fafafa;
  cursor: pointer;
  text-align: left;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
  transition: background 0.15s ease, transform 0.12s ease;
}

.filterAcc__head:active {
  transform: scale(0.995);
}

.filterAcc__item--city .filterAcc__head {
  background: rgba(14, 165, 233, 0.06);
}

.filterAcc__item--district .filterAcc__head {
  background: rgba(6, 182, 212, 0.07);
}

.filterAcc__item--tags .filterAcc__head {
  background: rgba(245, 158, 11, 0.08);
}

.filterAcc__item--categories .filterAcc__head {
  background: rgba(168, 85, 247, 0.07);
}

.filterAcc__item--status .filterAcc__head {
  background: rgba(16, 185, 129, 0.08);
}

.filterAcc__title {
  font-size: 0.8125rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: 0.02em;
}

.filterAcc__value {
  flex: 1;
  min-width: 0;
  margin-left: 4px;
  text-align: right;
  font-size: 0.75rem;
  font-weight: 600;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.filterAcc__head--active .filterAcc__value {
  color: #0f172a;
}

.filterAcc__head--active {
  box-shadow: inset 3px 0 0 0 rgba(14, 165, 233, 0.65);
}

.filterAcc__item--district .filterAcc__head--active {
  box-shadow: inset 3px 0 0 0 rgba(6, 182, 212, 0.75);
}

.filterAcc__item--tags .filterAcc__head--active {
  box-shadow: inset 3px 0 0 0 rgba(245, 158, 11, 0.85);
}

.filterAcc__item--categories .filterAcc__head--active {
  box-shadow: inset 3px 0 0 0 rgba(168, 85, 247, 0.75);
}

.filterAcc__item--status .filterAcc__head--active {
  box-shadow: inset 3px 0 0 0 rgba(16, 185, 129, 0.8);
}

.filterAcc__chev {
  margin-left: 6px;
  width: 6px;
  height: 6px;
  border-right: 2px solid #64748b;
  border-bottom: 2px solid #64748b;
  transform: rotate(45deg);
  flex-shrink: 0;
}

.filterAcc__chev--open {
  transform: rotate(-135deg);
}

.filterAcc__body {
  padding: 0 12px 12px;
  background: #fff;
}

.optGrid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* 筛选项：顶条强调选中态；多类配色区分 */
.opt {
  position: relative;
  min-height: 40px;
  padding: 8px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  font-size: 0.8125rem;
  font-weight: 500;
  color: #475569;
  cursor: pointer;
  touch-action: manipulation;
  border-top: 3px solid transparent;
  box-sizing: border-box;
  -webkit-tap-highlight-color: transparent;
  transition:
    transform 0.14s ease,
    box-shadow 0.14s ease,
    border-color 0.14s ease,
    background 0.14s ease,
    color 0.14s ease;
}

.opt:active:not(:disabled) {
  transform: scale(0.985);
}

.opt--on.opt--city {
  border-color: rgba(14, 165, 233, 0.4);
  border-top-color: #0ea5e9;
  background: linear-gradient(180deg, rgba(240, 249, 255, 0.9) 0%, #fff 100%);
  color: #0369a1;
  font-weight: 700;
}

.opt--on.opt--district {
  border-color: rgba(6, 182, 212, 0.4);
  border-top-color: #06b6d4;
  background: linear-gradient(180deg, rgba(236, 254, 255, 0.95) 0%, #fff 100%);
  color: #0e7490;
  font-weight: 700;
}

.opt--on.opt--tags {
  border-color: rgba(245, 158, 11, 0.45);
  border-top-color: #f59e0b;
  background: linear-gradient(180deg, rgba(255, 251, 235, 0.95) 0%, #fff 100%);
  color: #b45309;
  font-weight: 700;
}

.opt--on.opt--category {
  border-color: rgba(168, 85, 247, 0.4);
  border-top-color: #a855f7;
  background: linear-gradient(180deg, rgba(250, 245, 255, 0.95) 0%, #fff 100%);
  color: #6b21a8;
  font-weight: 700;
}

.opt--on.opt--status {
  border-color: rgba(16, 185, 129, 0.45);
  border-top-color: #10b981;
  background: linear-gradient(180deg, rgba(236, 253, 245, 0.95) 0%, #fff 100%);
  color: #047857;
  font-weight: 700;
}

.plist__list {
  list-style: none;
  margin: 0;
  padding: 4px 0 0;
}

.prow {
  display: grid;
  grid-template-columns: 118px minmax(0, 1fr);
  gap: 14px;
  align-items: stretch;
  min-height: 176px;
  padding: 14px;
  margin-bottom: 12px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: linear-gradient(165deg, #ffffff 0%, #fafbfc 100%);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.9) inset,
    0 8px 24px rgba(15, 23, 42, 0.06);
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.prow:active {
  transform: scale(0.992);
}

.prow--on {
  border-color: rgba(34, 197, 94, 0.42);
  box-shadow:
    0 0 0 2px rgba(34, 197, 94, 0.38),
    0 0 0 8px rgba(34, 197, 94, 0.14),
    0 0 0 18px rgba(34, 197, 94, 0.07),
    0 1px 0 rgba(255, 255, 255, 0.95) inset,
    0 12px 32px rgba(34, 197, 94, 0.14);
}

.prow--off {
  border-color: rgba(100, 116, 139, 0.4);
  box-shadow:
    0 0 0 2px rgba(148, 163, 184, 0.35),
    0 0 0 8px rgba(148, 163, 184, 0.12),
    0 0 0 18px rgba(148, 163, 184, 0.06),
    0 6px 20px rgba(15, 23, 42, 0.06);
}

.prow__media {
  min-height: 156px;
}

.prow__cover {
  width: 100%;
  height: 100%;
  min-height: 156px;
  border-radius: 14px;
  overflow: hidden;
  background: linear-gradient(145deg, #f1f5f9 0%, #e2e8f0 100%);
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
}

.prow__cover img {
  width: 100%;
  height: 100%;
  min-height: 156px;
  object-fit: cover;
  display: block;
}

.prow__noimg {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 156px;
  font-size: 0.75rem;
  color: #94a3b8;
}

.prow__body {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 156px;
}

.prow__top {
  flex-shrink: 0;
}

.prow__titleRow {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.prow__name {
  margin: 0;
  font-weight: 700;
  font-size: 0.9375rem;
  color: #0f172a;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
  min-width: 0;
}

.prow__status {
  flex-shrink: 0;
}

.prow__status--on,
.prow__status--off {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8125rem;
  font-weight: 700;
  line-height: 1.2;
  padding: 7px 14px 7px 11px;
  border-radius: 999px;
  letter-spacing: 0.02em;
  white-space: nowrap;
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.75) inset,
    0 2px 6px rgba(15, 23, 42, 0.07);
}

.prow__status--on {
  background: linear-gradient(180deg, rgba(34, 197, 94, 0.24) 0%, rgba(22, 163, 74, 0.14) 100%);
  color: #14532d;
  border: 1px solid rgba(34, 197, 94, 0.55);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.75) inset,
    0 2px 6px rgba(22, 101, 52, 0.14);
}

.prow__status--off {
  background: linear-gradient(180deg, rgba(71, 85, 105, 0.14) 0%, rgba(51, 65, 85, 0.1) 100%);
  color: #1e293b;
  border: 1px solid rgba(100, 116, 139, 0.5);
}

.prow__status--on .prow__statusIco,
.prow__status--off .prow__statusIco {
  opacity: 0.92;
}

.prow__status--on .prow__statusLbl,
.prow__status--off .prow__statusLbl {
  font-weight: 800;
}

.prow__metaStack {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 6px;
}

.prow__row2 {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 0;
}

.prow__row2 :deep(.star-rating) {
  flex-shrink: 0;
}

.prow__visits {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  font-size: 0.6875rem;
  line-height: 1.2;
  color: #94a3b8;
  font-variant-numeric: tabular-nums;
}

.prow__visitsLabel {
  font-weight: 600;
  letter-spacing: 0.04em;
  color: #94a3b8;
}

.prow__visitsVal {
  font-weight: 700;
  color: #64748b;
}

.prow__rowPrice {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 6px;
}

.prow__priceBlock {
  display: inline-flex;
  flex-direction: row;
  align-items: baseline;
  gap: 0;
  line-height: 1.15;
}

.prow__priceYuan {
  font-size: 0.75rem;
  font-weight: 700;
  color: #dc2626;
  margin-right: 1px;
}

.prow__priceInt {
  font-size: 1.0625rem;
  font-weight: 800;
  color: #b91c1c;
  letter-spacing: -0.02em;
}

.prow__addr {
  flex: 1;
  margin: 0 0 8px;
  font-size: 0.75rem;
  color: #64748b;
  line-height: 1.45;
  min-height: 2.2em;
}

.prow__addrInner {
  display: flex;
  align-items: flex-start;
  gap: 5px;
}

.prow__addrIcon {
  color: #0ea5e9;
  flex-shrink: 0;
  margin-top: 1px;
}

.prow__addrText {
  flex: 1;
  min-width: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.prow__bottom {
  margin-top: auto;
  flex-shrink: 0;
}

.prow__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 6px;
}

.tagpill {
  font-size: 0.65rem;
  font-weight: 600;
  padding: 3px 7px;
  border-radius: 4px;
  background: #f8fafc;
  color: #475569;
  border: 1px solid #e2e8f0;
}

.prow__flags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

/* 商品角标：胶囊 + 渐变底 + 小图标，与筛选区矩形风格区分 */
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
  text-shadow: 0 1px 0 rgba(0, 0, 0, 0.1);
}

.badge--hot .badge__ico {
  opacity: 0.95;
}

.badge--rec {
  color: #fff;
  background: linear-gradient(135deg, #a5b4fc 0%, #6366f1 50%, #4f46e5 100%);
  border-color: rgba(255, 255, 255, 0.35);
  text-shadow: 0 1px 0 rgba(0, 0, 0, 0.1);
}

.badge--rec .badge__ico {
  opacity: 0.95;
}

.prow__dist {
  margin-top: 8px;
  display: flex;
  justify-content: flex-start;
}

/* 距离：独立胶囊，与地址/角标区分，提高对比与可扫读性 */
.prow__distChip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  padding: 6px 11px 6px 8px;
  border-radius: 999px;
  font-size: 0.8125rem;
  line-height: 1.2;
  font-weight: 600;
  color: #0c4a6e;
  background: linear-gradient(145deg, #e0f2fe 0%, #f0f9ff 55%, #e0f2fe 100%);
  border: 1px solid rgba(14, 165, 233, 0.35);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.85) inset,
    0 2px 8px rgba(14, 165, 233, 0.12);
}

.prow__distChip__ico {
  flex-shrink: 0;
  color: #0284c7;
}

.prow__distChip__label {
  flex-shrink: 0;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: #0369a1;
}

.prow__distChip__val {
  font-variant-numeric: tabular-nums;
  font-size: 0.9375rem;
  font-weight: 800;
  color: #075985;
  letter-spacing: -0.02em;
}

.prow__distChip__unit {
  font-size: 0.6875rem;
  font-weight: 700;
  color: #0369a1;
  margin-left: 1px;
}

.prow__distChip--na {
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
}

.plist__sentinel {
  height: 1px;
  margin: 0;
  padding: 0;
  overflow: hidden;
}

.plist__more {
  text-align: center;
  padding: 12px;
  font-size: 0.8125rem;
  color: #94a3b8;
}

.plist__empty {
  padding: 2rem 1rem;
  text-align: center;
  color: #64748b;
  font-size: 0.9rem;
}

.fab {
  --fab-offset: 20px;
  --fab-stack: 0px;
  position: fixed;
  right: 16px;
  bottom: calc(var(--fab-offset) + var(--fab-stack) + env(safe-area-inset-bottom, 0px));
  width: 56px;
  height: 56px;
  min-width: 44px;
  min-height: 44px;
  padding: 6px 4px;
  border-radius: 14px;
  border: 1px solid rgba(14, 165, 233, 0.35);
  background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
  color: #fff;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.15);
  cursor: pointer;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  touch-action: manipulation;
}

.fab__text {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  font-weight: 600;
  letter-spacing: 0.02em;
  line-height: 1.1;
  text-align: center;
}

.fab__line {
  display: block;
  font-size: 0.6875rem;
}

.fab__text--single {
  font-size: 0.8125rem;
  letter-spacing: 0.04em;
}

.fab--guide {
  --fab-stack: 0px;
}

.fab--bulletin {
  --fab-stack: 0px;
  border-color: rgba(245, 158, 11, 0.45);
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  box-shadow: 0 4px 16px rgba(180, 83, 9, 0.2);
}

.fab--bulletin--stacked {
  --fab-stack: calc(56px + 10px);
}

/* —— 宽屏：与后台一致的视口断点；列表双列 + 桌面 hover，不改动窄屏单列 —— */
@media (min-width: 1024px) {
  .plist {
    padding-bottom: calc(48px + env(safe-area-inset-bottom, 0px));
  }

  .plist__inner {
    max-width: none;
    padding-left: 0;
    padding-right: 0;
  }

  /* auto-fill：列更宽；同行等高，避免左侧图区与右侧信息区错位 */
  .plist__list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 18px;
    align-items: stretch;
  }

  .plist__list > .prow {
    margin-bottom: 0;
    align-items: stretch;
    min-height: 0;
    grid-template-columns: 140px minmax(0, 1fr);
    gap: 14px;
    padding: 14px;
    border-radius: 16px;
  }

  /* 有封面或有商品标签 / 两者皆无：两档统一最小高度（同行拉伸后仍保持信息区顶对齐） */
  .plist__list > .prow--deskH-rich {
    min-height: 240px;
  }

  .plist__list > .prow--deskH-plain {
    min-height: 240px;
  }

  .plist__list > .prow .prow__media {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
    min-height: 0;
    min-width: 0;
    align-self: start;
  }

  /* 封面高度约为宽的 130%（10:13），图片铺满裁切框 */
  .plist__list > .prow .prow__cover {
    width: 100%;
    min-height: 0;
    height: auto;
    aspect-ratio: 10 / 13;
    box-sizing: border-box;
    border-radius: 12px;
  }

  .plist__list > .prow .prow__cover img {
    min-height: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .plist__list > .prow .prow__noimg {
    min-height: 0;
    aspect-ratio: 10 / 13;
    height: auto;
  }

  .plist__list > .prow .prow__flags--underCover {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-start;
    gap: 5px;
    width: 100%;
    margin: 0;
  }

  .plist__list > .prow .prow__flags--underCover .badge {
    font-size: 0.5625rem;
    padding: 4px 7px 4px 5px;
  }

  .plist__list > .prow .prow__body {
    min-height: 0;
    height: 100%;
    padding-top: 2px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    box-sizing: border-box;
  }

  /*
   * 原因：窄屏用 flex:1 + margin-top:auto 把标签区贴底；桌面同行等高时 addr 被拉成长条，
   * 地址文字仍在块顶，标签在块底 → 中间出现大空白。宽屏取消「地址吃满剩余高度」与「底栏 auto」。
   */
  .plist__list > .prow .prow__addr {
    flex: 0 1 auto;
    min-height: 0;
    margin: 0 0 8px;
    font-size: 0.78125rem;
    line-height: 1.5;
  }

  .plist__list > .prow .prow__name {
    font-size: 0.96875rem;
    letter-spacing: -0.01em;
  }

  .plist__list > .prow .prow__bottom {
    margin-top: 0;
    flex-shrink: 0;
  }

  /* 商品标签多行时限制高度，避免右栏高度差过大 */
  .plist__list > .prow .prow__tags {
    max-height: 2.75rem;
    overflow: hidden;
    margin-bottom: 6px;
  }

  .filterDeck__surface {
    border-radius: 18px;
  }

  /* 与 app-shell 居中宽度对齐，浮标贴在内容区右缘内侧 */
  .fab--guide,
  .fab--bulletin {
    right: calc((100vw - min(var(--mweb-shell-max, 1440px), 100vw)) / 2 + 40px);
  }
}

@media (min-width: 1024px) and (prefers-reduced-motion: no-preference) {
  .prow:hover {
    transform: translateY(-2px);
    box-shadow:
      0 1px 0 rgba(255, 255, 255, 0.95) inset,
      0 14px 36px rgba(15, 23, 42, 0.1);
  }

  .prow--on:hover {
    box-shadow:
      0 0 0 2px rgba(34, 197, 94, 0.38),
      0 0 0 8px rgba(34, 197, 94, 0.14),
      0 0 0 18px rgba(34, 197, 94, 0.07),
      0 1px 0 rgba(255, 255, 255, 0.95) inset,
      0 14px 36px rgba(34, 197, 94, 0.16);
  }

  .prow--off:hover {
    box-shadow:
      0 0 0 2px rgba(148, 163, 184, 0.35),
      0 0 0 8px rgba(148, 163, 184, 0.12),
      0 0 0 18px rgba(148, 163, 184, 0.06),
      0 10px 28px rgba(15, 23, 42, 0.08);
  }

  .plist__searchBtn:hover {
    filter: brightness(1.03);
  }

  .filterSeg__btn:hover:not(.filterSeg__btn--on) {
    color: #334155;
    background: rgba(255, 255, 255, 0.35);
  }

  .fab--guide:hover {
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.14);
  }

  .fab--bulletin:hover {
    box-shadow: 0 8px 22px rgba(180, 83, 9, 0.28);
  }
}
</style>
