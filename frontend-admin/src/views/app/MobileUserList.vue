<template>
  <div class="page">
    <el-card class="panel" shadow="never">
      <div class="toolbar">
        <div class="toolbar-title">移动端用户</div>
        <div class="toolbar-actions">
          <el-button :disabled="!selectedIds.length" type="warning" @click="batchStatus('disabled')">一键禁用</el-button>
          <el-button :disabled="!selectedIds.length" type="success" @click="batchStatus('normal')">一键恢复</el-button>
        </div>
      </div>

      <div class="filter">
        <el-select
          v-model="statusFilter"
          clearable
          class="filter-select"
          placeholder="用户状态"
          @change="doSearch"
          @clear="doSearch"
        >
          <el-option label="正常" value="normal" />
          <el-option label="禁用" value="disabled" />
        </el-select>
        <el-input
          v-model="keyword"
          clearable
          class="filter-input"
          placeholder="IP / 归属地 / visitorKey"
          @clear="doSearch"
          @keyup.enter="doSearch"
        />
        <el-input
          v-model="userRegion"
          clearable
          class="filter-input filter-input--narrow"
          placeholder="所属区域"
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
        <el-table-column
          column-key="ip"
          prop="ip"
          label="用户 IP"
          v-bind="tw.col('ip', { minWidth: 132 })"
          class-name="col-text-wrap"
        />
        <el-table-column
          column-key="ipRegion"
          prop="ipRegion"
          label="IP 归属地"
          v-bind="tw.col('ipRegion', { minWidth: 160 })"
          class-name="col-text-wrap"
        />
        <el-table-column
          column-key="userRegion"
          prop="userRegion"
          label="所属区域"
          v-bind="tw.col('userRegion', { minWidth: 120 })"
          class-name="col-text-wrap"
        />
        <el-table-column column-key="status" label="状态" v-bind="tw.col('status', { minWidth: 100 })" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'normal' ? 'success' : 'danger'" effect="light">
              {{ row.status === "normal" ? "正常" : "禁用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column column-key="lastLoginAt" label="最新登录时间" v-bind="tw.col('lastLoginAt', { minWidth: 172 })">
          <template #default="{ row }">{{ formatDateTime(row.lastLoginAt) }}</template>
        </el-table-column>
        <el-table-column column-key="isOnline" label="在线状态" v-bind="tw.col('isOnline', { minWidth: 100 })" align="center">
          <template #default="{ row }">
            <el-tag :type="row.isOnline ? 'success' : 'info'" effect="plain">
              {{ row.isOnline ? "在线" : "离线" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column column-key="actions" label="操作" v-bind="tw.col('actions', { minWidth: 140 })" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row.id)">查看详情</el-button>
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

    <el-drawer v-model="drawer.visible" title="用户详情" size="520px" destroy-on-close>
      <div v-if="drawer.detail" v-loading="drawer.loading" class="detail-wrap">
        <el-descriptions :column="1" border size="small" class="detail-desc">
          <el-descriptions-item label="ID">{{ drawer.detail.id }}</el-descriptions-item>
          <el-descriptions-item label="visitorKey">{{ drawer.detail.visitorKey || "—" }}</el-descriptions-item>
          <el-descriptions-item label="用户 IP">{{ drawer.detail.ip || "—" }}</el-descriptions-item>
          <el-descriptions-item label="IP 归属地">{{ drawer.detail.ipRegion || "—" }}</el-descriptions-item>
          <el-descriptions-item label="用户状态">
            <el-tag :type="drawer.detail.status === 'normal' ? 'success' : 'danger'" size="small">
              {{ drawer.detail.status === "normal" ? "正常" : "禁用" }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="所属区域">{{ drawer.detail.userRegion || "—" }}</el-descriptions-item>
          <el-descriptions-item label="最近登录时间">{{ formatDateTime(drawer.detail.lastLoginAt) }}</el-descriptions-item>
          <el-descriptions-item label="最新访问次数">{{ drawer.detail.visitCount }}</el-descriptions-item>
          <el-descriptions-item label="最近访问商品 ID">{{ drawer.detail.lastProductId ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="最近提交留言 ID">{{ drawer.detail.lastMessageId ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="密码错误次数">{{ drawer.detail.pwdFailCount }}</el-descriptions-item>
          <el-descriptions-item label="在线状态">
            {{ drawer.detail.isOnline ? "在线" : "离线" }}
          </el-descriptions-item>
          <el-descriptions-item label="最近心跳 / 活跃">{{ formatDateTime(drawer.detail.lastSeenAt) }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDateTime(drawer.detail.createdAt) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDateTime(drawer.detail.updatedAt) }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail-section-title">留言记录</div>
        <el-table :data="drawer.detail.messages" border size="small" class="detail-msg-table">
          <el-table-column prop="id" label="留言 ID" width="88" />
          <el-table-column prop="productId" label="商品 ID" width="88" />
          <el-table-column prop="content" label="内容" min-width="160" show-overflow-tooltip />
          <el-table-column label="审核" width="96">
            <template #default="{ row }">
              {{ row.auditStatus === "approved" ? "已通过" : "待审批" }}
            </template>
          </el-table-column>
          <el-table-column prop="ipRegion" label="归属地" min-width="140" class-name="col-text-wrap" />
          <el-table-column label="提交时间" width="172">
            <template #default="{ row }">{{ formatDateTime(row.createdAt) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { onMounted, reactive, ref } from "vue";

import { http } from "@/api/http";
import { usePersistedTableWidths } from "@/composables/usePersistedTableWidths";
import type { MobileUserDetail, MobileUserRow } from "@/types/mobileUser";

const tw = usePersistedTableWidths("app-mobile-users");
import { formatDateTime } from "@/utils/datetime";

const loading = ref(false);
const items = ref<MobileUserRow[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const statusFilter = ref<"normal" | "disabled" | undefined>(undefined);
const keyword = ref("");
const userRegion = ref("");
const selectedIds = ref<number[]>([]);

const drawer = reactive({
  visible: false,
  loading: false,
  detail: null as MobileUserDetail | null,
});

function onSel(rows: MobileUserRow[]) {
  selectedIds.value = rows.map((r) => r.id);
}

function doSearch() {
  page.value = 1;
  void load();
}

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get("/app/mobile-users", {
      params: {
        page: page.value,
        pageSize: pageSize.value,
        status: statusFilter.value || undefined,
        keyword: keyword.value.trim() || undefined,
        userRegion: userRegion.value.trim() || undefined,
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

async function openDetail(id: number) {
  drawer.visible = true;
  drawer.loading = true;
  drawer.detail = null;
  try {
    const { data } = await http.get(`/app/mobile-users/${id}`);
    drawer.detail = data?.data || null;
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "加载失败");
    drawer.visible = false;
  } finally {
    drawer.loading = false;
  }
}

async function batchStatus(status: "normal" | "disabled") {
  if (!selectedIds.value.length) return;
  const label = status === "normal" ? "恢复" : "禁用";
  try {
    await ElMessageBox.confirm(`确定将选中的 ${selectedIds.value.length} 个用户${label}吗？`, "提示", {
      type: "warning",
    });
  } catch {
    return;
  }
  try {
    await http.post("/app/mobile-users/batch-status", { ids: selectedIds.value, status });
    ElMessage.success(`已${label}`);
    await load();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "操作失败");
  }
}

async function confirmDelete(row: MobileUserRow) {
  await ElMessageBox.confirm(`确定删除该移动端用户吗？关联留言将一并删除。`, "提示", { type: "warning" });
  try {
    await http.delete(`/app/mobile-users/${row.id}`);
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
  max-width: 260px;
}

.filter-input--narrow {
  max-width: 200px;
}

.filter-select {
  width: 140px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.detail-wrap {
  padding-right: 8px;
}

.detail-desc {
  margin-bottom: 16px;
}

.detail-section-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 10px;
}

.detail-msg-table {
  width: 100%;
}

.table-scroll {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.data-table {
  min-width: 960px;
}

.data-table :deep(.col-text-wrap .cell) {
  white-space: normal;
  word-break: break-word;
  line-height: 1.45;
}

.detail-msg-table :deep(.col-text-wrap .cell) {
  white-space: normal;
  word-break: break-word;
  line-height: 1.45;
}
</style>
