<template>
  <div class="page">
    <el-card class="panel" shadow="never">
      <div class="toolbar">
        <div class="toolbar-title">菜单列表</div>
        <el-button type="primary" @click="openCreate(null)">新增根菜单</el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="tree"
        row-key="id"
        border
        default-expand-all
        :tree-props="{ children: 'children' }"
        @header-dragend="tw.onHeaderDragEnd"
      >
        <el-table-column column-key="title" prop="title" label="名称" v-bind="tw.col('title', { minWidth: 200 })" />
        <el-table-column column-key="path" prop="path" label="路由路径" v-bind="tw.col('path', { minWidth: 220 })">
          <template #default="{ row }">
            <span>{{ row.path || "—" }}</span>
          </template>
        </el-table-column>
        <el-table-column column-key="icon" prop="icon" label="图标" v-bind="tw.col('icon', { width: 120 })" />
        <el-table-column column-key="sortOrder" prop="sortOrder" label="排序" v-bind="tw.col('sortOrder', { width: 90 })" />
        <el-table-column column-key="isActive" label="状态" v-bind="tw.col('isActive', { width: 110 })">
          <template #default="{ row }">
            <el-tag :type="row.isActive ? 'success' : 'info'">
              {{ row.isActive ? "启用" : "停用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column column-key="actions" label="操作" v-bind="tw.col('actions', { width: 260 })" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openCreate(row.id)">新增子项</el-button>
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="confirmDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialog.visible" :title="dialog.title" width="560px" destroy-on-close>
      <el-form label-width="96px">
        <el-form-item label="名称">
          <el-input v-model="dialog.form.title" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="路由路径">
          <el-input v-model="dialog.form.path" placeholder="分组菜单可留空" maxlength="255" />
        </el-form-item>
        <el-form-item label="图标">
          <el-select v-model="dialog.form.icon" filterable placeholder="选择图标" clearable>
            <el-option v-for="opt in iconOptions" :key="opt" :label="opt" :value="opt" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="dialog.form.sortOrder" :min="0" :max="999999" />
        </el-form-item>
        <el-form-item label="父级">
          <el-select v-model="dialog.form.parentId" clearable placeholder="无（根菜单）">
            <el-option
              v-for="opt in parentOptions"
              :key="opt.id"
              :label="opt.label"
              :value="opt.id"
              :disabled="opt.disabled"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="dialog.form.isActive" active-text="启用" inactive-text="停用" />
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
import { computed, onMounted, reactive, ref } from "vue";

import { http } from "@/api/http";
import { usePersistedTableWidths } from "@/composables/usePersistedTableWidths";
import type { MenuNode } from "@/types/menu";

const tw = usePersistedTableWidths("system-menus");

const loading = ref(false);
const tree = ref<MenuNode[]>([]);

const iconOptions = [
  "Odometer",
  "Setting",
  "Menu",
  "Document",
  "Notebook",
  "User",
  "Bell",
  "Goods",
];

const dialog = reactive({
  visible: false,
  title: "新增菜单",
  saving: false,
  editingId: null as number | null,
  form: {
    title: "",
    path: "",
    icon: "",
    sortOrder: 0,
    parentId: null as number | null,
    isActive: true,
  },
});

function flattenForParent(
  nodes: MenuNode[],
  depth = 0,
  excludeSubtree?: Set<number>,
): { id: number; label: string; disabled: boolean }[] {
  const out: { id: number; label: string; disabled: boolean }[] = [];
  for (const n of nodes) {
    const disabled = Boolean(excludeSubtree?.has(n.id));
    out.push({ id: n.id, label: `${" ".repeat(depth * 2)}${n.title}`, disabled });
    if (n.children?.length) {
      out.push(...flattenForParent(n.children, depth + 1, excludeSubtree));
    }
  }
  return out;
}

function collectDescendantIds(node: MenuNode): Set<number> {
  const s = new Set<number>();
  const walk = (n: MenuNode) => {
    s.add(n.id);
    for (const c of n.children || []) walk(c);
  };
  walk(node);
  return s;
}

function findNodeById(nodes: MenuNode[], id: number): MenuNode | null {
  for (const n of nodes) {
    if (n.id === id) return n;
    if (n.children?.length) {
      const r = findNodeById(n.children, id);
      if (r) return r;
    }
  }
  return null;
}

const parentOptions = computed(() => {
  const exclude = new Set<number>();
  if (dialog.editingId) {
    const node = findNodeById(tree.value, dialog.editingId);
    if (node) {
      for (const id of collectDescendantIds(node)) exclude.add(id);
    } else {
      exclude.add(dialog.editingId);
    }
  }
  return flattenForParent(tree.value, 0, exclude);
});

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get("/system/menus");
    tree.value = data?.data || [];
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "加载失败");
  } finally {
    loading.value = false;
  }
}

function openCreate(parentId: number | null) {
  dialog.title = parentId ? "新增子菜单" : "新增根菜单";
  dialog.editingId = null;
  dialog.form = {
    title: "",
    path: "",
    icon: "",
    sortOrder: 0,
    parentId,
    isActive: true,
  };
  dialog.visible = true;
}

function openEdit(row: MenuNode) {
  dialog.title = "编辑菜单";
  dialog.editingId = row.id;
  dialog.form = {
    title: row.title,
    path: row.path || "",
    icon: row.icon || "",
    sortOrder: row.sortOrder,
    parentId: row.parentId,
    isActive: row.isActive,
  };
  dialog.visible = true;
}

async function save() {
  if (!dialog.form.title.trim()) {
    ElMessage.warning("请输入名称");
    return;
  }
  dialog.saving = true;
  try {
    const payload = {
      title: dialog.form.title.trim(),
      path: dialog.form.path.trim() ? dialog.form.path.trim() : null,
      icon: dialog.form.icon || null,
      sortOrder: dialog.form.sortOrder,
      parentId: dialog.form.parentId ?? null,
      isActive: dialog.form.isActive,
    };
    if (dialog.editingId) {
      await http.put(`/system/menus/${dialog.editingId}`, payload);
      ElMessage.success("已保存");
    } else {
      await http.post("/system/menus", payload);
      ElMessage.success("已创建");
    }
    dialog.visible = false;
    await load();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "保存失败");
  } finally {
    dialog.saving = false;
  }
}

async function confirmDelete(row: MenuNode) {
  await ElMessageBox.confirm(`确定删除「${row.title}」吗？`, "提示", { type: "warning" });
  try {
    await http.delete(`/system/menus/${row.id}`);
    ElMessage.success("已删除");
    await load();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "删除失败");
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
</style>
