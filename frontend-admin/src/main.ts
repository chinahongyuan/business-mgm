import { createApp } from "vue";
import ElementPlus from "element-plus";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import "element-plus/dist/index.css";
import "element-plus/theme-chalk/dark/css-vars.css";
import * as ElementPlusIconsVue from "@element-plus/icons-vue";

import App from "./App.vue";
import { router } from "./router";
import { pinia } from "./store";
import { useThemeStore } from "./store/theme";

import "./styles/global.css";
import "./styles/table-column-resize.css";
import "./styles/responsive.css";
import "./styles/theme-dark.css";
import "./styles/stats-screen.css";

const app = createApp(App);
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component);
}
app.use(pinia);
useThemeStore().init();
app.use(router);
app.use(ElementPlus, { locale: zhCn });
app.mount("#app");
