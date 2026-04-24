<template>
  <div class="app-root">
    <div class="app-shell">
      <!--
        仅缓存商品列表；与 sessionStorage 中的 scrollY 配合。
        key=visitorKey：同一会话内列表↔详情仍复用缓存；重登后 visitorKey 变，强制新 mount 走 onMounted 拉全量数据，避免 401 后只触发 onActivated 时列表为空。
      -->
      <router-view v-slot="{ Component }">
        <keep-alive include="ProductListView">
          <component :is="Component" v-if="Component" :key="visitorKey || 'anon'" />
        </keep-alive>
      </router-view>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";

import { useSessionStore } from "@/stores/session";

const { visitorKey } = storeToRefs(useSessionStore());
</script>

<style scoped>
.app-root {
  min-height: 100vh;
  min-height: 100dvh;
}

.app-shell {
  min-height: 100vh;
  min-height: 100dvh;
}

/* 宽屏：居中内容区（参考管理后台主区域 max-width + 留白），不收紧移动端全宽 */
@media (min-width: 1024px) {
  .app-shell {
    max-width: var(--mweb-shell-max, 1440px);
    margin-inline: auto;
    padding-inline: 24px;
    padding-top: 12px;
    padding-bottom: 28px;
    box-sizing: border-box;
  }
}
</style>
