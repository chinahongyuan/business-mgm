<template>
  <div class="page">
    <el-card class="panel" shadow="never">
      <div class="toolbar">
        <div class="toolbar-title">留言板</div>
        <div class="toolbar-actions">
          <el-button :disabled="!selectedIds.length" type="primary" @click="batchToggleAudit">一键审核</el-button>
          <el-button type="primary" @click="openCreate">新增留言</el-button>
        </div>
      </div>

      <div class="filter">
        <el-select
          v-model="auditFilter"
          clearable
          class="filter-select"
          placeholder="审核状态"
          @change="doSearch"
          @clear="doSearch"
        >
          <el-option label="待审批" value="pending" />
          <el-option label="已通过" value="approved" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="提交开始"
          end-placeholder="提交结束"
          value-format="x"
          class="filter-range"
          @change="onRangeChange"
        />
        <el-input
          v-model="productName"
          clearable
          class="filter-input"
          placeholder="商品名称"
          @clear="doSearch"
          @keyup.enter="doSearch"
        />
        <el-input
          v-model="mobileUserIp"
          clearable
          class="filter-input filter-input--narrow"
          placeholder="移动端用户 IP"
          @clear="doSearch"
          @keyup.enter="doSearch"
        />
        <el-button type="primary" plain @click="doSearch">查询</el-button>
      </div>

      <div class="table-scroll">
        <el-table
          v-loading="loading"
          :data="items"
          border
          class="data-table"
          table-layout="auto"
          @selection-change="onSel"
          @header-dragend="tw.onHeaderDragEnd"
        >
        <el-table-column column-key="selection" type="selection" v-bind="tw.col('selection', { width: 48 })" fixed />
        <el-table-column column-key="cover" label="商品封面" v-bind="tw.col('cover', { width: 88 })">
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
          column-key="productName"
          prop="productName"
          label="商品名称"
          v-bind="tw.col('productName', { minWidth: 140 })"
          show-overflow-tooltip
        />
        <el-table-column
          column-key="mobileUserIp"
          prop="mobileUserIp"
          label="移动端用户 IP"
          v-bind="tw.col('mobileUserIp', { minWidth: 160 })"
          class-name="col-text-wrap"
        />
        <el-table-column
          column-key="contentPreview"
          prop="contentPreview"
          label="内容摘要"
          v-bind="tw.col('contentPreview', { minWidth: 160 })"
          show-overflow-tooltip
        />
        <el-table-column column-key="createdAt" label="提交时间" v-bind="tw.col('createdAt', { width: 180 })">
          <template #default="{ row }">{{ formatDateTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column column-key="auditStatus" label="审核状态" v-bind="tw.col('auditStatus', { width: 110 })" align="center">
          <template #default="{ row }">
            <el-tag :type="row.auditStatus === 'approved' ? 'success' : 'warning'" effect="light">
              {{ row.auditStatus === "approved" ? "已通过" : "待审批" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column column-key="actions" label="操作" v-bind="tw.col('actions', { minWidth: 140 })" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="confirmDelete(row)">删除</el-button>
          </template>
        </el-table-column>
        </el-table>
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

    <el-dialog v-model="form.visible" :title="form.mode === 'create' ? '新增留言' : '编辑留言'" width="560px" destroy-on-close>
      <el-form label-width="96px">
        <el-form-item v-if="form.mode === 'create'" label="商品">
          <el-select
            v-model="form.productId"
            filterable
            remote
            reserve-keyword
            placeholder="搜索商品名称"
            :remote-method="searchProducts"
            :loading="form.productLoading"
            style="width: 100%"
          >
            <el-option v-for="p in form.productOptions" :key="p.id" :label="p.name" :value="p.id">
              <span>{{ p.name }}</span>
            </el-option>
          </el-select>
          <div class="form-hint">管理员新增的留言在列表「移动端用户 IP」列显示为「管理后台」，并默认已通过。</div>
        </el-form-item>
        <el-form-item label="留言内容">
          <el-input v-model="form.content" type="textarea" :rows="6" maxlength="2000" show-word-limit />
        </el-form-item>
        <el-form-item v-if="form.mode === 'edit'" label="审核状态">
          <el-radio-group v-model="form.auditStatus">
            <el-radio value="pending">待审批</el-radio>
            <el-radio value="approved">已通过</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="form.visible = false">取消</el-button>
        <el-button type="primary" :loading="form.saving" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { onMounted, reactive, ref } from "vue";

import { http } from "@/api/http";
import { usePersistedTableWidths } from "@/composables/usePersistedTableWidths";
import type { MessageBoardRow, ProductOption } from "@/types/messageBoard";

const tw = usePersistedTableWidths("message-board");
import { formatDateTime } from "@/utils/datetime";

const loading = ref(false);
const items = ref<MessageBoardRow[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const auditFilter = ref<"pending" | "approved" | undefined>(undefined);
const dateRange = ref<[number, number] | null>(null);
const productName = ref("");
const mobileUserIp = ref("");
const selectedIds = ref<number[]>([]);

const form = reactive({
  visible: false,
  mode: "create" as "create" | "edit",
  id: 0,
  productId: undefined as number | undefined,
  content: "",
  auditStatus: "pending" as "pending" | "approved",
  saving: false,
  productLoading: false,
  productOptions: [] as ProductOption[],
});

function onRangeChange() {
  doSearch();
}

function onSel(rows: MessageBoardRow[]) {
  selectedIds.value = rows.map((r) => r.id);
}

function doSearch() {
  page.value = 1;
  void load();
}

function rangeParams() {
  if (!dateRange.value || dateRange.value.length !== 2) {
    return { startTime: undefined as string | undefined, endTime: undefined as string | undefined };
  }
  const [a, b] = dateRange.value;
  const s = new Date(a);
  const e = new Date(b);
  return {
    startTime: formatLocalIso(s),
    endTime: formatLocalIso(e),
  };
}

function formatLocalIso(d: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

async function load() {
  loading.value = true;
  try {
    const { startTime, endTime } = rangeParams();
    const { data } = await http.get("/message-boards", {
      params: {
        page: page.value,
        pageSize: pageSize.value,
        auditStatus: auditFilter.value || undefined,
        startTime,
        endTime,
        productName: productName.value.trim() || undefined,
        mobileUserIp: mobileUserIp.value.trim() || undefined,
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

async function searchProducts(q: string) {
  form.productLoading = true;
  try {
    const { data } = await http.get("/message-boards/products/options", {
      params: { keyword: q?.trim() || undefined, pageSize: 50 },
    });
    form.productOptions = data?.data?.items || [];
  } catch {
    form.productOptions = [];
  } finally {
    form.productLoading = false;
  }
}

function openCreate() {
  form.mode = "create";
  form.id = 0;
  form.productId = undefined;
  form.content = "";
  form.productOptions = [];
  form.visible = true;
  void searchProducts("");
}

async function openEdit(row: MessageBoardRow) {
  form.mode = "edit";
  form.id = row.id;
  try {
    const { data } = await http.get(`/message-boards/${row.id}`);
    const d = data?.data;
    form.productId = d?.productId;
    form.content = d?.content || "";
    form.auditStatus = d?.auditStatus || "pending";
    form.visible = true;
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "加载失败");
  }
}

async function submitForm() {
  const c = form.content.trim();
  if (!c) {
    ElMessage.warning("请输入留言内容");
    return;
  }
  if (form.mode === "create" && !form.productId) {
    ElMessage.warning("请选择商品");
    return;
  }
  form.saving = true;
  try {
    if (form.mode === "create") {
      await http.post("/message-boards", { productId: form.productId, content: c });
      ElMessage.success("已新增");
    } else {
      await http.put(`/message-boards/${form.id}`, {
        content: c,
        auditStatus: form.auditStatus,
      });
      ElMessage.success("已保存");
    }
    form.visible = false;
    await load();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "保存失败");
  } finally {
    form.saving = false;
  }
}

async function batchToggleAudit() {
  if (!selectedIds.value.length) return;
  await ElMessageBox.confirm(
    `将操作选中的 ${selectedIds.value.length} 条留言的审核状态，确定吗？`,
    "一键审核",
    { type: "warning" },
  );
  try {
    await http.post("/message-boards/batch-toggle-audit", { ids: selectedIds.value });
    ElMessage.success("已更新审核状态");
    await load();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "操作失败");
  }
}

async function confirmDelete(row: MessageBoardRow) {
  await ElMessageBox.confirm(`确定删除该留言吗？`, "提示", { type: "warning" });
  try {
    await http.delete(`/message-boards/${row.id}`);
    ElMessage.success("已删除");
    await load();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "删除失败");
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
  max-width: 220px;
}

.filter-input--narrow {
  max-width: 180px;
}

.filter-select {
  width: 140px;
}

.filter-range {
  max-width: 360px;
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

.form-hint {
  margin-top: 8px;
  font-size: 12px;
  color: rgba(15, 23, 42, 0.55);
  line-height: 1.5;
}

.table-scroll {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.data-table {
  min-width: 920px;
}

.data-table :deep(.col-text-wrap .cell) {
  white-space: normal;
  word-break: break-word;
  line-height: 1.45;
}
</style>
