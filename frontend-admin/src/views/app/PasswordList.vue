<template>
  <div class="page">
    <el-card class="panel" shadow="never">
      <div class="toolbar">
        <div class="toolbar-title">登录口令</div>
        <div class="toolbar-actions">
          <el-button type="primary" @click="openAdd">新增口令</el-button>
          <el-button type="success" plain @click="batchGenerate">一键创建</el-button>
          <el-button :disabled="!selectedIds.length" type="warning" @click="batchStatus('disabled')">一键禁用</el-button>
          <el-button :disabled="!selectedIds.length" type="success" @click="batchStatus('normal')">一键恢复</el-button>
        </div>
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
        <el-table-column column-key="id" prop="id" label="密码 ID" v-bind="tw.col('id', { width: 96 })" />
        <el-table-column
          column-key="passwordPlain"
          prop="passwordPlain"
          label="密码内容"
          v-bind="tw.col('passwordPlain', { minWidth: 180 })"
          show-overflow-tooltip
        />
        <el-table-column column-key="status" label="密码状态" v-bind="tw.col('status', { width: 200 })" align="center">
          <template #default="{ row }">
            <el-radio-group
              :model-value="row.status"
              size="small"
              class="pwd-status-rg"
              :disabled="statusBusyId === row.id"
              @change="(v: string) => onStatusChange(row, v as 'normal' | 'disabled')"
            >
              <el-radio-button label="normal">正常</el-radio-button>
              <el-radio-button label="disabled">禁用</el-radio-button>
            </el-radio-group>
          </template>
        </el-table-column>
        <el-table-column column-key="createdAt" label="创建时间" v-bind="tw.col('createdAt', { width: 176 })">
          <template #default="{ row }">{{ formatDateTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column column-key="actions" label="操作" v-bind="tw.col('actions', { width: 140 })" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">修改</el-button>
            <el-button link type="danger" @click="confirmDelete(row)">删除</el-button>
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

    <el-dialog v-model="addDlg.visible" title="新增口令" width="440px" destroy-on-close @closed="resetAdd">
      <el-form label-width="88px">
        <el-form-item label="密码内容" required>
          <el-input
            v-model="addDlg.passwordPlain"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="支持英文、中文、数字、大小写等"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDlg.visible = false">取消</el-button>
        <el-button type="primary" :loading="addDlg.saving" @click="submitAdd">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editDlg.visible" title="修改口令" width="480px" destroy-on-close>
      <el-form label-width="88px">
        <el-form-item label="密码内容" required>
          <el-input
            v-model="editDlg.passwordPlain"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="editDlg.status">
            <el-radio value="normal">正常</el-radio>
            <el-radio value="disabled">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDlg.visible = false">取消</el-button>
        <el-button type="primary" :loading="editDlg.saving" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { onMounted, reactive, ref } from "vue";

import { http } from "@/api/http";
import { usePersistedTableWidths } from "@/composables/usePersistedTableWidths";
import { formatDateTime } from "@/utils/datetime";

const tw = usePersistedTableWidths("app-passwords");

type PasswordRow = {
  id: number;
  passwordPlain: string;
  status: "normal" | "disabled";
  createdAt: string | null;
  expiresAt: string | null;
};

const loading = ref(false);
const items = ref<PasswordRow[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const selectedIds = ref<number[]>([]);
const statusBusyId = ref<number | null>(null);

const addDlg = reactive({
  visible: false,
  saving: false,
  passwordPlain: "",
});

const editDlg = reactive({
  visible: false,
  saving: false,
  id: 0,
  passwordPlain: "",
  status: "normal" as "normal" | "disabled",
});

function onSel(rows: PasswordRow[]) {
  selectedIds.value = rows.map((r) => r.id);
}

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get("/app/mobile-login-passwords", {
      params: { page: page.value, pageSize: pageSize.value },
    });
    items.value = data?.data?.items || [];
    total.value = data?.data?.total ?? 0;
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "加载失败");
  } finally {
    loading.value = false;
  }
}

function openAdd() {
  addDlg.passwordPlain = "";
  addDlg.visible = true;
}

function resetAdd() {
  addDlg.passwordPlain = "";
}

async function submitAdd() {
  const plain = addDlg.passwordPlain.trim();
  if (!plain) {
    ElMessage.warning("请输入密码内容");
    return;
  }
  addDlg.saving = true;
  try {
    await http.post("/app/mobile-login-passwords", { passwordPlain: plain });
    ElMessage.success("已新增");
    addDlg.visible = false;
    await load();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "保存失败");
  } finally {
    addDlg.saving = false;
  }
}

async function batchGenerate() {
  await ElMessageBox.confirm("将自动创建 5 条 6 位随机数字口令，永不过期。是否继续？", "一键创建", {
    type: "info",
    confirmButtonText: "创建",
    cancelButtonText: "取消",
  });
  try {
    const { data } = await http.post<{ data: { items: PasswordRow[] } }>("/app/mobile-login-passwords/batch-generate");
    const n = data?.data?.items?.length ?? 0;
    ElMessage.success(`已创建 ${n} 条口令`);
    await load();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "创建失败");
  }
}

async function batchStatus(status: "normal" | "disabled") {
  if (!selectedIds.value.length) return;
  const label = status === "normal" ? "恢复" : "禁用";
  await ElMessageBox.confirm(`确定将选中的 ${selectedIds.value.length} 条口令批量${label}吗？`, "提示", {
    type: "warning",
  });
  try {
    await http.post("/app/mobile-login-passwords/batch-status", { ids: selectedIds.value, status });
    ElMessage.success(`已${label}`);
    await load();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "操作失败");
  }
}

async function onStatusChange(row: PasswordRow, status: "normal" | "disabled") {
  if (row.status === status) return;
  statusBusyId.value = row.id;
  try {
    await http.put(`/app/mobile-login-passwords/${row.id}`, { status });
    row.status = status;
    ElMessage.success("状态已更新");
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "更新失败");
    await load();
  } finally {
    statusBusyId.value = null;
  }
}

function openEdit(row: PasswordRow) {
  editDlg.id = row.id;
  editDlg.passwordPlain = row.passwordPlain;
  editDlg.status = row.status;
  editDlg.visible = true;
}

async function submitEdit() {
  const plain = editDlg.passwordPlain.trim();
  if (!plain) {
    ElMessage.warning("请输入密码内容");
    return;
  }
  editDlg.saving = true;
  try {
    await http.put(`/app/mobile-login-passwords/${editDlg.id}`, {
      passwordPlain: plain,
      status: editDlg.status,
      expiresAt: null,
    });
    ElMessage.success("已保存");
    editDlg.visible = false;
    await load();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "保存失败");
  } finally {
    editDlg.saving = false;
  }
}

async function confirmDelete(row: PasswordRow) {
  await ElMessageBox.confirm("确定删除该条口令吗？", "提示", { type: "warning" });
  try {
    await http.delete(`/app/mobile-login-passwords/${row.id}`);
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

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.pwd-table :deep(.el-radio-button__inner) {
  padding: 5px 12px;
}

.pwd-status-rg {
  flex-wrap: nowrap;
  justify-content: center;
}
</style>
