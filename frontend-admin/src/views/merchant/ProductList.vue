<template>
  <div class="page">
    <el-card class="panel" shadow="never">
      <div class="toolbar">
        <div class="toolbar-title">商品管理</div>
        <div class="toolbar-actions">
          <el-button @click="goTrash">回收站</el-button>
          <el-button @click="openCategoryDialog">商品分类</el-button>
          <el-button type="primary" @click="goCreate">新增商品</el-button>
        </div>
      </div>

      <div class="filter">
        <el-input
          v-model="keyword"
          clearable
          class="filter-input"
          placeholder="商品名称"
          @clear="doSearch"
          @keyup.enter="doSearch"
        />
        <el-input
          v-model="district"
          clearable
          class="filter-input filter-input--district"
          placeholder="所属区域"
          @clear="doSearch"
          @keyup.enter="doSearch"
        />
        <el-select
          v-model="statusFilter"
          clearable
          class="filter-select"
          placeholder="商品状态"
          @clear="doSearch"
          @change="doSearch"
        >
          <el-option label="上架" value="on" />
          <el-option label="下架" value="off" />
        </el-select>
        <el-button type="primary" plain @click="doSearch">查询</el-button>
      </div>

      <div class="table-scroll-wrap">
        <div
          v-show="showTableHScroll"
          ref="topScrollRef"
          class="scroll-h-bar scroll-h-bar--top"
          aria-hidden="true"
          @scroll="onTopHScroll"
        >
          <div class="scroll-h-bar__inner" :style="{ width: `${tableScrollMirrorWidth}px` }" />
        </div>
        <div
          ref="tableScrollRef"
          class="table-scroll"
          @scroll="onMainTableScroll"
        >
        <el-table
          v-loading="loading"
          :data="items"
          border
          class="pwd-table table-scroll-inner"
          table-layout="auto"
          @header-dragend="tw.onHeaderDragEnd"
        >
        <el-table-column column-key="cover" label="封面" v-bind="tw.col('cover', { width: 88 })">
          <template #default="{ row }">
            <el-image
              v-if="row.coverImage"
              :src="row.coverImage"
              fit="cover"
              class="thumb"
              :preview-src-list="[row.coverImage]"
              preview-teleported
            />
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column
          column-key="name"
          prop="name"
          label="商品名称"
          v-bind="tw.col('name', { minWidth: 160 })"
          class-name="col-text-wrap"
        />
        <el-table-column column-key="sortOrder" label="排序号" v-bind="tw.col('sortOrder', { width: 108 })" align="center">
          <template #default="{ row }">
            <el-input
              v-model="sortOrderDraft[row.id]"
              size="small"
              maxlength="7"
              inputmode="numeric"
              class="sort-order-input"
              :disabled="sortOrderBusyId === row.id"
              @focus="onSortOrderFocus(row)"
              @blur="onSortOrderBlur(row)"
            />
          </template>
        </el-table-column>
        <el-table-column
          column-key="city"
          prop="city"
          label="所属城市"
          v-bind="tw.col('city', { minWidth: 112 })"
          class-name="col-text-wrap"
        />
        <el-table-column
          column-key="district"
          prop="district"
          label="所属区域"
          v-bind="tw.col('district', { minWidth: 120 })"
          class-name="col-text-wrap"
        />
        <el-table-column
          column-key="address"
          prop="address"
          label="商品地址"
          v-bind="tw.col('address', { minWidth: 220 })"
          class-name="col-text-wrap"
        />
        <el-table-column column-key="flag3" label="显示隐藏" v-bind="tw.col('flag3', { width: 168 })" align="center">
          <template #default="{ row }">
            <div class="product-list-switch">
              <el-switch
                :model-value="row.flag3"
                size="default"
                inline-prompt
                active-text="显示"
                inactive-text="隐藏"
                :disabled="flagBusyKey === `${row.id}-flag3`"
                @change="(v: boolean) => onProductFlagChange(row, 'flag3', v)"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column column-key="status" label="状态" v-bind="tw.col('status', { width: 168 })" align="center">
          <template #default="{ row }">
            <div class="product-list-switch">
              <el-switch
                :model-value="row.status === 'on'"
                size="default"
                inline-prompt
                active-text="上架"
                inactive-text="下架"
                :disabled="statusBusyId === row.id"
                @change="(v: boolean) => onProductStatusChange(row, v ? 'on' : 'off')"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column column-key="flag1" label="热门商品" v-bind="tw.col('flag1', { width: 132 })" align="center">
          <template #default="{ row }">
            <div class="product-list-switch">
              <el-switch
                :model-value="row.flag1"
                size="default"
                inline-prompt
                active-text="是"
                inactive-text="否"
                :disabled="flagBusyKey === `${row.id}-flag1`"
                @change="(v: boolean) => onProductFlagChange(row, 'flag1', v)"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column column-key="flag2" label="推荐商品" v-bind="tw.col('flag2', { width: 132 })" align="center">
          <template #default="{ row }">
            <div class="product-list-switch">
              <el-switch
                :model-value="row.flag2"
                size="default"
                inline-prompt
                active-text="是"
                inactive-text="否"
                :disabled="flagBusyKey === `${row.id}-flag2`"
                @change="(v: boolean) => onProductFlagChange(row, 'flag2', v)"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column column-key="actions" label="操作" v-bind="tw.col('actions', { minWidth: 140 })" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goEdit(row.id)">编辑</el-button>
            <el-button link type="danger" @click="confirmDelete(row)">删除</el-button>
          </template>
        </el-table-column>
        </el-table>
        </div>
        <p v-if="showTableHScroll" class="table-scroll-hint">横向查看：拖动顶部滚动条，或在表格区域按住 Shift 再滚动鼠标滚轮</p>
      </div>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next, sizes"
          :page-sizes="[10, 20, 50]"
          @current-change="load"
          @size-change="load"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="catDialog.visible"
      width="600px"
      class="cat-dialog"
      destroy-on-close
      align-center
      @open="loadCategories"
    >
      <template #header>
        <div class="cat-dialog-head">
          <span class="cat-dialog-title">商品分类管理</span>
          <el-button type="primary" :loading="catDialog.adding" @click="addCategory">新增分类</el-button>
        </div>
      </template>
      <el-table :data="catDialog.rows" border stripe class="cat-table" @header-dragend="twCat.onHeaderDragEnd">
        <el-table-column
          column-key="cat-type"
          prop="typeCode"
          label="类型码"
          v-bind="twCat.col('cat-type', { width: 96 })"
          align="center"
        />
        <el-table-column column-key="cat-name" label="商品分类" v-bind="twCat.col('cat-name', { minWidth: 200 })">
          <template #default="{ row }">
            <el-input v-model="row.name" maxlength="120" show-word-limit size="small" clearable />
          </template>
        </el-table-column>
        <el-table-column column-key="cat-actions" label="操作" v-bind="twCat.col('cat-actions', { width: 88 })" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="danger"
              :loading="catDialog.deletingId === row.id"
              @click="deleteCategory(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="catDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="catDialog.saving" @click="saveCategories">保存名称</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { nextTick, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { http } from "@/api/http";
import { usePersistedTableWidths } from "@/composables/usePersistedTableWidths";
import type { ProductCategory, ProductListItem } from "@/types/merchant";

const tw = usePersistedTableWidths("merchant-products");
const twCat = usePersistedTableWidths("merchant-products-category-dialog");

const router = useRouter();
const loading = ref(false);
const items = ref<ProductListItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const keyword = ref("");
const district = ref("");
/** 未选 = 全部；on / off 按上架下架筛选 */
const statusFilter = ref<"on" | "off" | undefined>(undefined);
const statusBusyId = ref<number | null>(null);
const flagBusyKey = ref<string | null>(null);
/** 失焦保存排序号时：与 @focus 时快照比较 */
const sortOrderAtFocus = reactive<Record<number, number>>({});
/** 列表内文本框展示，与 row.sortOrder 同步于 load / 保存后 */
const sortOrderDraft = reactive<Record<number, string>>({});
const sortOrderBusyId = ref<number | null>(null);

/** 宽表：顶部同步横向滚动条 + Shift+滚轮（见 onMounted 非 passive 监听） */
const tableScrollRef = ref<HTMLElement | null>(null);
const topScrollRef = ref<HTMLElement | null>(null);
const showTableHScroll = ref(false);
const tableScrollMirrorWidth = ref(0);
let _hScrollSyncing = false;
let _tableScrollResizeObserver: ResizeObserver | null = null;
let _tableWheelHandler: ((e: WheelEvent) => void) | null = null;

function syncTableScrollMetrics() {
  const el = tableScrollRef.value;
  if (!el) return;
  tableScrollMirrorWidth.value = el.scrollWidth;
  showTableHScroll.value = el.scrollWidth > el.clientWidth + 2;
}

function onMainTableScroll() {
  const main = tableScrollRef.value;
  const top = topScrollRef.value;
  if (!main || !top) return;
  if (_hScrollSyncing) return;
  _hScrollSyncing = true;
  top.scrollLeft = main.scrollLeft;
  _hScrollSyncing = false;
}

function onTopHScroll() {
  const main = tableScrollRef.value;
  const top = topScrollRef.value;
  if (!main || !top) return;
  if (_hScrollSyncing) return;
  _hScrollSyncing = true;
  main.scrollLeft = top.scrollLeft;
  _hScrollSyncing = false;
}

const catDialog = reactive({
  visible: false,
  saving: false,
  adding: false,
  deletingId: null as number | null,
  rows: [] as { id: number; typeCode: number; name: string }[],
});

function openCategoryDialog() {
  catDialog.visible = true;
}

async function loadCategories() {
  try {
    const { data } = await http.get<{ data: { items: ProductCategory[] } }>("/merchant/product-categories");
    catDialog.rows = (data?.data?.items || []).map((c) => ({
      id: c.id,
      typeCode: c.typeCode,
      name: c.name,
    }));
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "加载分类失败");
  }
}

async function saveCategories() {
  catDialog.saving = true;
  try {
    for (const row of catDialog.rows) {
      const name = row.name.trim();
      if (!name) {
        ElMessage.warning("分类名称不能为空");
        return;
      }
      await http.put(`/merchant/product-categories/${row.id}`, { name });
    }
    ElMessage.success("已保存");
    catDialog.visible = false;
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "保存失败");
  } finally {
    catDialog.saving = false;
  }
}

async function addCategory() {
  try {
    const { value } = await ElMessageBox.prompt("请输入分类名称", "新增分类", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      inputValue: "新分类",
      inputValidator: (v) => {
        if (!v || !String(v).trim()) return "请输入名称";
        return true;
      },
    });
    catDialog.adding = true;
    await http.post("/merchant/product-categories", { name: String(value).trim() });
    ElMessage.success("已新增分类");
    await loadCategories();
  } catch (e: unknown) {
    if (e === "cancel") return;
    ElMessage.error(e instanceof Error ? e.message : "添加失败");
  } finally {
    catDialog.adding = false;
  }
}

async function deleteCategory(row: { id: number; name: string }) {
  try {
    await ElMessageBox.confirm(`确定删除分类「${row.name}」吗？删除后不可恢复。`, "删除分类", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  catDialog.deletingId = row.id;
  try {
    await http.delete(`/merchant/product-categories/${row.id}`);
    ElMessage.success("已删除");
    await loadCategories();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "删除失败");
  } finally {
    catDialog.deletingId = null;
  }
}

async function onProductFlagChange(row: ProductListItem, key: "flag1" | "flag2" | "flag3", val: boolean) {
  if (Boolean(row[key]) === val) return;
  flagBusyKey.value = `${row.id}-${key}`;
  try {
    await http.put(`/merchant/products/${row.id}`, { [key]: val });
    row[key] = val;
    ElMessage.success("已更新");
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "更新失败");
    await load();
  } finally {
    flagBusyKey.value = null;
  }
}

async function onProductStatusChange(row: ProductListItem, status: "on" | "off") {
  if (row.status === status) return;
  statusBusyId.value = row.id;
  try {
    await http.put(`/merchant/products/${row.id}`, { status });
    row.status = status;
    ElMessage.success("状态已更新");
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "更新失败");
    await load();
  } finally {
    statusBusyId.value = null;
  }
}

function onSortOrderFocus(row: ProductListItem) {
  sortOrderAtFocus[row.id] = row.sortOrder;
}

function parseSortOrderText(raw: string): number | null {
  const s = raw.trim();
  if (s === "") return null;
  const n = Number(s);
  if (!Number.isFinite(n) || n < 0 || !Number.isInteger(n)) return null;
  if (n > 9999999) return null;
  return n;
}

async function onSortOrderBlur(row: ProductListItem) {
  const prev = sortOrderAtFocus[row.id];
  const draft = sortOrderDraft[row.id] ?? "";
  const n = parseSortOrderText(draft);
  if (n === null) {
    row.sortOrder = prev ?? 0;
    sortOrderDraft[row.id] = String(prev ?? 0);
    ElMessage.warning("请输入 0～9999999 的整数排序号");
    return;
  }
  if (prev !== undefined && n === prev) return;
  sortOrderBusyId.value = row.id;
  try {
    await http.put(`/merchant/products/${row.id}`, { sortOrder: n });
    row.sortOrder = n;
    sortOrderDraft[row.id] = String(n);
    sortOrderAtFocus[row.id] = n;
    ElMessage.success("排序号已保存");
  } catch (e: unknown) {
    row.sortOrder = prev ?? 0;
    sortOrderDraft[row.id] = String(prev ?? 0);
    ElMessage.error(e instanceof Error ? e.message : "保存失败");
  } finally {
    sortOrderBusyId.value = null;
  }
}

function doSearch() {
  page.value = 1;
  void load();
}

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get("/merchant/products", {
      params: {
        page: page.value,
        pageSize: pageSize.value,
        keyword: keyword.value.trim() || undefined,
        district: district.value.trim() || undefined,
        status: statusFilter.value || undefined,
      },
    });
    items.value = data?.data?.items || [];
    total.value = data?.data?.total ?? 0;
    for (const it of items.value) {
      sortOrderAtFocus[it.id] = it.sortOrder;
      sortOrderDraft[it.id] = String(it.sortOrder);
    }
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "加载失败");
  } finally {
    loading.value = false;
    await nextTick();
    syncTableScrollMetrics();
  }
}

function goCreate() {
  void router.push({ name: "merchant-product-create" });
}

function goTrash() {
  void router.push({ name: "merchant-products-trash" });
}

function goEdit(id: number) {
  void router.push({ name: "merchant-product-edit", params: { id: String(id) } });
}

async function confirmDelete(row: ProductListItem) {
  await ElMessageBox.confirm(`确定将「${row.name}」移入回收站吗？可在回收站恢复。`, "删除商品", {
    type: "warning",
  });
  try {
    await http.delete(`/merchant/products/${row.id}`);
    ElMessage.success("已移入回收站");
    await load();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "删除失败");
  }
}

function setupTableHScroll() {
  const el = tableScrollRef.value;
  if (!el || _tableWheelHandler) return;
  _tableWheelHandler = (e: WheelEvent) => {
    if (!e.shiftKey) return;
    el.scrollLeft += e.deltaY;
    onMainTableScroll();
    e.preventDefault();
  };
  el.addEventListener("wheel", _tableWheelHandler, { passive: false });
  _tableScrollResizeObserver = new ResizeObserver(() => {
    syncTableScrollMetrics();
  });
  _tableScrollResizeObserver.observe(el);
}

onMounted(() => {
  nextTick(() => {
    setupTableHScroll();
    void load();
  });
});

onUnmounted(() => {
  const el = tableScrollRef.value;
  if (el && _tableWheelHandler) {
    el.removeEventListener("wheel", _tableWheelHandler);
  }
  _tableWheelHandler = null;
  _tableScrollResizeObserver?.disconnect();
  _tableScrollResizeObserver = null;
});

watch(
  () => items.value.length,
  () => {
    nextTick(() => syncTableScrollMetrics());
  },
);
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

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.filter {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 12px;
  align-items: center;
  margin-bottom: 14px;
}

.filter-input {
  max-width: 260px;
}

.filter-input--district {
  max-width: 220px;
}

.filter-select {
  width: 140px;
}

.cat-dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding-right: 32px;
}

.cat-dialog-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.cat-table {
  width: 100%;
}

.thumb {
  width: 56px;
  height: 56px;
  border-radius: 8px;
}

.muted {
  color: rgba(15, 23, 42, 0.45);
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* 表格内居中；开关外观完全使用 Element Plus 默认样式（size=default，高度大于 small） */
.product-list-switch {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2px 0;
}

/* 开启态：使用主题 success 绿，避免默认 primary 蓝（与 Element Plus 语义色一致） */
.product-list-switch :deep(.el-switch) {
  --el-switch-on-color: var(--el-color-success);
}

.sort-order-input {
  width: 100%;
  max-width: 88px;
  margin: 0 auto;
}

.sort-order-input :deep(.el-input__wrapper) {
  min-height: 32px;
  padding: 1px 10px;
  border-radius: 8px;
  box-sizing: border-box;
}

.sort-order-input :deep(.el-input__inner) {
  height: 30px;
  line-height: 30px;
  text-align: center;
}

.table-scroll-wrap {
  width: 100%;
}

.scroll-h-bar {
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: thin;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.04);
  border: 1px solid rgba(15, 23, 42, 0.08);
}

.scroll-h-bar--top {
  height: 14px;
  margin-bottom: 8px;
}

.scroll-h-bar__inner {
  height: 1px;
  pointer-events: none;
}

.table-scroll {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  touch-action: pan-x pan-y;
}

.table-scroll-inner {
  min-width: 1280px;
}

.table-scroll-hint {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.45;
  color: rgba(15, 23, 42, 0.48);
}

.table-scroll-inner :deep(.col-text-wrap .cell) {
  white-space: normal;
  word-break: break-word;
  line-height: 1.45;
}
</style>
