import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "@/store/auth";

import AdminLayout from "@/layouts/AdminLayout.vue";
import LoginView from "@/views/LoginView.vue";
import DashboardHome from "@/views/DashboardHome.vue";
import AdminUserManage from "@/views/system/AdminUserManage.vue";
import LoginLogs from "@/views/system/LoginLogs.vue";
import MenuManage from "@/views/system/MenuManage.vue";
import OperationLogs from "@/views/system/OperationLogs.vue";
import ProductList from "@/views/merchant/ProductList.vue";
import ProductTrash from "@/views/merchant/ProductTrash.vue";
import ProductTagManage from "@/views/merchant/ProductTagManage.vue";
import MessageBoardList from "@/views/MessageBoardList.vue";
import MobileUserList from "@/views/app/MobileUserList.vue";
import PasswordList from "@/views/app/PasswordList.vue";

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/login",
      name: "login",
      component: LoginView,
      meta: { public: true, title: "登录" },
    },
    {
      path: "/",
      component: AdminLayout,
      meta: { requiresAuth: true },
      children: [
        { path: "", redirect: "/dashboard" },
        {
          path: "dashboard",
          name: "dashboard",
          component: DashboardHome,
          meta: { title: "工作台" },
        },
        {
          path: "system/menus",
          name: "system-menus",
          component: MenuManage,
          meta: { title: "菜单管理" },
        },
        {
          path: "system/logs/login",
          name: "system-login-logs",
          component: LoginLogs,
          meta: { title: "登录日志" },
        },
        {
          path: "system/logs/operation",
          name: "system-operation-logs",
          component: OperationLogs,
          meta: { title: "操作日志" },
        },
        {
          path: "system/users",
          name: "system-users",
          component: AdminUserManage,
          meta: { title: "用户管理" },
        },
        {
          path: "merchant/tags",
          name: "merchant-tags",
          component: ProductTagManage,
          meta: { title: "标签管理" },
        },
        {
          path: "merchant/products",
          name: "merchant-products",
          component: ProductList,
          meta: { title: "商品管理" },
        },
        {
          path: "merchant/products/trash",
          name: "merchant-products-trash",
          component: ProductTrash,
          meta: { title: "商品回收站" },
        },
        {
          path: "merchant/products/create",
          name: "merchant-product-create",
          component: () => import("@/views/merchant/ProductEdit.vue"),
          meta: { title: "新增商品" },
        },
        {
          path: "merchant/products/:id/edit",
          name: "merchant-product-edit",
          component: () => import("@/views/merchant/ProductEdit.vue"),
          meta: { title: "编辑商品" },
        },
        {
          path: "message-boards",
          name: "message-boards",
          component: MessageBoardList,
          meta: { title: "留言板" },
        },
        {
          path: "app/users",
          name: "app-users",
          component: MobileUserList,
          meta: { title: "移动端用户" },
        },
        {
          path: "passwords",
          name: "passwords",
          component: PasswordList,
          meta: { title: "密码管理" },
        },
        {
          path: "announcements",
          name: "announcements",
          component: () => import("@/views/cms/AnnouncementEdit.vue"),
          meta: { title: "娱乐指南管理" },
        },
        {
          path: "bulletins",
          name: "bulletins",
          component: () => import("@/views/cms/BulletinEdit.vue"),
          meta: { title: "公告管理" },
        },
        {
          path: "home-pages",
          name: "home-pages",
          component: () => import("@/views/cms/HomePageEdit.vue"),
          meta: { title: "首页管理" },
        },
        {
          path: "stats/activity",
          name: "stats-activity",
          component: () => import("@/views/stats/ActivityStats.vue"),
          meta: { title: "活跃度统计" },
        },
        {
          path: "stats/region",
          name: "stats-region",
          component: () => import("@/views/stats/RegionStats.vue"),
          meta: { title: "区域统计" },
        },
        {
          path: "stats/online-users",
          name: "stats-online-users",
          component: () => import("@/views/stats/OnlineUsersStats.vue"),
          meta: { title: "在线用户统计" },
        },
        {
          path: "stats/product-attention",
          name: "stats-product-attention",
          component: () => import("@/views/stats/ProductAttentionStats.vue"),
          meta: { title: "商品关注度统计" },
        },
        // 未匹配的后台子路径（如 /dashboard/xxx）→ 回工作台
        {
          path: ":pathMatch(.*)*",
          name: "admin-fallback",
          redirect: { name: "dashboard" },
        },
      ],
    },
    // 未匹配的顶层路径（如 /foo）→ 回工作台（未登录时由守卫改去登录页）
    {
      path: "/:pathMatch(.*)*",
      name: "global-fallback",
      redirect: { name: "dashboard" },
    },
  ],
  scrollBehavior() {
    return { top: 0 };
  },
});

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore();
  if (to.meta.public) {
    if (auth.token && to.path === "/login") {
      return next({ path: "/dashboard" });
    }
    return next();
  }
  if (!auth.token) {
    return next({ path: "/login", query: { redirect: to.fullPath } });
  }
  if (!auth.user) {
    try {
      await auth.fetchMe();
    } catch {
      auth.logout();
      return next({ path: "/login", query: { redirect: to.fullPath } });
    }
  }
  return next();
});
