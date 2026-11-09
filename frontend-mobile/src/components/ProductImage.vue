<template>
  <picture class="product-image" :class="{ 'product-image--failed': failed }">
    <source v-if="srcset && !useOriginal" type="image/webp" :srcset="srcset" :sizes="sizes" />
    <img
      v-if="!failed"
      :key="retryVersion"
      :src="src"
      alt=""
      :width="media?.width"
      :height="media?.height"
      :loading="eager ? 'eager' : 'lazy'"
      :fetchpriority="priority ? 'high' : 'auto'"
      decoding="async"
      @error="onError"
    />
  </picture>
  <button v-if="failed" class="product-image__retry" type="button" aria-label="重新加载图片" @click.stop="retry">
    重新加载
  </button>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { imageSrcset, type MediaAsset } from "@/utils/media";

const props = withDefaults(defineProps<{
  src: string;
  media?: MediaAsset | null;
  eager?: boolean;
  priority?: boolean;
  sizes?: string;
}>(), { sizes: "(min-width: 1024px) 220px, 112px" });
const failed = ref(false);
const useOriginal = ref(false);
const retryVersion = ref(0);
const srcset = computed(() => imageSrcset(props.media, 640));
function onError() {
  if (srcset.value && !useOriginal.value) useOriginal.value = true;
  else failed.value = true;
}
function retry() {
  retryVersion.value++;
  failed.value = false;
  useOriginal.value = false;
}
watch(() => props.src, retry);
</script>

<style scoped>
.product-image { display: block; width: 100%; height: 100%; background: #e2e8f0; }
.product-image img { display: block; width: 100%; height: 100%; object-fit: cover; }
.product-image--failed { display: none; }
.product-image__retry {
  width: 100%; height: 100%; min-height: 44px; border: 0; padding: 8px;
  background: #e2e8f0; color: #334155; font: inherit; font-size: 12px; cursor: pointer;
}
.product-image__retry:focus-visible { outline: 2px solid #0369a1; outline-offset: -3px; }
</style>
