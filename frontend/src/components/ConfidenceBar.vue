<template>
  <div class="conf-bar">
    <div class="conf-fill" :style="{ width: pct + '%', background: color }" />
    <span class="conf-label">{{ (value * 100).toFixed(0) }}%</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ value: { type: Number, default: 0 } })

const pct = computed(() => Math.min(100, Math.max(0, props.value * 100)))
const color = computed(() => {
  if (props.value >= 0.8) return '#52c41a'
  if (props.value >= 0.6) return '#fa8c16'
  return '#ff4d4f'
})
</script>

<style scoped>
.conf-bar {
  position: relative;
  height: 20px;
  background: #f0f0f0;
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  align-items: center;
}
.conf-fill {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  border-radius: 10px;
  transition: width .4s ease;
}
.conf-label {
  position: relative;
  z-index: 1;
  font-size: 11px;
  font-weight: 700;
  color: #333;
  padding-left: 8px;
}
</style>
