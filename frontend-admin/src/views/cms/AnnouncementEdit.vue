<template>
  <div class="page">
    <el-card v-loading="loading" class="panel" shadow="never">
      <template #header>
        <div class="card-head">
          <span class="toolbar-title">公告管理</span>
          <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
        </div>
      </template>

      <el-form label-width="120px" class="form cms-form">
        <section class="form-section">
          <h3 class="form-section-title">公告状态</h3>
          <el-form-item label="发布状态">
            <el-radio-group v-model="form.status">
              <el-radio value="published">发布</el-radio>
              <el-radio value="draft">未发布</el-radio>
            </el-radio-group>
          </el-form-item>
        </section>

        <section class="form-section">
          <h3 class="form-section-title">公告浏览情况</h3>
          <el-row :gutter="20">
            <el-col :xs="24" :sm="12" :md="6">
              <div class="read-stat">
                <div class="read-stat__label">公告浏览量</div>
                <div class="read-stat__value">{{ meta.viewCount }}</div>
              </div>
            </el-col>
            <el-col :xs="24" :sm="12" :md="6">
              <div class="read-stat">
                <div class="read-stat__label">最新浏览时间</div>
                <div class="read-stat__value">{{ formatDateTime(meta.lastViewAt) }}</div>
              </div>
            </el-col>
            <el-col :xs="24" :sm="12" :md="6">
              <div class="read-stat">
                <div class="read-stat__label">最新访客 IP</div>
                <div class="read-stat__value">{{ meta.lastViewUserIp ?? "—" }}</div>
              </div>
            </el-col>
            <el-col :xs="24" :sm="12" :md="6">
              <div class="read-stat">
                <div class="read-stat__label">最新访客 IP 归属地</div>
                <div class="read-stat__value">{{ meta.lastViewIpRegion ?? "—" }}</div>
              </div>
            </el-col>
          </el-row>
        </section>

        <section class="form-section form-section--last">
          <h3 class="form-section-title">公告内容</h3>
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
import { formatDateTime } from "@/utils/datetime";

type AnnouncementDto = {
  id: number;
  contentHtml: string;
  status: "published" | "draft";
  viewCount: number;
  lastViewAt: string | null;
  lastViewUserId: number | null;
  lastViewUserIp: string | null;
  lastViewIpRegion: string | null;
};

const loading = ref(false);
const saving = ref(false);

const form = reactive({
  contentHtml: "",
  status: "draft" as "published" | "draft",
});

const meta = reactive({
  viewCount: 0,
  lastViewAt: null as string | null,
  lastViewUserId: null as number | null,
  lastViewUserIp: null as string | null,
  lastViewIpRegion: null as string | null,
});

function applyDto(d: AnnouncementDto) {
  form.contentHtml = d.contentHtml || "";
  form.status = d.status === "published" ? "published" : "draft";
  meta.viewCount = d.viewCount ?? 0;
  meta.lastViewAt = d.lastViewAt;
  meta.lastViewUserId = d.lastViewUserId;
  meta.lastViewUserIp = d.lastViewUserIp ?? null;
  meta.lastViewIpRegion = d.lastViewIpRegion;
}

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get<{ data: AnnouncementDto }>("/cms/announcement");
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
    const { data } = await http.put<{ data: AnnouncementDto }>("/cms/announcement", {
      contentHtml: form.contentHtml,
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

.read-stat {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(248, 250, 252, 0.65);
  box-sizing: border-box;
}

.read-stat__label {
  font-size: 12px;
  color: rgba(15, 23, 42, 0.5);
  margin-bottom: 6px;
}

.read-stat__value {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  word-break: break-all;
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
