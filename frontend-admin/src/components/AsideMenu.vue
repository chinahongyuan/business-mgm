<template>
  <el-menu
    class="bm-menu"
    :router="true"
    :default-active="active"
    :collapse="false"
  >
    <AsideMenuNode v-for="m in items" :key="m.id" :node="m" />
  </el-menu>
</template>

<script setup lang="ts">
import { computed, watch } from "vue";
import { useRoute } from "vue-router";

import AsideMenuNode from "@/components/AsideMenuNode.vue";
import type { MenuNode } from "@/types/menu";

const props = defineProps<{ items: MenuNode[] }>();

const route = useRoute();
const active = computed(() => route.path);

/** 开发环境：父级仅展开子菜单；叶子项需配置 path，否则路由无法跳转（仅告警，不改变行为）。 */
function warnLeafMenuPaths(nodes: MenuNode[]) {
  if (!import.meta.env.DEV) return;
  const walk = (list: MenuNode[]) => {
    for (const n of list) {
      if (n.children?.length) walk(n.children);
      else if (!String(n.path ?? "").trim()) {
        console.warn(`[AsideMenu] 叶子菜单缺少 path（将无路由跳转）: id=${n.id} title=${n.title}`);
      }
    }
  };
  walk(nodes);
}

watch(
  () => props.items,
  (nodes) => warnLeafMenuPaths(nodes),
  { immediate: true, deep: true }
);
</script>

<style scoped>
.bm-menu {
  border-right: none;
  padding: 8px 8px 12px;
  background: transparent;
}

.bm-menu :deep(.el-menu-item),
.bm-menu :deep(.el-sub-menu__title) {
  border-radius: 12px;
  margin: 4px 0;
}

.bm-menu :deep(.el-menu-item.is-active) {
  background: rgba(37, 99, 235, 0.12);
}
</style>
