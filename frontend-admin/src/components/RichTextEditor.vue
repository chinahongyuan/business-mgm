<template>
  <div class="bm-rich ck-editor-host">
    <Ckeditor v-model="html" :editor="editor" :config="config" />
  </div>
</template>

<script setup lang="ts">
import { Ckeditor } from "@ckeditor/ckeditor5-vue";
import { ClassicEditor } from "@ckeditor/ckeditor5-editor-classic";
import { Essentials } from "@ckeditor/ckeditor5-essentials";
import { Paragraph } from "@ckeditor/ckeditor5-paragraph";
import { Bold, Italic, Underline, Strikethrough } from "@ckeditor/ckeditor5-basic-styles";
import { Link } from "@ckeditor/ckeditor5-link";
import { List } from "@ckeditor/ckeditor5-list";
import {
  Image,
  ImageUpload,
  ImageToolbar,
  ImageCaption,
  ImageResize,
  ImageStyle,
} from "@ckeditor/ckeditor5-image";
import { BlockQuote } from "@ckeditor/ckeditor5-block-quote";
import { Heading } from "@ckeditor/ckeditor5-heading";
import { Table, TableToolbar } from "@ckeditor/ckeditor5-table";
import { MediaEmbed } from "@ckeditor/ckeditor5-media-embed";
import { Indent, IndentBlock } from "@ckeditor/ckeditor5-indent";
import { PasteFromOffice } from "@ckeditor/ckeditor5-paste-from-office";
import { GeneralHtmlSupport } from "@ckeditor/ckeditor5-html-support";
import { SourceEditing } from "@ckeditor/ckeditor5-source-editing";
import { FileRepository } from "@ckeditor/ckeditor5-upload";
import { ButtonView } from "@ckeditor/ckeditor5-ui";
import { Font } from "@ckeditor/ckeditor5-font";
import type { Editor } from "@ckeditor/ckeditor5-core";
import { ElMessage } from "element-plus";
import { ref, watch } from "vue";

import { http } from "@/api/http";

import "ckeditor5/ckeditor5.css";
import "ckeditor5/ckeditor5-content.css";

const props = defineProps<{ modelValue: string }>();
const emit = defineEmits<{ "update:modelValue": [v: string] }>();

const html = ref(props.modelValue || "");
const editor = ClassicEditor;
watch(
  () => props.modelValue,
  (v) => {
    if (v !== html.value) html.value = v || "";
  },
);

watch(html, (v) => emit("update:modelValue", v));

function uploadAdapterPlugin(editor: Editor) {
  editor.plugins.get(FileRepository).createUploadAdapter = (loader) => ({
    upload: () =>
      loader.file.then(
        (file) =>
          new Promise<{ default: string }>((resolve, reject) => {
            const fd = new FormData();
            fd.append("file", file as File);
            http
              .post<{ data: { url: string } }>("/upload", fd, {
                headers: { "Content-Type": "multipart/form-data" },
              })
              .then((res) => resolve({ default: res.data.data.url }))
              .catch(reject);
          }),
      ),
    abort: () => {},
  });
}

function escapeHtmlAttr(s: string) {
  return s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

function insertVideoSnippet(editor: Editor, url: string) {
  const snippet = `<figure class="media"><video controls preload="metadata" playsinline src="${url.replace(/"/g, "&quot;")}" style="max-width:100%;height:auto;display:block"></video></figure>`;
  try {
    const viewFragment = editor.data.processor.toView(snippet);
    const modelFragment = editor.data.toModel(viewFragment);
    editor.model.insertContent(modelFragment);
  } catch {
    editor.setData(`${editor.getData()}${snippet}`);
  }
}

/** 从 model 选区取根内路径的快照，供插入前用 createPositionFromPath 还原（避免 Position 在异步后失效/被重绑） */
function snapshotModelPath(editor: Editor): number[] | null {
  const root = editor.model.document.getRoot();
  if (!root) return null;
  try {
    const pos = editor.model.document.selection.getFirstPosition();
    if (!pos || pos.root !== root) return null;
    return [...pos.path];
  } catch {
    return null;
  }
}

/** 一次选择多个图片文件，依次上传并插入 */
function batchUploadImagesPlugin(editor: Editor) {
  editor.ui.componentFactory.add("batchUploadImages", (locale) => {
    const view = new ButtonView(locale);
    view.set({
      label: "批量上传图片",
      tooltip: "一次可选多个图片文件",
      withText: true,
    });
    /** 工具栏/按钮在 pointerdown 时往往仍能读到「进按钮前」的 model 选区；execute 时焦点已变，选区可能已被清空到末尾。 */
    let pathFromPreToolbarPointer: number[] | null = null;
    const capturePathOnPointerDown = () => {
      pathFromPreToolbarPointer = snapshotModelPath(editor);
    };
    let pointerListenerAttached = false;
    const attachPointerListener = () => {
      if (!view.isRendered || !view.element || pointerListenerAttached) return;
      pointerListenerAttached = true;
      const el = view.element;
      el.addEventListener("pointerdown", capturePathOnPointerDown, { capture: true });
      editor.on("destroy", () => {
        el.removeEventListener("pointerdown", capturePathOnPointerDown, { capture: true });
      });
    };
    view.on("change:isRendered", attachPointerListener);
    attachPointerListener();
    view.on("execute", () => {
      const pathForInsert =
        pathFromPreToolbarPointer && pathFromPreToolbarPointer.length
          ? [...pathFromPreToolbarPointer]
          : snapshotModelPath(editor);
      const input = document.createElement("input");
      input.type = "file";
      input.multiple = true;
      input.accept = "image/*";
      input.onchange = () => {
        const files = Array.from(input.files || []);
        if (!files.length) return;
        void (async () => {
          let ok = 0;
          let fail = 0;
          const urls: string[] = [];
          for (const file of files) {
            try {
              if (!file.type.startsWith("image/")) {
                fail += 1;
                continue;
              }
              const fd = new FormData();
              fd.append("file", file);
              const res = await http.post<{ data: { url: string } }>("/upload", fd, {
                headers: { "Content-Type": "multipart/form-data" },
              });
              urls.push(res.data.data.url);
              ok += 1;
            } catch {
              fail += 1;
              ElMessage.error(`上传失败：${file.name}`);
            }
          }
          if (urls.length) {
            const html = urls
              .map(
                (u) =>
                  `<p><img src="${escapeHtmlAttr(u)}" alt="" style="max-width:100%"></p>`,
              )
              .join("");
            const root = editor.model.document.getRoot();
            if (!root) return;
            const insertPath = pathForInsert;
            editor.model.change(() => {
              const viewFragment = editor.data.processor.toView(html);
              const modelFragment = editor.data.toModel(viewFragment);
              let position;
              if (insertPath) {
                try {
                  position = editor.model.createPositionFromPath(root, insertPath);
                } catch {
                  position = editor.model.createPositionAt(root, "end");
                }
              } else {
                position = editor.model.createPositionAt(root, "end");
              }
              editor.model.insertContent(modelFragment, position);
            });
          }
          if (ok > 0 && fail === 0) ElMessage.success(`已上传 ${ok} 张图片`);
          else if (ok > 0 && fail > 0) ElMessage.warning(`成功 ${ok} 张，失败 ${fail} 张`);
        })();
      };
      input.click();
    });
    return view;
  });
}

/** 一次选择多个视频文件，依次上传并插入 */
function batchUploadVideosPlugin(editor: Editor) {
  editor.ui.componentFactory.add("batchUploadVideos", (locale) => {
    const view = new ButtonView(locale);
    view.set({
      label: "批量上传视频",
      tooltip: "一次可选多个视频文件",
      withText: true,
    });
    view.on("execute", () => {
      const input = document.createElement("input");
      input.type = "file";
      input.multiple = true;
      input.accept = "video/*";
      input.onchange = () => {
        const files = Array.from(input.files || []);
        if (!files.length) return;
        void (async () => {
          let ok = 0;
          let fail = 0;
          for (const file of files) {
            try {
              if (!file.type.startsWith("video/")) {
                fail += 1;
                continue;
              }
              const fd = new FormData();
              fd.append("file", file);
              const res = await http.post<{ data: { url: string } }>("/upload", fd, {
                headers: { "Content-Type": "multipart/form-data" },
              });
              const url = res.data.data.url;
              insertVideoSnippet(editor, url);
              await new Promise((resolve) => setTimeout(resolve, 50));
              ok += 1;
            } catch {
              fail += 1;
              ElMessage.error(`上传失败：${file.name}`);
            }
          }
          if (ok > 0 && fail === 0) ElMessage.success(`已上传 ${ok} 个视频`);
          else if (ok > 0 && fail > 0) ElMessage.warning(`成功 ${ok} 个，失败 ${fail} 个`);
        })();
      };
      input.click();
    });
    return view;
  });
}

const config = {
  licenseKey: "GPL",
  plugins: [
    Essentials,
    Paragraph,
    Bold,
    Italic,
    Underline,
    Strikethrough,
    Font,
    Link,
    List,
    Image,
    ImageUpload,
    ImageToolbar,
    ImageCaption,
    ImageResize,
    ImageStyle,
    BlockQuote,
    Heading,
    Table,
    TableToolbar,
    MediaEmbed,
    Indent,
    IndentBlock,
    PasteFromOffice,
    GeneralHtmlSupport,
    SourceEditing,
    uploadAdapterPlugin,
    batchUploadImagesPlugin,
    batchUploadVideosPlugin,
  ],
  htmlSupport: {
    allow: [
      {
        name: /^.+$/,
        attributes: true,
        classes: true,
        styles: true,
      },
    ],
  },
  toolbar: {
    items: [
      "heading",
      "|",
      "fontSize",
      "fontFamily",
      "|",
      "fontColor",
      "fontBackgroundColor",
      "|",
      "bold",
      "italic",
      "underline",
      "strikethrough",
      "link",
      "|",
      "bulletedList",
      "numberedList",
      "|",
      "outdent",
      "indent",
      "|",
      "imageUpload",
      "batchUploadImages",
      "batchUploadVideos",
      "mediaEmbed",
      "blockQuote",
      "insertTable",
      "|",
      "sourceEditing",
      "|",
      "undo",
      "redo",
    ],
  },
  heading: {
    options: [
      { model: "paragraph", title: "正文", class: "ck-heading_paragraph" },
      { model: "heading2", view: "h2", title: "标题 2", class: "ck-heading_heading2" },
      { model: "heading3", view: "h3", title: "标题 3", class: "ck-heading_heading3" },
    ],
  },
  fontSize: {
    options: [9, 10, 11, 12, 13, "default", 15, 16, 18, 20, 22, 24, 28, 32],
    supportAllValues: true,
  },
  fontFamily: {
    supportAllValues: true,
    options: [
      "default",
      { title: "微软雅黑", model: "Microsoft YaHei, PingFang SC, Hiragino Sans GB, sans-serif" },
      { title: "宋体", model: "SimSun, Songti SC, STSong, serif" },
      { title: "黑体", model: "SimHei, STHeiti, Microsoft YaHei, sans-serif" },
      { title: "楷体", model: "KaiTi, STKaiti, KaiTi_GB2312, serif" },
      { title: "仿宋", model: "FangSong, STFangsong, serif" },
      { title: "苹方 / 冬青", model: "PingFang SC, Hiragino Sans GB, Microsoft YaHei, sans-serif" },
      { title: "Arial", model: "Arial, Helvetica, sans-serif" },
      { title: "Georgia", model: "Georgia, Times New Roman, serif" },
      { title: "等宽", model: "Consolas, Courier New, monospace" },
    ],
  },
  image: {
    toolbar: [
      "imageStyle:inline",
      "imageStyle:block",
      "imageStyle:side",
      "|",
      "toggleImageCaption",
      "imageTextAlternative",
    ],
  },
  placeholder:
    "支持图文排版；可设置中文字体、字号、颜色；单张图片上传或批量上传图片与视频，亦可插入媒体链接",
};
</script>

<style scoped>
.bm-rich {
  width: 100%;
}

.ck-editor-host :deep(.ck-editor__editable) {
  min-height: 360px;
}

.ck-editor-host :deep(.ck-content video) {
  max-width: 100%;
  height: auto;
}

.ck-editor-host :deep(.ck-toolbar) {
  flex-wrap: wrap;
  gap: 4px;
}

/* 编辑区优先使用可显示中文的字体栈，与「字体」下拉一致 */
.ck-editor-host :deep(.ck-content) {
  font-family: "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", SimSun, sans-serif;
}
</style>
