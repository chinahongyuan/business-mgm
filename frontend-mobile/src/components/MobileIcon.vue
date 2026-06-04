<!-- 移动端列表用内联 SVG（stroke / fill 两套根节点，避免角标描边发糊） -->
<template>
  <!-- 角标用小实心图标 -->
  <svg
    v-if="isFill"
    class="mobile-icon mobile-icon--fill"
    :class="[`mobile-icon--${name}`, sizeClass]"
    viewBox="0 0 24 24"
    fill="currentColor"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
    focusable="false"
  >
    <template v-if="name === 'fireFill'">
      <!-- 简洁火焰形，避免 Heroicons 部分 path 在部分 SVG 解析器下非法 -->
      <path
        d="M12 3c-2 3-4 5-4 8a4 4 0 1 0 8 0c0-3-2-5-4-8z"
      />
    </template>
    <template v-else-if="name === 'starFill'">
      <path
        fill-rule="evenodd"
        clip-rule="evenodd"
        d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.006 5.404.434c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.267 5.273c.269 1.121-.96 2.019-1.96 1.425L12 18.354 7.373 21.18c-.999.593-2.229-.304-1.96-1.425l1.267-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.434 2.082-5.005Z"
      />
    </template>
    <template v-else-if="name === 'chatFill'">
      <path
        d="M4 4.5A2.5 2.5 0 0 1 6.5 2h11A2.5 2.5 0 0 1 20 4.5v7a2.5 2.5 0 0 1-2.5 2.5h-5.5l-4.2 3.15a.75.75 0 0 1-1.2-.6V14H6.5A2.5 2.5 0 0 1 4 11.5v-7Z"
      />
    </template>
  </svg>
  <svg
    v-else
    class="mobile-icon"
    :class="[`mobile-icon--${name}`, sizeClass]"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
    focusable="false"
  >
    <template v-if="name === 'search'">
      <path d="M21 21l-4.35-4.35M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z" />
    </template>
    <template v-else-if="name === 'mapPin'">
      <path d="M12 21s7-4.5 7-11a7 7 0 1 0 -14 0c0 6.5 7 11 7 11z" />
      <circle cx="12" cy="10" r="2" fill="currentColor" stroke="none" />
    </template>
    <template v-else-if="name === 'route'">
      <path d="M12 4v4M12 16v4M4 12h4M16 12h4" />
      <circle cx="12" cy="12" r="3" />
    </template>
    <template v-else-if="name === 'nearMe'">
      <!-- 同心圆 + 中心点：表达「相对我的距离」 -->
      <circle cx="12" cy="12" r="2.25" fill="currentColor" stroke="none" />
      <circle cx="12" cy="12" r="6.5" />
      <circle cx="12" cy="12" r="10" opacity="0.45" />
    </template>
    <template v-else-if="name === 'store'">
      <path d="M3 9l2-5h14l2 5v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9zM9 22V12h6v10" />
    </template>
    <template v-else-if="name === 'tagPrice'">
      <path d="M12 2l7 7-8 8-7-7V5a2 2 0 0 1 2-2h6z" />
      <circle cx="12" cy="9" r="1.5" fill="currentColor" stroke="none" />
    </template>
    <template v-else-if="name === 'sort'">
      <path d="M4 6h16M4 12h10M4 18h6" />
    </template>
    <template v-else-if="name === 'moon'">
      <!-- Heroicons outline：暂停营业 / 休息 -->
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </template>
    <template v-else-if="name === 'sun'">
      <!-- Heroicons outline：营业中 / 在岗 -->
      <path
        d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z"
      />
    </template>
  </svg>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    name:
      | "search"
      | "mapPin"
      | "nearMe"
      | "route"
      | "store"
      | "tagPrice"
      | "sort"
      | "moon"
      | "sun"
      | "fireFill"
      | "starFill"
      | "chatFill";
    size?: "xs" | "sm" | "md" | "lg";
  }>(),
  { size: "md" },
);

const fillNames = ["fireFill", "starFill", "chatFill"] as const;
const isFill = computed(() => (fillNames as readonly string[]).includes(props.name));

const sizeClass = computed(() => `mobile-icon--sz-${props.size}`);
</script>

<style scoped>
.mobile-icon {
  display: block;
  flex-shrink: 0;
}

.mobile-icon--fill {
  stroke: none;
}

.mobile-icon--sz-xs {
  width: 12px;
  height: 12px;
}

.mobile-icon--sz-sm {
  width: 14px;
  height: 14px;
}

.mobile-icon--sz-md {
  width: 18px;
  height: 18px;
}

.mobile-icon--sz-lg {
  width: 24px;
  height: 24px;
}
</style>
