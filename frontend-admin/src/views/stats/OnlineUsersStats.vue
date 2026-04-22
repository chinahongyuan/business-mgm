<template>
  <div v-loading="loading" class="stats-screen" :class="{ 'stats-screen--light': !isDark }">
    <header class="stats-screen__hero">
      <div>
        <h1 class="stats-screen__title">在线用户统计</h1>
        <p class="stats-screen__sub">
          基于「最近心跳 / 活跃时间」推断在线窗口（约 5 分钟）、近 24 小时活跃规模、账号状态结构与 7 日活跃趋势，支撑运维与风控。
        </p>
      </div>
    </header>

    <section v-if="kpis.length" class="stats-kpi">
      <div v-for="k in kpis" :key="k.label" class="stats-kpi__card">
        <div class="stats-kpi__label">{{ k.label }}</div>
        <div>
          <span class="stats-kpi__value">{{ formatKpi(k) }}</span>
          <span class="stats-kpi__suffix">{{ k.suffix }}</span>
        </div>
      </div>
    </section>

    <div class="stats-grid">
      <section class="stats-panel stats-panel--half">
        <div class="stats-panel__head">
          <h2 class="stats-panel__title">账号状态结构</h2>
          <p class="stats-panel__hint">正常 / 禁用</p>
        </div>
        <VChart class="stats-chart stats-chart--short" :option="optPie" autoresize />
      </section>
      <section class="stats-panel stats-panel--half">
        <div class="stats-panel__head">
          <h2 class="stats-panel__title">近 7 日活跃（按日）</h2>
          <p class="stats-panel__hint">当日有访问的用户数</p>
        </div>
        <VChart class="stats-chart stats-chart--tall" :option="optLine" autoresize />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { LineChart, PieChart } from "echarts/charts";
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

use([CanvasRenderer, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent]);

type Dim = { name: string; value: number };

const { isDark } = storeToRefs(useThemeStore());
const loading = ref(false);
const payload = ref<{
  kpis: { label: string; value: number; suffix: string }[];
  statusPie: Dim[];
  dauByDay: { labels: string[]; values: number[] };
} | null>(null);

const kpis = computed(() => payload.value?.kpis || []);

function formatKpi(k: { value: number; suffix: string }) {
  return String(k.value ?? 0);
}

const optPie = computed(() => {
  const t = chartTheme(isDark.value);
  const data = payload.value?.statusPie || [];
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

const optLine = computed(() => {
  const p = payload.value?.dauByDay;
  const dark = isDark.value;
  const t = chartTheme(dark);
  const labels = p?.labels || [];
  const values = p?.values || [];
  return {
    color: [STATS_PALETTE[2]],
    tooltip: {
      trigger: "axis",
      backgroundColor: t.tooltipBg,
      borderColor: t.tooltipBorder,
      textStyle: { color: t.text },
    },
    grid: { left: 8, right: 8, top: 28, bottom: 4, containLabel: true },
    xAxis: {
      type: "category",
      data: labels,
      boundaryGap: false,
      axisLine: { lineStyle: { color: t.axisLine } },
      axisLabel: { color: t.textMuted, fontSize: 11 },
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { color: t.splitLine } },
      axisLabel: { color: t.textWeak, fontSize: 11 },
    },
    series: [
      {
        name: "活跃",
        type: "line",
        smooth: true,
        areaStyle: { opacity: 0.18 },
        data: values,
        symbol: "circle",
        symbolSize: 8,
      },
    ],
  };
});

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get("/stats/online-users");
    payload.value = data?.data || null;
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : "加载失败");
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>
