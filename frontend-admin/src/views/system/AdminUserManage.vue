<template>
  <div class="page">
    <el-card class="panel" shadow="never">
      <div class="toolbar">
        <div class="toolbar-title">后台账号</div>
        <el-button type="primary" @click="openCreate">新增账号</el-button>
      </div>

      <el-table v-loading="loading" :data="items" border @header-dragend="tw.onHeaderDragEnd">
        <el-table-column column-key="id" prop="id" label="ID" v-bind="tw.col('id', { width: 90 })" />
        <el-table-column
          column-key="username"
          prop="username"
          label="用户名"
          v-bind="tw.col('username', { minWidth: 160 })"
        />
        <el-table-column column-key="isActive" label="状态" v-bind="tw.col('isActive', { width: 120 })">
          <template #default="{ row }">
            <el-tag :type="row.isActive ? 'success' : 'info'">
              {{ row.isActive ? "启用" : "停用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column column-key="createdAt" label="创建时间" v-bind="tw.col('createdAt', { minWidth: 180 })">
          <template #default="{ row }">{{ formatDateTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column column-key="actions" label="操作" v-bind="tw.col('actions', { width: 200 })" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
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

    <el-dialog v-model="dialog.visible" :title="dialog.title" width="640px" destroy-on-close>
      <el-form label-width="96px">
        <el-form-item label="用户名">
          <el-input v-model="dialog.form.username" maxlength="64" show-word-limit :disabled="dialog.editing" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="dialog.form.password"
            type="password"
            show-password
            :placeholder="dialog.editing ? '不修改请留空' : '至少 6 位'"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="dialog.form.isActive" active-text="启用" inactive-text="停用" />
        </el-form-item>
        <el-form-item label="菜单权限">
          <el-tree
            ref="treeRef"
            class="perm-tree"
            :data="menuTree"
            show-checkbox
            node-key="id"
            default-expand-all
            :props="{ label: 'title', children: 'children' }"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { nextTick, onMounted, reactive, ref } from "vue";

import { http } from "@/api/http";
import { usePersistedTableWidths } from "@/composables/usePersistedTableWidths";
import type { MenuNode } from "@/types/menu";

const tw = usePersistedTableWidths("system-admin-users");
import { formatDateTime } from "@/utils/datetime";

type AdminRow = {
  id: number;
  username: string;
  isActive: boolean;
  menuIds: number[];
  createdAt?: string | null;
};

const loading = ref(false);
const items = ref<AdminRow[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);

const menuTree = ref<MenuNode[]>([]);
const treeRef = ref<{ getCheckedKeys: (leafOnly?: boolean) => unknown[]; getHalfCheckedKeys: () => unknown[]; setCheckedKeys: (keys: unknown[]) => void } | null>(null);

const dialog = reactive({
  visible: false,
  title: "新增账号",
  saving: false,
  editing: false,
  editingId: 0,
  form: {
    username: "",
    password: "",
    isActive: true,
  },
});

async function loadMenus() {
  const { data } = await http.get("/system/menus");
  menuTree.value = data?.data || [];
}

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get("/system/users", {
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

function collectCheckedMenuIds(): number[] {
  const tree = treeRef.value;
  if (!tree) return [];
  const a = tree.getCheckedKeys(false) as number[];
  const b = tree.getHalfCheckedKeys() as number[];
  return Array.from(new Set([...a, ...b]));
}

function openCreate() {
  dialog.title = "新增账号";
  dialog.editing = false;
  dialog.editingId = 0;
  dialog.form = { username: "", password: "", isActive: true };
  dialog.visible = true;
  nextTick(() => {
    treeRef.value?.setCheckedKeys([]);
  });
}

function openEdit(row: AdminRow) {
  dialog.title = "编辑账号";
  dialog.editing = true;
  dialog.editingId = row.id;
  dialog.form = {
    username: row.username,
    password: "",
    isActive: row.isActive,
  };
  dialog.visible = true;
  nextTick(() => {
    treeRef.value?.setCheckedKeys(row.menuIds || []);
  });
}

async function save() {
  if (!dialog.form.username.trim()) {
    ElMessage.warning("请输入用户名");
    return;
  }
  if (!dialog.editing && dialog.form.password.length < 6) {
    ElMessage.warning("密码至少 6 位");
    return;
  }
  dialog.saving = true;
  try {
    const menuIds = collectCheckedMenuIds();
    if (!dialog.editing) {
      await http.post("/system/users", {
        username: dialog.form.username.trim(),
        password: dialog.form.password,
        isActive: dialog.form.isActive,
        menuIds,
      });
      ElMessage.success("已创建");
    } else {
      const payload: Record<string, unknown> = {
        username: dialog.form.username.trim(),
        isActive: dialog.form.isActive,
        menuIds,
      };
      if (dialog.form.password) payload.password = dialog.form.password;
      await http.put(`/system/users/${dialog.editingId}`, payload);
      ElMessage.success("已保存");
    }
    dialog.visible = false;
    await load();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "保存失败");
  } finally {
    dialog.saving = false;
  }
}

async function confirmDelete(row: AdminRow) {
  await ElMessageBox.confirm(`确定删除账号「${row.username}」吗？`, "提示", { type: "warning" });
  try {
    await http.delete(`/system/users/${row.id}`);
    ElMessage.success("已删除");
    await load();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "删除失败");
  }
}

onMounted(async () => {
  await loadMenus();
  await load();
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

.perm-tree {
  width: 100%;
  max-height: 360px;
  overflow: auto;
  padding: 10px 10px 8px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.02);
}
</style>
