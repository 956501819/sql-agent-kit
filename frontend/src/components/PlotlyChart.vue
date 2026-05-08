<template>
  <div ref="chartEl" class="chart-container" />
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'

const props = defineProps({
  // Accepts a plotly figure object {data, layout} directly
  chartData: { type: Object, default: null },
})

const chartEl = ref(null)
let Plotly = null

async function loadPlotly() {
  if (!Plotly) {
    Plotly = (await import('plotly.js-dist-min')).default
  }
  return Plotly
}

async function renderChart(fig) {
  if (!fig) return
  // Wait for DOM to be ready
  await nextTick()
  if (!chartEl.value) return
  try {
    const lib = await loadPlotly()
    lib.react(chartEl.value, fig.data, {
      ...fig.layout,
      font: { family: 'Microsoft YaHei, Arial, sans-serif', size: 13 },
      margin: { l: 50, r: 30, t: 50, b: 50 },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
    })
  } catch (e) {
    console.error('Chart render error:', e)
  }
}

watch(() => props.chartData, (fig) => { if (fig) renderChart(fig) })
onMounted(() => { if (props.chartData) renderChart(props.chartData) })
onUnmounted(() => { if (chartEl.value && Plotly) Plotly.purge(chartEl.value) })
</script>

<style scoped>
.chart-container { width: 100%; min-height: 360px; }
</style>
