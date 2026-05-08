<template>
  <div v-if="scores && Object.keys(scores).length" class="scores">
    <div class="score-item" v-for="(val, key) in scoreMap" :key="key">
      <span class="score-label">{{ val.label }}</span>
      <div class="score-bar-wrap">
        <div class="score-bar" :style="{ width: (scores[key] || 0) * 10 + '%', background: val.color }" />
      </div>
      <span class="score-num" :style="{ color: val.color }">{{ scores[key] ?? '-' }}/10</span>
    </div>
  </div>
</template>

<script setup>
defineProps({ scores: Object })

const scoreMap = {
  sql_correctness: { label: 'SQL 准确性', color: '#7c83fd' },
  chart_fitness:   { label: '图表适配',   color: '#52c41a' },
  summary_quality: { label: '结论质量',   color: '#fa8c16' },
}
</script>

<style scoped>
.scores { display: flex; flex-direction: column; gap: 10px; }
.score-item { display: flex; align-items: center; gap: 10px; }
.score-label { width: 80px; font-size: 12px; color: #555; flex-shrink: 0; }
.score-bar-wrap {
  flex: 1;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}
.score-bar { height: 100%; border-radius: 4px; transition: width .4s ease; }
.score-num { width: 40px; font-size: 12px; font-weight: 700; text-align: right; flex-shrink: 0; }
</style>
