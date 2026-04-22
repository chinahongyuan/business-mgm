<template>
  <Teleport to="body">
    <div v-if="modelValue" class="ann-overlay" role="dialog" aria-modal="true" aria-labelledby="ann-title">
      <div class="ann-panel">
        <h2 id="ann-title" class="ann-title">公告</h2>
        <div class="ann-body ck-content" v-html="contentHtml" />
        <div v-if="mode === 'strict'" class="ann-strict">
          <p v-if="countdown > 0" class="ann-count">请阅读 {{ countdown }} 秒后可确认</p>
          <label class="ann-check">
            <input v-model="ack" type="checkbox" :disabled="countdown > 0" />
            <span>我已知晓</span>
          </label>
        </div>
        <div class="ann-actions">
          <button
            v-if="mode === 'strict'"
            type="button"
            class="ann-btn ann-btn--primary"
            :disabled="!ack || countdown > 0"
            @click="emitConfirm"
          >
            确定
          </button>
          <button v-else type="button" class="ann-btn ann-btn--primary" @click="emitClose">关闭</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    modelValue: boolean;
    contentHtml: string;
    mode: "strict" | "simple";
  }>(),
  {
    contentHtml: "",
  },
);

const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
  (e: "confirm"): void;
}>();

const ack = ref(false);
const countdown = ref(5);
let timer: ReturnType<typeof setInterval> | null = null;

watch(
  () => props.modelValue,
  (open) => {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    if (open && props.mode === "strict") {
      ack.value = false;
      countdown.value = 5;
      timer = setInterval(() => {
        countdown.value -= 1;
        if (countdown.value <= 0 && timer) {
          clearInterval(timer);
          timer = null;
        }
      }, 1000);
    } else if (open && props.mode === "simple") {
      ack.value = true;
      countdown.value = 0;
    }
    if (open) {
      nextTick(() => {
        document.querySelectorAll(".ann-body video").forEach((v) => {
          const videoEl = v as HTMLVideoElement;
          videoEl.setAttribute("playsinline", "");
          videoEl.setAttribute("webkit-playsinline", "");
        });
      });
    }
    if (!open) {
      nextTick(() => {
        document.querySelectorAll('.ann-body video').forEach((v) => {
          const videoEl = v as HTMLVideoElement;
          videoEl.pause();
          videoEl.currentTime = 0;
          videoEl.src = '';
          videoEl.load();
        });
      });
    }
  },
);

onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
});

function emitConfirm() {
  emit("update:modelValue", false);
  emit("confirm");
}

function emitClose() {
  emit("update:modelValue", false);
}
</script>

<style scoped>
.ann-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(15, 23, 42, 0.35);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: env(safe-area-inset-top, 0) 12px calc(12px + env(safe-area-inset-bottom, 0));
}

.ann-panel {
  width: 100%;
  max-width: 28rem;
  max-height: min(78vh, 640px);
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 16px 16px 12px 12px;
  box-shadow: 0 -12px 40px rgba(15, 23, 42, 0.12);
  overflow: hidden;
}

.ann-title {
  margin: 0;
  padding: 14px 16px 8px;
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
  flex-shrink: 0;
  text-align: center;
}

.ann-body {
  flex: 1;
  /* flex 子项默认 min-height:auto 时可能与 overflow:auto 在部分内核下产生滚动/裁切异常 */
  min-height: 0;
  overflow: auto;
  padding: 0 16px 12px;
  font-size: 0.9375rem;
  line-height: 1.55;
  color: #334155;
  -webkit-overflow-scrolling: touch;
  /* 将公告正文绘制限制在本滚动盒内，减轻 WebKit/Chrome 在「视频单独合成层 + 滚动」时溢出遮罩的 bug */
  contain: paint;
  isolation: isolate;
}

.ann-body :deep(img) {
  max-width: 100%;
  height: auto;
  vertical-align: middle;
  border-radius: 8px;
}

.ann-body :deep(video) {
  display: block;
  max-width: 100%;
  width: 100%;
  height: auto;
  border-radius: 8px;
  background: #000;
  object-fit: contain;
  /* 避免 translateZ(0) 等将 video 强提到独立合成层，播放后在 overflow 内滚动时常见「画面粘住/跑出弹窗」 */
  max-height: 70vh;
}

.ann-strict {
  padding: 0 16px 8px;
  flex-shrink: 0;
}

.ann-count {
  margin: 0 0 8px;
  font-size: 0.8125rem;
  color: #64748b;
}

.ann-check {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
  color: #0f172a;
  cursor: pointer;
}

.ann-check input {
  width: 18px;
  height: 18px;
  accent-color: #0284c7;
}

.ann-actions {
  padding: 12px 16px calc(12px + env(safe-area-inset-bottom, 0));
  border-top: 1px solid rgba(148, 163, 184, 0.12);
  flex-shrink: 0;
}

.ann-btn {
  width: 100%;
  padding: 12px 16px;
  border: none;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
}

.ann-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.ann-btn--primary {
  background: linear-gradient(120deg, #0ea5e9 0%, #0284c7 50%, #6366f1 100%);
  color: #fff;
}

@media (min-width: 1024px) {
  .ann-overlay {
    align-items: center;
    justify-content: center;
    padding: 24px;
  }

  .ann-panel {
    max-width: min(36rem, 100%);
    border-radius: 16px;
    box-shadow:
      0 24px 64px rgba(15, 23, 42, 0.14),
      0 0 0 1px rgba(148, 163, 184, 0.12);
  }
}
</style>
