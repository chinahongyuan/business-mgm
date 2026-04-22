<template>
  <div v-loading="loading" class="stats-screen" :class="{ 'stats-screen--light': !isDark }">
    <header class="stats-screen__hero">
      <div>
        <h1 class="stats-screen__title">区域统计</h1>
        <p class="stats-screen__sub">
          从商品「所属区域 / 城市」与移动端「IP 归属地 / 用户所选区域」多视角观察地域分布，便于区域运营与推广投放。
        </p>
      </div>
    </header>

    <div class="stats-grid">
      <section class="stats-panel stats-panel--half">
        <div class="stats-panel__head">
          <h2 class="stats-panel__title">商品 · 所属区域 TOP</h2>
          <p class="stats-panel__hint">mer_product.district</p>
        </div>
        <VChart class="stats-chart" :option="optProductDistrict" autoresize />
      </section>
      <section class="stats-panel stats-panel--half">
        <div class="stats-panel__head">
          <h2 class="stats-panel__title">移动端 · IP 归属地分布</h2>
          <p class="stats-panel__hint">用户侧上报 / 解析</p>
        </div>
        <VChart class="stats-chart stats-chart--short" :option="optIpPie" autoresize />
      </section>
      <section class="stats-panel stats-panel--half">
        <div class="stats-panel__head">
          <h2 class="stats-panel__title">移动端 · 用户所属区域</h2>
          <p class="stats-panel__hint">user_region</p>
        </div>
        <VChart class="stats-chart" :option="optUserRegion" autoresize />
      </section>
      <section class="stats-panel stats-panel--half">
        <div class="stats-panel__head">
          <h2 class="stats-panel__title">商品 · 所属城市 TOP</h2>
          <p class="stats-panel__hint">mer_product.city</p>
        </div>
        <VChart class="stats-chart" :option="optCity" autoresize />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { BarChart, PieChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { ElMessage } from "element-plus";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";
import VChart from "vue-echarts";

import { http } from "@/api/http";
import { useThemeStore } from "@/store/theme";
import { STATS_PALETTE, chartTheme } from "@/utils/statsChartTheme";

use([CanvasRenderer, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent]);

type Dim = { name: string; value: number };

const { isDark } = storeToRefs(useThemeStore());
const loading = ref(false);
const payload = ref<{
  productByDistrict: Dim[];
  mobileByIpRegion: Dim[];
  mobileByUserRegion: Dim[];
  productByCity: Dim[];
} | null>(null);

function hBar(names: string[], values: number[], dark: boolean) {
  const t = chartTheme(dark);
  return {
    color: STATS_PALETTE,
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: { color: t.text },
    },
    grid: { left: 8, right: 12, top: 8, bottom: 4, containLabel: true },
    xAxis: {
      type: "value",
      splitLine: { lineStyle: { color: t.splitLine } },
      axisLabel: { color: t.textWeak, fontSize: 11 },
    },
    yAxis: {
      type: "category",
      data: names,
      axisLine: { lineStyle: { color: t.axisLine } },
      axisLabel: { color: t.textMuted, fontSize: 11 },
    },
    series: [
      {
        type: "bar",
        data: values,
        barMaxWidth: 22,
        itemStyle: { borderRadius: [0, 6, 6, 0] },
      },
    ],
  };
}

function pieOption(data: Dim[], dark: boolean) {
  const t = chartTheme(dark);
  return {
    color: STATS_PALETTE,
    tooltip: {
      trigger: "item",
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: { color: t.text },
    },
    legend: {
      type: "scroll",
      bottom: 0,
      textStyle: { color: t.textMuted, fontSize: 11 },
    },
    series: [
      {
        type: "pie",
        radius: ["38%", "62%"],
        center: ["50%", "46%"],
        data: data.map((d) => ({ name: d.name, value: d.value })),
        label: { color: t.textMuted, fontSize: 11 },
        emphasis: { itemStyle: { shadowBlur: 12, shadowColor: "rgba(0,0,0,0.25)" } },
      },
    ],
  };
}

const optProductDistrict = computed(() => {
  const list = payload.value?.productByDistrict || [];
  const dark = isDark.value;
  const names = list.map((x) => x.name).reverse();
  const values = list.map((x) => x.value).reverse();
  return hBar(names, values, dark);
});

const optIpPie = computed(() => pieOption(payload.value?.mobileByIpRegion || [], isDark.value));

const optUserRegion = computed(() => {
  const list = payload.value?.mobileByUserRegion || [];
  const dark = isDark.value;
  const names = list.map((x) => x.name).reverse();
  const values = list.map((x) => x.value).reverse();
  return hBar(names, values, dark);
});

const optCity = computed(() => {
  const list = payload.value?.productByCity || [];
  const dark = isDark.value;
  const names = list.map((x) => x.name).reverse();
  const values = list.map((x) => x.value).reverse();
  return hBar(names, values, dark);
});

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get("/stats/region");
    payload.value = data?.data || null;
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "加载失败");
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>
