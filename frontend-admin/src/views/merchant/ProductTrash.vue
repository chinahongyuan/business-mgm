<template>
  <div class="page">
    <el-card class="panel" shadow="never">
      <div class="toolbar">
        <div class="toolbar-title">商品回收站</div>
        <div class="toolbar-actions">
          <el-button :disabled="!selectedIds.length" type="primary" @click="batchRestore">批量恢复</el-button>
          <el-button :disabled="!selectedIds.length" type="danger" @click="purgeBatch">彻底删除</el-button>
          <el-button @click="goList">返回商品列表</el-button>
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
        <el-date-picker
          v-model="deletedRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          value-format="x"
          class="filter-range"
          @change="onRangeChange"
        />
        <el-button type="primary" plain @click="doSearch">查询</el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="items"
        border
        class="pwd-table"
        @selection-change="onSel"
        @header-dragend="tw.onHeaderDragEnd"
      >
        <el-table-column column-key="selection" type="selection" v-bind="tw.col('selection', { width: 48 })" />
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
          show-overflow-tooltip
        />
        <el-table-column
          column-key="city"
          prop="city"
          label="所属城市"
          v-bind="tw.col('city', { width: 120 })"
          show-overflow-tooltip
        />
        <el-table-column
          column-key="district"
          prop="district"
          label="所属区域"
          v-bind="tw.col('district', { width: 140 })"
          show-overflow-tooltip
        />
        <el-table-column column-key="deletedAt" label="删除时间" v-bind="tw.col('deletedAt', { width: 168 })">
          <template #default="{ row }">
            {{ formatDateTime(row.deletedAt) }}
          </template>
        </el-table-column>
        <el-table-column column-key="actions" label="操作" v-bind="tw.col('actions', { width: 168 })" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="restoreOne(row)">恢复</el-button>
            <el-button link type="danger" @click="purgeOne(row)">彻底删除</el-button>
          </template>
        </el-table-column>
      </el-table>

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
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { http } from "@/api/http";
import { usePersistedTableWidths } from "@/composables/usePersistedTableWidths";
import type { ProductListItem } from "@/types/merchant";

const tw = usePersistedTableWidths("merchant-products-trash");
import { formatDateTime } from "@/utils/datetime";

const router = useRouter();
const loading = ref(false);
const items = ref<ProductListItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const keyword = ref("");
const district = ref("");
const deletedRange = ref<[number, number] | null>(null);
const selectedIds = ref<number[]>([]);

const PURGE_CONFIRM =
  "将永久删除所选商品及关联数据（含留言、标签关联等），此操作不可恢复。是否继续？";

function onSel(rows: ProductListItem[]) {
  selectedIds.value = rows.map((r) => r.id);
}

function doSearch() {
  page.value = 1;
  void load();
}

function onRangeChange() {
  doSearch();
}

function rangeParams(): { startTime?: string; endTime?: string } {
  if (!deletedRange.value || deletedRange.value.length !== 2) {
    return {};
  }
  const [a, b] = deletedRange.value;
  return {
    startTime: new Date(a).toISOString(),
    endTime: new Date(b).toISOString(),
  };
}

async function load() {
  loading.value = true;
  try {
    const { startTime, endTime } = rangeParams();
    const { data } = await http.get("/merchant/products/trash", {
      params: {
        page: page.value,
        pageSize: pageSize.value,
        keyword: keyword.value.trim() || undefined,
        district: district.value.trim() || undefined,
        startTime,
        endTime,
      },
    });
    items.value = data?.data?.items || [];
    total.value = data?.data?.total ?? 0;
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "加载失败");
  } finally {
    loading.value = false;
  }
}

function goList() {
  void router.push({ name: "merchant-products" });
}

async function restoreOne(row: ProductListItem) {
  try {
    await http.post(`/merchant/products/${row.id}/restore`);
    ElMessage.success("已恢复");
    await load();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "恢复失败");
  }
}

async function purgePermanent(ids: number[], title: string) {
  if (!ids.length) {
    ElMessage.warning("请先选择要删除的商品");
    return;
  }
  try {
    await ElMessageBox.confirm(PURGE_CONFIRM, title, {
      type: "warning",
      confirmButtonText: "确定彻底删除",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await http.post("/merchant/products/trash/permanent-delete", { ids });
    ElMessage.success("已彻底删除");
    await load();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "删除失败");
  }
}

async function purgeBatch() {
  await purgePermanent(selectedIds.value, "确认彻底删除");
}

async function purgeOne(row: ProductListItem) {
  await purgePermanent([row.id], "确认彻底删除");
}

async function batchRestore() {
  if (!selectedIds.value.length) return;
  await ElMessageBox.confirm(`确定恢复选中的 ${selectedIds.value.length} 个商品吗？`, "批量恢复", {
    type: "info",
  });
  try {
    await http.post("/merchant/products/batch-restore", { ids: selectedIds.value });
    ElMessage.success("已恢复");
    await load();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "操作失败");
  }
}

onMounted(() => load());
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

.filter-range {
  width: 100%;
  max-width: 380px;
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
</style>
