<template>
  <div ref="logEl" class="process-log">
    <div v-if="!logs.length" class="log-empty">等待分析开始...</div>
    <div v-for="(line, i) in logs" :key="i" class="log-line" v-html="formatLine(line)" />
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({ logs: { type: Array, default: () => [] } })
const logEl = ref(null)

watch(() => props.logs.length, async () => {
  await nextTick()
  if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight
})

function formatLine(line) {
  // Colorize emoji-prefixed lines
  return line
    .replace(/✅/g, '<span class="ok">✅</span>')
    .replace(/❌/g, '<span class="err">❌</span>')
    .replace(/⚠️/g, '<span class="warn">⚠️</span>')
    .replace(/\n/g, '<br/>')
}
</script>

<style scoped>
.process-log {
  background: #1e1e2e;
  color: #cdd6f4;
  border-radius: 8px;
  padding: 14px 16px;
  font-family: 'Menlo', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.7;
  max-height: 320px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.log-empty { color: #6c7086; }
.log-line { margin-bottom: 2px; }
:deep(.ok)   { color: #a6e3a1; }
:deep(.err)  { color: #f38ba8; }
:deep(.warn) { color: #f9e2af; }
</style>
