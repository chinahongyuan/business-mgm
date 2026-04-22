<template>
  <div class="page">
    <el-card class="panel" shadow="never">
      <div class="toolbar">
        <div class="toolbar-title">登录日志</div>
      </div>

      <el-table v-loading="loading" :data="items" border @header-dragend="tw.onHeaderDragEnd">
        <el-table-column column-key="id" prop="id" label="ID" v-bind="tw.col('id', { width: 90 })" />
        <el-table-column
          column-key="username"
          prop="username"
          label="用户名"
          v-bind="tw.col('username', { minWidth: 140 })"
        />
        <el-table-column column-key="success" label="结果" v-bind="tw.col('success', { width: 110 })">
          <template #default="{ row }">
            <el-tag :type="row.success ? 'success' : 'danger'">
              {{ row.success ? "成功" : "失败" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column column-key="ip" prop="ip" label="IP" v-bind="tw.col('ip', { minWidth: 140 })" />
        <el-table-column
          column-key="message"
          prop="message"
          label="说明"
          v-bind="tw.col('message', { minWidth: 160 })"
          show-overflow-tooltip
        />
        <el-table-column column-key="createdAt" label="时间" v-bind="tw.col('createdAt', { minWidth: 180 })">
          <template #default="{ row }">{{ formatDateTime(row.createdAt) }}</template>
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
import { ElMessage } from "element-plus";
import { onMounted, ref } from "vue";

import { http } from "@/api/http";
import { usePersistedTableWidths } from "@/composables/usePersistedTableWidths";
import { formatDateTime } from "@/utils/datetime";

const tw = usePersistedTableWidths("system-login-logs");

type Row = {
  id: number;
  username: string;
  success: boolean;
  ip?: string | null;
  message?: string | null;
  createdAt?: string | null;
};

const loading = ref(false);
const items = ref<Row[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get("/system/login-logs", {
      params: { page: page.value, pageSize: pageSize.value },
    });
    const payload = data?.data;
    items.value = payload?.items || [];
    total.value = payload?.total || 0;
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "加载失败");
  } finally {
    loading.value = false;
  }
}

onMounted(load);
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
  gap: 12px;
  margin-bottom: 16px;
}

.toolbar-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
