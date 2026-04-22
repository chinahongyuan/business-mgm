<template>
  <div v-loading="loading" class="stats-screen" :class="{ 'stats-screen--light': !isDark }">
    <header class="stats-screen__hero">
      <div>
        <h1 class="stats-screen__title">商品关注度统计</h1>
        <p class="stats-screen__sub">
          围绕商品访问、上下架、星级与标签关联热度，帮助识别爆款与长尾，支持运营与推广策略。
        </p>
      </div>
    </header>

    <section v-if="kpis.length" class="stats-kpi">
      <div v-for="k in kpis" :key="k.label" class="stats-kpi__card">
        <div class="stats-kpi__label">{{ k.label }}</div>
        <div>
          <span class="stats-kpi__value">{{ String(k.value ?? 0) }}</span>
          <span class="stats-kpi__suffix">{{ k.suffix }}</span>
        </div>
      </div>
    </section>

    <div class="stats-grid">
      <section class="stats-panel stats-panel--half">
        <div class="stats-panel__head">
          <h2 class="stats-panel__title">上下架结构</h2>
          <p class="stats-panel__hint">在售 / 下架</p>
        </div>
        <VChart class="stats-chart stats-chart--short" :option="optShelf" autoresize />
      </section>
      <section class="stats-panel stats-panel--half">
        <div class="stats-panel__head">
          <h2 class="stats-panel__title">星级分布</h2>
          <p class="stats-panel__hint">mer_product.star_rating</p>
        </div>
        <VChart class="stats-chart stats-chart--short" :option="optStar" autoresize />
      </section>
      <section class="stats-panel">
        <div class="stats-panel__head">
          <h2 class="stats-panel__title">访问量 TOP（商品）</h2>
          <p class="stats-panel__hint">按 visit_count 降序</p>
        </div>
        <VChart class="stats-chart stats-chart--tall" :option="optTop" autoresize />
      </section>
      <section class="stats-panel">
        <div class="stats-panel__head">
          <h2 class="stats-panel__title">标签热度</h2>
          <p class="stats-panel__hint">关联商品数</p>
        </div>
        <VChart class="stats-chart" :option="optTag" autoresize />
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
type TopRow = { id: number; name: string; visitCount: number; city: string; district: string; status: string };

const { isDark } = storeToRefs(useThemeStore());
const loading = ref(false);
const payload = ref<{
  kpis: { label: string; value: number; suffix: string }[];
  shelfPie: Dim[];
  topProducts: TopRow[];
  starDistribution: Dim[];
  tagHot: Dim[];
} | null>(null);

const kpis = computed(() => payload.value?.kpis || []);

const optShelf = computed(() => {
  const t = chartTheme(isDark.value);
  const data = payload.value?.shelfPie || [];
  return {
    color: [STATS_PALETTE[2], STATS_PALETTE[0]],
    tooltip: {
      trigger: "item",
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: { color: t.text },
    },
    legend: { bottom: 0, textStyle: { color: t.textMuted, fontSize: 11 } },
    series: [
      {
        type: "pie",
        radius: ["40%", "65%"],
        center: ["50%", "46%"],
        data: data.map((d) => ({ name: d.name, value: d.value })),
        label: { color: t.textMuted, fontSize: 11 },
      },
    ],
  };
});

const optStar = computed(() => {
  const t = chartTheme(isDark.value);
  const list = payload.value?.starDistribution || [];
  return {
    color: STATS_PALETTE,
    tooltip: {
      trigger: "axis",
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: { color: t.text },
    },
    grid: { left: 8, right: 8, top: 28, bottom: 4, containLabel: true },
    xAxis: {
      type: "category",
      data: list.map((x) => x.name),
      axisLabel: { color: t.textMuted, fontSize: 11, rotate: 0 },
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { color: t.splitLine } },
      axisLabel: { color: t.textWeak, fontSize: 11 },
    },
    series: [{ type: "bar", data: list.map((x) => x.value), barMaxWidth: 36, itemStyle: { borderRadius: [6, 6, 0, 0] } }],
  };
});

const optTop = computed(() => {
  const list = payload.value?.topProducts || [];
  const dark = isDark.value;
  const t = chartTheme(dark);
  const names = list.map((x) => x.name.slice(0, 18) + (x.name.length > 18 ? "…" : "")).reverse();
  const values = list.map((x) => x.visitCount).reverse();
  return {
    color: ["#38bdf8"],
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
      axisLabel: { color: t.textMuted, fontSize: 11 },
    },
    series: [{ type: "bar", data: values, barMaxWidth: 20, itemStyle: { borderRadius: [0, 6, 6, 0] } }],
  };
});

const optTag = computed(() => {
  const t = chartTheme(isDark.value);
  const list = payload.value?.tagHot || [];
  return {
    color: STATS_PALETTE,
    tooltip: {
      trigger: "axis",
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: { color: t.text },
    },
    grid: { left: 8, right: 8, top: 28, bottom: 4, containLabel: true },
    xAxis: {
      type: "category",
      data: list.map((x) => x.name),
      axisLabel: { color: t.textMuted, fontSize: 11, rotate: 28 },
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { color: t.splitLine } },
      axisLabel: { color: t.textWeak, fontSize: 11 },
    },
    series: [
      {
        type: "bar",
        data: list.map((x) => x.value),
        barMaxWidth: 28,
        itemStyle: { borderRadius: [6, 6, 0, 0] },
      },
    ],
  };
});

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get("/stats/product-attention");
    payload.value = data?.data || null;
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "加载失败");
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>
