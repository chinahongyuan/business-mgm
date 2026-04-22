import { createRouter, createWebHistory } from "vue-router";

import { useSessionStore } from "@/stores/session";

import HomeView from "@/views/HomeView.vue";
/** 同步引用，避免 () => import() 的异步包装导致 keep-alive include 与组件 name 对不上、列表仍被整页销毁 */
import ProductListView from "@/views/ProductListView.vue";

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
      meta: { title: "首页" },
    },
    {
      path: "/products",
      name: "products",
      component: ProductListView,
      meta: { title: "商品", requiresAuth: true },
    },
    {
      path: "/products/:id",
      name: "product-detail",
      component: () => import("@/views/ProductDetailView.vue"),
      meta: { title: "商品详情", requiresAuth: true },
    },
    {
      path: "/:pathMatch(.*)*",
      name: "not-found",
      redirect: "/",
    },
  ],
  scrollBehavior(to, from) {
    // 从详情返回列表：不强制滚顶，由列表页 onActivated 恢复位置
    if (to.name === "products" && from?.name === "product-detail") {
      return false;
    }
    return { top: 0 };
  },
});

router.beforeEach((to) => {
  const session = useSessionStore();
  if (to.name === "home" && session.isLoggedIn()) {
    return { name: "products" };
  }
  if (to.meta.requiresAuth && !session.isLoggedIn()) {
    return { path: "/" };
  }
  return true;
});
