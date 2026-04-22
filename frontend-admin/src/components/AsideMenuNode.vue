<template>
  <!-- 有 children 时为分组：点击只展开/收起，不跳转路由 -->
  <el-sub-menu v-if="node.children?.length" :index="groupIndex">
    <template #title>
      <span class="bm-menu-title">
        <el-icon v-if="iconComp">
          <component :is="iconComp" />
        </el-icon>
        <span>{{ node.title }}</span>
      </span>
    </template>
    <AsideMenuNode v-for="c in node.children" :key="c.id" :node="c" />
  </el-sub-menu>

  <el-menu-item v-else :index="leafIndex" :route="leafRoute">
    <el-icon v-if="iconComp">
      <component :is="iconComp" />
    </el-icon>
    <span>{{ node.title }}</span>
  </el-menu-item>
</template>

<script setup lang="ts">
import { Menu as MenuIcon } from "@element-plus/icons-vue";
import * as Icons from "@element-plus/icons-vue";
import { computed } from "vue";

import type { MenuNode } from "@/types/menu";

const props = defineProps<{ node: MenuNode }>();

const groupIndex = computed(() => `g-${props.node.id}`);
const leafIndex = computed(() => props.node.path || `m-${props.node.id}`);
const leafRoute = computed(() => (props.node.path ? { path: props.node.path } : undefined));

const iconComp = computed(() => {
  const name = props.node.icon || "";
  const comp = (Icons as Record<string, unknown>)[name];
  return (typeof comp === "object" && comp) || MenuIcon;
});
</script>

<style scoped>
.bm-menu-title {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}
</style>
