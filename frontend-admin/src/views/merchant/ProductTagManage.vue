<template>
  <div class="page">
    <el-card class="panel" shadow="never">
      <div class="toolbar">
        <div class="toolbar-title">商品标签</div>
        <el-button type="primary" @click="openCreate">新增标签</el-button>
      </div>

      <el-table v-loading="loading" :data="items" border @header-dragend="tw.onHeaderDragEnd">
        <el-table-column column-key="id" prop="id" label="ID" v-bind="tw.col('id', { width: 90 })" />
        <el-table-column column-key="name" prop="name" label="名称" v-bind="tw.col('name', { minWidth: 200 })" />
        <el-table-column column-key="createdAt" label="创建时间" v-bind="tw.col('createdAt', { minWidth: 168 })">
          <template #default="{ row }">{{ formatDateTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column column-key="updatedAt" label="更新时间" v-bind="tw.col('updatedAt', { minWidth: 168 })">
          <template #default="{ row }">{{ formatDateTime(row.updatedAt) }}</template>
        </el-table-column>
        <el-table-column column-key="actions" label="操作" v-bind="tw.col('actions', { width: 180 })" fixed="right">
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

    <el-dialog v-model="dialog.visible" :title="dialog.title" width="480px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="dialog.form.name" maxlength="120" show-word-limit />
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
import { onMounted, reactive, ref } from "vue";

import { http } from "@/api/http";
import { usePersistedTableWidths } from "@/composables/usePersistedTableWidths";
import type { ProductTag } from "@/types/merchant";

const tw = usePersistedTableWidths("merchant-tags");
import { formatDateTime } from "@/utils/datetime";

const loading = ref(false);
const items = ref<ProductTag[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);

const dialog = reactive({
  visible: false,
  title: "新增标签",
  saving: false,
  editingId: null as number | null,
  form: { name: "" },
});

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get("/merchant/tags", {
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

function openCreate() {
  dialog.title = "新增标签";
  dialog.editingId = null;
  dialog.form = { name: "" };
  dialog.visible = true;
}

function openEdit(row: ProductTag) {
  dialog.title = "编辑标签";
  dialog.editingId = row.id;
  dialog.form = { name: row.name };
  dialog.visible = true;
}

async function save() {
  const name = dialog.form.name.trim();
  if (!name) {
    ElMessage.warning("请输入名称");
    return;
  }
  dialog.saving = true;
  try {
    if (dialog.editingId) {
      await http.put(`/merchant/tags/${dialog.editingId}`, { name });
    } else {
      await http.post("/merchant/tags", { name });
    }
    ElMessage.success("已保存");
    dialog.visible = false;
    await load();
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "保存失败");
  } finally {
    dialog.saving = false;
  }
}

async function confirmDelete(row: ProductTag) {
  await ElMessageBox.confirm(`确定删除标签「${row.name}」吗？`, "提示", { type: "warning" });
  try {
    await http.delete(`/merchant/tags/${row.id}`);
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
