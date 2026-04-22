<template>
  <el-container class="bm-shell">
    <!-- 桌面：固定侧栏；窄屏：侧栏隐藏，改用抽屉（视口断点，非 UA） -->
    <el-aside v-show="!isNarrowLayout" class="bm-aside bm-aside--desktop" width="252px">
      <div class="bm-brand">
        <div class="bm-brand-mark" aria-hidden="true">M</div>
        <div class="bm-brand-text">
          <div class="bm-brand-title">System Management</div>
        </div>
      </div>

      <nav class="bm-aside-nav" aria-label="主导航">
        <AsideMenu :items="auth.menus" />
      </nav>
    </el-aside>

    <el-drawer
      v-if="isNarrowLayout"
      v-model="navDrawerOpen"
      direction="ltr"
      :size="drawerWidth"
      :with-header="false"
      class="bm-drawer"
      append-to-body
      @closed="onDrawerClosed"
    >
      <div class="bm-drawer-body">
        <div class="bm-brand bm-brand--drawer">
          <div class="bm-brand-mark" aria-hidden="true">M</div>
          <div class="bm-brand-text">
            <div class="bm-brand-title">System Management</div>
          </div>
        </div>
        <nav class="bm-aside-nav" aria-label="主导航">
          <AsideMenu :items="auth.menus" />
        </nav>
      </div>
    </el-drawer>

    <el-container class="bm-main-wrap">
      <el-header class="bm-header">
        <div class="bm-header-left">
          <el-button
            v-if="isNarrowLayout"
            class="bm-nav-toggle"
            :icon="Menu"
            circle
            text
            size="large"
            aria-label="打开导航菜单"
            @click="navDrawerOpen = true"
          />
          <div class="bm-page-title">{{ pageTitle }}</div>
        </div>
        <div class="bm-header-right">
          <el-tooltip
            :content="theme.isDark ? '切换为明亮模式' : '切换为黑暗模式'"
            placement="bottom"
            :show-after="400"
          >
            <el-button
              class="bm-theme-btn"
              :icon="theme.isDark ? Sunny : Moon"
              circle
              text
              size="large"
              aria-label="切换明暗主题"
              @click="theme.toggle()"
            />
          </el-tooltip>
          <el-dropdown trigger="click" @command="onUserCommand">
            <span class="bm-user">
              <el-avatar :size="32" class="bm-avatar">{{ userInitial }}</el-avatar>
              <span class="bm-user-name">{{ auth.user?.username || "管理员" }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="bm-main">
        <router-view v-slot="{ Component }">
          <transition name="bm-fade" mode="out-in">
            <component :is="Component" :key="route.fullPath" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ArrowDown, Menu, Moon, Sunny } from "@element-plus/icons-vue";
import { ElMessageBox } from "element-plus";
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import AsideMenu from "@/components/AsideMenu.vue";
import { useBreakpoints } from "@/composables/useBreakpoints";
import { useAuthStore } from "@/store/auth";
import { useThemeStore } from "@/store/theme";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const theme = useThemeStore();
const { isNarrowLayout } = useBreakpoints();

const navDrawerOpen = ref(false);
/** 抽屉宽度（Element Plus drawer size） */
const drawerWidth = "280px";

const pageTitle = computed(() => String(route.meta.title || "工作台"));
const userInitial = computed(() => (auth.user?.username?.slice(0, 1) || "管").toUpperCase());

watch(
  () => route.fullPath,
  () => {
    navDrawerOpen.value = false;
  }
);

function onDrawerClosed() {
  navDrawerOpen.value = false;
}

async function onUserCommand(cmd: string) {
  if (cmd !== "logout") return;
  await ElMessageBox.confirm("确定退出登录吗？", "提示", {
    type: "warning",
    confirmButtonText: "退出",
    cancelButtonText: "取消",
  });
  auth.logout();
  await router.replace("/login");
}
</script>

<style scoped>
.bm-shell {
  height: 100%;
  min-height: 100vh;
  background: radial-gradient(1200px 700px at 20% 0%, rgba(37, 99, 235, 0.08), transparent 60%),
    radial-gradient(900px 600px at 90% 10%, rgba(124, 58, 237, 0.07), transparent 55%), #f6f7fb;
}

.bm-aside {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  border-right: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(12px);
}

/* 菜单区域独立滚动，滚动条样式与整体（slate + 品牌蓝紫）一致 */
.bm-aside-nav {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
  scrollbar-color: rgba(37, 99, 235, 0.38) rgba(15, 23, 42, 0.06);
}

.bm-aside-nav::-webkit-scrollbar {
  width: 8px;
}

.bm-aside-nav::-webkit-scrollbar-track {
  margin: 6px 0;
  background: rgba(15, 23, 42, 0.04);
  border-radius: 999px;
}

.bm-aside-nav::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(37, 99, 235, 0.45), rgba(124, 58, 237, 0.42));
  border: 2px solid transparent;
  background-clip: padding-box;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.35) inset;
}

.bm-aside-nav::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, rgba(37, 99, 235, 0.62), rgba(124, 58, 237, 0.55));
}

.bm-aside-nav::-webkit-scrollbar-thumb:active {
  background: linear-gradient(180deg, rgba(29, 78, 216, 0.75), rgba(109, 40, 217, 0.68));
}

@media (prefers-reduced-motion: reduce) {
  .bm-aside-nav::-webkit-scrollbar-thumb {
    transition: none;
  }
}

.bm-brand {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 18px 16px 10px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.bm-brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: #fff;
  font-weight: 900;
  letter-spacing: 1px;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  box-shadow: 0 16px 34px rgba(37, 99, 235, 0.22);
}

.bm-brand-title {
  font-weight: 800;
  font-size: 14px;
  line-height: 1.2;
  color: #0f172a;
}

.bm-brand-sub {
  margin-top: 3px;
  font-size: 12px;
  color: rgba(15, 23, 42, 0.55);
}

.bm-main-wrap {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.bm-header-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.bm-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.bm-nav-toggle {
  flex-shrink: 0;
}

.bm-header {
  height: 64px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  padding-top: max(0px, env(safe-area-inset-top));
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(12px);
}

.bm-page-title {
  font-size: 15px;
  font-weight: 750;
  color: rgba(15, 23, 42, 0.88);
  letter-spacing: 0.2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.bm-user {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
  color: rgba(15, 23, 42, 0.78);
}

.bm-avatar {
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  color: #fff;
  font-weight: 800;
}

.bm-user-name {
  font-size: 13px;
  font-weight: 650;
}

.bm-main {
  flex: 1;
  min-height: 0;
  min-width: 0;
  padding: 18px;
  padding-bottom: calc(18px + env(safe-area-inset-bottom, 0px));
  overflow: auto;
  -webkit-overflow-scrolling: touch;
}

.bm-drawer-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  padding: 0 4px 12px;
}

.bm-brand--drawer {
  flex-shrink: 0;
}

.bm-fade-enter-active,
.bm-fade-leave-active {
  transition: opacity 100ms ease, transform 100ms ease;
}
.bm-fade-enter-from,
.bm-fade-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

@media (prefers-reduced-motion: reduce) {
  .bm-fade-enter-active,
  .bm-fade-leave-active {
    transition: none;
  }
  .bm-fade-enter-from,
  .bm-fade-leave-to {
    transform: none;
  }
}

@media (max-width: 900px) {
  .bm-aside--desktop {
    width: 220px !important;
  }
}

@media (max-width: 768px) {
  .bm-header {
    padding-left: max(12px, env(safe-area-inset-left));
    padding-right: max(12px, env(safe-area-inset-right));
  }

  .bm-user-name {
    display: none;
  }

  .bm-main {
    padding: 12px;
    padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px));
  }
}
</style>
