<template>
  <span v-if="clamped > 0" class="star-rating" role="img" :aria-label="`星级 ${clamped} 星`">
    <span v-for="i in 5" :key="i" class="star" :class="{ 'star--on': i <= clamped }">★</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  rating: number;
}>();

const clamped = computed(() => {
  const n = Math.round(Number(props.rating) || 0);
  return Math.min(5, Math.max(0, n));
});
</script>

<style scoped>
.star-rating {
  display: inline-flex;
  gap: 1px;
  line-height: 1;
  vertical-align: middle;
}

.star {
  font-size: 0.95rem;
  color: #e5e7eb;
  opacity: 0.45;
  transition: color 0.15s ease, opacity 0.15s ease;
}

.star--on {
  color: #f59e0b;
  opacity: 1;
  text-shadow:
    0 0 1px rgba(180, 83, 9, 0.35),
    0 1px 0 rgba(251, 191, 36, 0.4);
}
</style>
