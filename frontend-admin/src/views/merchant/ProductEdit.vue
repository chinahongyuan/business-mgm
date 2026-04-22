<template>
  <div class="page">
    <el-card v-loading="pageLoading" class="panel" shadow="never">
      <template #header>
        <div class="card-head">
          <span class="toolbar-title">{{ isEdit ? "编辑商品" : "新增商品" }}</span>
          <div class="head-actions">
            <el-button @click="goBack">返回列表</el-button>
            <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
          </div>
        </div>
      </template>

      <el-form label-width="120px" class="form product-form">
        <section class="form-section">
          <h3 class="form-section-title">基础信息</h3>
          <el-row :gutter="20">
            <el-col :xs="24" :lg="14">
              <el-form-item label="商品名称" required>
                <el-input v-model="form.name" maxlength="255" show-word-limit placeholder="商品名称" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :xs="24" :lg="14">
              <el-form-item label="商品分类" required>
                <el-select v-model="form.categoryId" placeholder="选择分类" style="width: 100%">
                  <el-option
                    v-for="c in categories"
                    :key="c.id"
                    :label="`${c.name}（类型 ${c.typeCode}）`"
                    :value="c.id"
                  />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="封面图">
            <div class="cover-row">
              <el-upload
                class="cover-uploader"
                :show-file-list="false"
                accept="image/*"
                :http-request="onCoverUpload"
              >
                <el-image v-if="form.coverImage" :src="form.coverImage" fit="cover" class="cover-preview" />
                <el-icon v-else class="cover-placeholder"><Plus /></el-icon>
              </el-upload>
              <div class="cover-hint">点击上传封面，建议比例 1:1</div>
            </div>
          </el-form-item>
          <div class="field-inline-group field-inline-group--status-price">
            <el-form-item label="商品状态" class="field-inline-item">
              <el-radio-group v-model="form.status">
                <el-radio value="on">上架</el-radio>
                <el-radio value="off">下架</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="商品星级" class="field-inline-item">
              <el-rate v-model="form.starRating" :max="5" show-score clearable />
            </el-form-item>
            <el-form-item label="商品价格" class="field-inline-item">
              <el-input-number
                v-model="form.price"
                :min="0"
                :precision="0"
                :step="1"
                controls-position="right"
                class="input-num-price"
                placeholder="请输入价格"
                value-on-clear
              />
            </el-form-item>
          </div>
          <el-form-item label="商品标签" class="form-item-tags">
            <div v-if="allTags.length" class="tag-field">
              <el-checkbox-group v-model="form.tagIds" class="tag-group">
                <el-checkbox v-for="t in allTags" :key="t.id" :value="t.id" border size="small">
                  {{ t.name }}
                </el-checkbox>
              </el-checkbox-group>
            </div>
            <div v-else class="muted tag-empty">暂无标签，请先在「标签管理」中维护</div>
          </el-form-item>
          <div class="field-inline-group field-inline-group--sort-visit">
            <el-form-item label="排序号" class="field-inline-item">
              <el-input-number
                v-model="form.sortOrder"
                :min="0"
                :max="9999999"
                controls-position="right"
                class="input-num-tight"
              />
            </el-form-item>
            <el-form-item label="访问数" class="field-inline-item field-inline-item--visit">
              <div class="inline-hint">
                <el-input-number v-model="form.visitCount" :min="0" controls-position="right" class="input-num-tight" />
                <span class="field-hint">预留统计，移动端接入后可自动累加</span>
              </div>
            </el-form-item>
          </div>
        </section>

        <section class="form-section">
          <h3 class="form-section-title">区域与地址</h3>
        <!-- 等 /api/public/config 写入 mapAk 后再挂载，避免首屏 ak 为空导致 bootstrap 早退、永远不注入百度脚本 -->
        <div v-if="!mapMetaLoaded" class="map-meta-wait">正在加载地图配置…</div>
        <BaiduMapRegion
          v-else-if="mapAk"
          :key="mapAk"
          ref="mapRef"
          :ak="mapAk"
          :province="form.province"
          :city="form.city"
          :district="form.district"
          :longitude="form.longitude"
          :latitude="form.latitude"
          @update:province="(v) => (form.province = v)"
          @update:city="(v) => (form.city = v)"
          @update:district="(v) => (form.district = v)"
          @update:longitude="(v) => (form.longitude = v)"
          @update:latitude="(v) => (form.latitude = v)"
          @update:address="(v) => (form.address = v)"
        />
        <el-alert
          v-else
          type="warning"
          show-icon
          :closable="false"
          title="未配置百度地图 AK"
          description="config.json 中 baidu_map.ak 为空或后端未加载配置，Network 中不会出现 api.map.baidu.com 请求。"
        />
        <el-row :gutter="16" class="row-region">
          <el-col :xs="24" :md="8">
            <el-form-item label="所属省份">
              <el-input v-model="form.province" placeholder="省" clearable class="input-region" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="8">
            <el-form-item label="所属城市">
              <el-input v-model="form.city" placeholder="市" clearable class="input-region" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="8">
            <el-form-item label="所属区域">
              <el-input v-model="form.district" placeholder="区" clearable class="input-region" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="经纬度" class="form-item-lnglat">
          <div class="lnglat-row">
            <el-input-number v-model="lngModel" :precision="6" :step="0.000001" controls-position="right" class="input-num-lnglat" />
            <span class="sep">,</span>
            <el-input-number v-model="latModel" :precision="6" :step="0.000001" controls-position="right" class="input-num-lnglat" />
            <span class="field-hint">修改后地图标记会自动同步</span>
          </div>
        </el-form-item>
        <el-form-item label="商品地址">
          <div class="addr-field-wrap">
            <el-input
              v-model="form.address"
              type="textarea"
              :rows="3"
              placeholder="输入至少 2 个字可显示南京市范围内预选；点选某条后才会写入地址；地图点击选点会同步逆地理编码地址"
              class="addr-textarea"
              @input="onAddressInput"
              @blur="onAddressSuggestBlur"
            />
            <div v-if="addressSuggestions.length" class="addr-suggest-panel" role="listbox" aria-label="地址预选">
              <button
                v-for="(s, idx) in addressSuggestions"
                :key="idx"
                type="button"
                class="addr-suggest-item"
                @mousedown.prevent="pickAddressSuggestion(s)"
              >
                <span class="addr-suggest-title">{{ s.title || "—" }}</span>
                <span v-if="s.address" class="addr-suggest-sub">{{ s.address }}</span>
              </button>
            </div>
          </div>
        </el-form-item>
        </section>

        <section class="form-section">
          <h3 class="form-section-title">商品详情</h3>
          <el-form-item label="商品详情" class="form-item-detail">
            <RichTextEditor v-model="form.detailHtml" class="editor-block" />
          </el-form-item>
        </section>

        <section class="form-section form-section--last">
          <h3 class="form-section-title">扩展开关</h3>
          <el-row :gutter="24">
            <el-col :xs="24" :sm="8">
              <el-form-item label="热门商品">
                <el-switch v-model="form.flag1" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="8">
              <el-form-item label="推荐商品">
                <el-switch v-model="form.flag2" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="8">
              <el-form-item label="显示隐藏">
                <el-switch v-model="form.flag3" />
              </el-form-item>
            </el-col>
          </el-row>
        </section>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { Plus } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import type { UploadRequestOptions } from "element-plus";
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { http } from "@/api/http";
import BaiduMapRegion from "@/components/BaiduMapRegion.vue";
import RichTextEditor from "@/components/RichTextEditor.vue";
import type { ProductCategory, ProductDetail, ProductTag } from "@/types/merchant";

const route = useRoute();
const router = useRouter();

const pageLoading = ref(false);
const saving = ref(false);
const mapAk = ref("");
/** loadMeta 完成后再决定是否挂载地图，避免 ak 尚未返回时子组件已 onMounted 早退 */
const mapMetaLoaded = ref(false);
const categories = ref<ProductCategory[]>([]);
const allTags = ref<ProductTag[]>([]);
type MapPoiSuggestion = {
  title: string;
  address: string;
  lng: number;
  lat: number;
};

const mapRef = ref<{
  searchAddress: (a: string) => void;
  fetchPoiSuggestions: (k: string) => Promise<MapPoiSuggestion[]>;
  focusOnLngLat: (lng: number, lat: number, addressOverride?: string | null) => void;
} | null>(null);

const addressSuggestions = ref<MapPoiSuggestion[]>([]);
let addressInputDebounce: ReturnType<typeof setTimeout> | null = null;

const productId = computed(() => {
  const p = route.params.id;
  if (!p || p === "create") return null;
  const n = Number(p);
  return Number.isFinite(n) ? n : null;
});
const isEdit = computed(() => productId.value != null);

const form = reactive({
  name: "",
  coverImage: "",
  categoryId: undefined as number | undefined,
  status: "on",
  tagIds: [] as number[],
  starRating: 0,
  price: undefined as number | undefined,
  province: "",
  city: "",
  district: "",
  longitude: null as number | null,
  latitude: null as number | null,
  address: "",
  detailHtml: "",
  sortOrder: 0,
  visitCount: 0,
  flag1: false,
  flag2: false,
  /** 新增默认「显示」 */
  flag3: true,
});

const lngModel = computed({
  get: () => form.longitude ?? undefined,
  set: (v) => {
    form.longitude = v ?? null;
  },
});
const latModel = computed({
  get: () => form.latitude ?? undefined,
  set: (v) => {
    form.latitude = v ?? null;
  },
});

function goBack() {
  void router.push({ name: "merchant-products" });
}

async function loadMeta() {
  try {
    const [{ data: cfg }, { data: cats }, { data: tags }] = await Promise.all([
      http.get<{ data: { baiduMapAk: string; _debug?: Record<string, unknown> } }>("/public/config"),
      http.get<{ data: { items: ProductCategory[] } }>("/merchant/product-categories"),
      http.get<{ data: { items: ProductTag[] } }>("/merchant/tags/all"),
    ]);
    mapAk.value = cfg?.data?.baiduMapAk || "";
    if (import.meta.env.DEV && cfg?.data?._debug) {
      console.info("[BaiduMap] /api/public/config _debug", cfg.data._debug);
    }
    if (import.meta.env.DEV && !String(mapAk.value || "").trim()) {
      console.warn(
        "[BaiduMap] baiduMapAk 为空，不会请求 api.map.baidu.com。请查看上条 _debug 与 Flask 控制台 config.json 路径。",
      );
    }
    categories.value = cats?.data?.items || [];
    allTags.value = tags?.data?.items || [];
    if (!form.categoryId && categories.value.length) {
      form.categoryId = categories.value[0].id;
    }
  } finally {
    mapMetaLoaded.value = true;
  }
}

function applyProduct(p: ProductDetail) {
  form.name = p.name;
  form.coverImage = p.coverImage || "";
  form.categoryId = p.categoryId;
  form.status = p.status;
  form.tagIds = [...(p.tagIds || [])];
  form.starRating = p.starRating;
  form.price = p.price != null ? Math.round(Number(p.price)) : undefined;
  form.province = p.province || "";
  form.city = p.city || "";
  form.district = p.district || "";
  form.longitude = p.longitude;
  form.latitude = p.latitude;
  form.address = p.address || "";
  form.detailHtml = p.detailHtml || "";
  form.sortOrder = p.sortOrder;
  form.visitCount = p.visitCount;
  form.flag1 = p.flag1;
  form.flag2 = p.flag2;
  form.flag3 = p.flag3;
}

async function loadProduct() {
  if (!productId.value) return;
  const { data } = await http.get<{ data: ProductDetail }>(`/merchant/products/${productId.value}`);
  if (data?.data) applyProduct(data.data);
}

async function onCoverUpload(opt: UploadRequestOptions) {
  const fd = new FormData();
  fd.append("file", opt.file);
  const { data } = await http.post<{ data: { url: string } }>("/upload", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  form.coverImage = data.data.url;
}

/** 仅拉取南京市范围内预选，不自动写入商品地址（须点选某条） */
function onAddressInput() {
  if (addressInputDebounce) clearTimeout(addressInputDebounce);
  addressInputDebounce = setTimeout(async () => {
    const q = form.address.trim();
    if (q.length < 2) {
      addressSuggestions.value = [];
      return;
    }
    if (!mapRef.value) return;
    try {
      addressSuggestions.value = await mapRef.value.fetchPoiSuggestions(q);
    } catch {
      addressSuggestions.value = [];
    }
  }, 380);
}

function onAddressSuggestBlur() {
  window.setTimeout(() => {
    addressSuggestions.value = [];
  }, 200);
}

function pickAddressSuggestion(s: MapPoiSuggestion) {
  addressSuggestions.value = [];
  const line =
    [s.address, s.title].filter((x) => x && String(x).trim()).join(" ").trim() || s.title || "";
  mapRef.value?.focusOnLngLat(s.lng, s.lat, line || null);
}

onBeforeUnmount(() => {
  if (addressInputDebounce) clearTimeout(addressInputDebounce);
});

async function submit() {
  if (!form.name.trim()) {
    ElMessage.warning("请填写商品名称");
    return;
  }
  if (form.categoryId == null) {
    ElMessage.warning("请选择分类");
    return;
  }
  if (form.price === undefined || form.price === null || !Number.isFinite(Number(form.price))) {
    ElMessage.warning("请填写商品价格");
    return;
  }
  const priceInt = Math.round(Number(form.price));
  if (priceInt < 0) {
    ElMessage.warning("商品价格不能为负数");
    return;
  }
  saving.value = true;
  try {
    const payload = {
      name: form.name.trim(),
      coverImage: form.coverImage || null,
      categoryId: form.categoryId,
      status: form.status,
      tagIds: form.tagIds,
      starRating: form.starRating,
      price: priceInt,
      province: form.province || null,
      city: form.city || null,
      district: form.district || null,
      longitude: form.longitude,
      latitude: form.latitude,
      address: form.address || null,
      detailHtml: form.detailHtml,
      sortOrder: form.sortOrder,
      visitCount: form.visitCount,
      flag1: form.flag1,
      flag2: form.flag2,
      flag3: form.flag3,
    };
    if (isEdit.value && productId.value) {
      await http.put(`/merchant/products/${productId.value}`, payload);
    } else {
      await http.post("/merchant/products", payload);
    }
    ElMessage.success("已保存");
    void router.push({ name: "merchant-products" });
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "保存失败");
  } finally {
    saving.value = false;
  }
}

onMounted(async () => {
  pageLoading.value = true;
  try {
    await loadMeta();
    await loadProduct();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "加载失败");
  } finally {
    pageLoading.value = false;
  }
});
</script>

<style scoped>
.page {
  padding: 20px;
}

.panel {
  border-radius: var(--bm-radius, 12px);
  box-shadow: var(--bm-shadow);
  border: var(--bm-border);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.toolbar-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.head-actions {
  display: flex;
  gap: 8px;
}

.product-form {
  max-width: 100%;
}

.form-section {
  margin-bottom: 28px;
}

.form-section--last {
  margin-bottom: 0;
}

.form-section-title {
  margin: 0 0 16px;
  padding-bottom: 10px;
  font-size: 14px;
  font-weight: 650;
  letter-spacing: 0.02em;
  color: rgba(15, 23, 42, 0.72);
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.form-item-detail :deep(.el-form-item__content) {
  max-width: 100%;
}

.muted {
  font-size: 13px;
  color: rgba(15, 23, 42, 0.5);
}

.field-hint {
  margin-left: 0;
  font-size: 12px;
  line-height: 1.45;
  color: rgba(15, 23, 42, 0.5);
}

.inline-hint {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
}

.field-inline-group {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
}

.field-inline-group--status-price {
  gap: 4px 18px;
  margin-bottom: 4px;
}

.field-inline-group--sort-visit {
  gap: 6px 28px;
}

.field-inline-group .field-inline-item {
  flex: 0 1 auto;
  margin-bottom: 0;
}

.field-inline-group .field-inline-item :deep(.el-form-item__label) {
  padding-right: 6px;
}

.field-inline-item--visit {
  flex: 0 1 auto;
  min-width: 0;
  max-width: 100%;
}

.field-inline-item--visit .inline-hint {
  gap: 8px 12px;
}

@media (max-width: 767px) {
  .field-inline-group {
    flex-direction: column;
    gap: 14px;
  }

  .field-inline-group .field-inline-item {
    width: 100%;
  }
}

.input-num-tight {
  width: 132px;
}

.input-num-price {
  width: 160px;
}

.input-num-lnglat {
  width: 200px;
}

.lnglat-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 10px;
}

.form-item-lnglat .field-hint {
  flex-basis: 100%;
  margin-top: 2px;
}

@media (min-width: 768px) {
  .form-item-lnglat .field-hint {
    flex-basis: auto;
    margin-top: 0;
    margin-left: 4px;
  }
}

.row-region .input-region {
  width: 100%;
  max-width: 280px;
}

.form-item-tags :deep(.el-form-item__content) {
  align-items: flex-start;
}

.tag-field {
  width: 100%;
  max-width: 720px;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-blank);
  box-sizing: border-box;
}

.tag-empty {
  padding: 10px 0;
}

.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 10px;
  align-items: center;
}

.tag-group :deep(.el-checkbox) {
  margin-right: 0;
  height: auto;
}

.tag-group :deep(.el-checkbox.is-bordered) {
  padding: 6px 12px;
  border-radius: 8px;
}

/* 未选中：跟随 EP 主文字色（浅色模式正常；深色模式由 theme-dark.css 加强） */
.tag-group :deep(.el-checkbox.is-bordered .el-checkbox__label) {
  color: var(--el-text-color-primary);
  font-weight: 500;
}

.cover-row {
  display: flex;
  align-items: flex-end;
  gap: 16px;
}

.cover-uploader :deep(.el-upload) {
  border: 1px dashed rgba(15, 23, 42, 0.2);
  border-radius: 12px;
  cursor: pointer;
  width: 120px;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.6);
  transition: border-color 0.2s ease;
}

.cover-uploader :deep(.el-upload:hover) {
  border-color: rgba(37, 99, 235, 0.45);
}

.cover-preview {
  width: 120px;
  height: 120px;
  border-radius: 12px;
}

.cover-placeholder {
  font-size: 28px;
  color: rgba(15, 23, 42, 0.35);
}

.cover-hint {
  font-size: 12px;
  color: rgba(15, 23, 42, 0.5);
}

.sep {
  margin: 0 6px;
  color: rgba(15, 23, 42, 0.45);
}

.addr-field-wrap {
  position: relative;
  max-width: 640px;
  width: 100%;
}

.addr-textarea {
  width: 100%;
}

.addr-suggest-panel {
  position: absolute;
  left: 0;
  right: 0;
  top: 100%;
  margin-top: 4px;
  z-index: 20;
  max-height: 240px;
  overflow-y: auto;
  border-radius: 10px;
  border: 1px solid var(--el-border-color);
  background: var(--el-bg-color-overlay);
  color: var(--el-text-color-primary);
  box-shadow: var(--el-box-shadow-light);
}

.addr-suggest-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  width: 100%;
  padding: 10px 12px;
  margin: 0;
  border: none;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: transparent;
  text-align: left;
  cursor: pointer;
  font-size: 13px;
  line-height: 1.4;
  color: var(--el-text-color-primary);
  transition: background 0.15s ease;
}

.addr-suggest-item:last-child {
  border-bottom: none;
}

.addr-suggest-item:hover,
.addr-suggest-item:focus-visible {
  background: var(--el-fill-color-light);
  outline: none;
}

.addr-suggest-title {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.addr-suggest-sub {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.editor-block {
  width: 100%;
}

.map-meta-wait {
  padding: 12px 0;
  font-size: 13px;
  color: rgba(15, 23, 42, 0.55);
}
</style>
