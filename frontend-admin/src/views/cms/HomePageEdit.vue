<template>
  <div class="page">
    <el-card v-loading="loading" class="panel" shadow="never">
      <template #header>
        <div class="card-head">
          <span class="toolbar-title">首页管理</span>
          <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
        </div>
      </template>

      <el-form label-width="120px" class="form cms-form">
        <section class="form-section">
          <h3 class="form-section-title">首页状态</h3>
          <el-form-item label="发布状态">
            <el-radio-group v-model="form.status">
              <el-radio value="published">发布</el-radio>
              <el-radio value="draft">未发布</el-radio>
            </el-radio-group>
          </el-form-item>
        </section>

        <section class="form-section">
          <h3 class="form-section-title">移动端</h3>
          <el-form-item label="显示标题">
            <el-input
              v-model="form.mobileTitle"
              maxlength="255"
              show-word-limit
              placeholder="移动端展示用标题（可选）"
              clearable
            />
          </el-form-item>
        </section>

        <section class="form-section form-section--last">
          <h3 class="form-section-title">首页内容</h3>
          <el-form-item :label-width="0" class="form-item-editor">
            <RichTextEditor v-model="form.contentHtml" class="editor-block" />
          </el-form-item>
        </section>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";

import RichTextEditor from "@/components/RichTextEditor.vue";
import { http } from "@/api/http";

type HomePageDto = {
  id: number;
  contentHtml: string;
  mobileTitle?: string;
  status: "published" | "draft";
};

const loading = ref(false);
const saving = ref(false);

const form = reactive({
  contentHtml: "",
  mobileTitle: "",
  status: "draft" as "published" | "draft",
});

function applyDto(d: HomePageDto) {
  form.contentHtml = d.contentHtml || "";
  form.mobileTitle = d.mobileTitle ?? "";
  form.status = d.status === "published" ? "published" : "draft";
}

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get<{ data: HomePageDto }>("/cms/home-page");
    if (data?.data) applyDto(data.data);
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "加载失败");
  } finally {
    loading.value = false;
  }
}

async function submit() {
  saving.value = true;
  try {
    const { data } = await http.put<{ data: HomePageDto }>("/cms/home-page", {
      contentHtml: form.contentHtml,
      mobileTitle: form.mobileTitle.trim() || null,
      status: form.status,
    });
    if (data?.data) applyDto(data.data);
    ElMessage.success("已保存");
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "保存失败");
  } finally {
    saving.value = false;
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

.cms-form {
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

.muted {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.45;
  color: rgba(15, 23, 42, 0.5);
}

.form-item-editor :deep(.el-form-item__content) {
  margin-left: 0 !important;
  max-width: 100%;
  width: 100%;
}

.editor-block {
  width: 100%;
  min-width: 0;
}
</style>
