<template>
  <div class="sql-editor-wrap">
    <textarea
      v-if="editable"
      v-model="localSql"
      class="sql-textarea"
      spellcheck="false"
      rows="6"
    />
    <pre v-else class="sql-block"><code>{{ sql }}</code></pre>
    <div v-if="editable" class="sql-actions">
      <button class="btn btn--primary btn--sm" :disabled="running || !localSql.trim()" @click="runSql">
        {{ running ? '执行中...' : '▶ 执行' }}
      </button>
      <span v-if="execError" class="exec-error">{{ execError }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { runSqlApi } from '../api/index.js'

const props = defineProps({
  sql: String,
  editable: { type: Boolean, default: false },
  intent: { type: String, default: '' },
})

const emit = defineEmits(['result'])

const localSql = ref(props.sql || '')
const running = ref(false)
const execError = ref('')

watch(() => props.sql, (v) => { localSql.value = v || '' })

async function runSql() {
  if (!localSql.value.trim() || running.value) return
  running.value = true
  execError.value = ''
  try {
    const { data } = await runSqlApi.run(localSql.value.trim(), props.intent)
    if (!data.success) {
      execError.value = data.error || '执行失败'
    }
    emit('result', data)
  } catch (e) {
    execError.value = e.response?.data?.detail || e.message
  } finally {
    running.value = false
  }
}
</script>

<style scoped>
.sql-editor-wrap { display: flex; flex-direction: column; gap: 8px; }
.sql-block {
  background: #1e1e2e;
  color: #cdd6f4;
  padding: 14px 16px;
  border-radius: 8px;
  font-family: 'Menlo', 'Consolas', monospace;
  font-size: 13px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}
.sql-textarea {
  background: #1e1e2e;
  color: #cdd6f4;
  padding: 14px 16px;
  border-radius: 8px;
  font-family: 'Menlo', 'Consolas', monospace;
  font-size: 13px;
  width: 100%;
  box-sizing: border-box;
  resize: vertical;
  border: 1px solid #3a3a5c;
  outline: none;
  line-height: 1.6;
  white-space: pre;
  overflow-x: auto;
}
.sql-textarea:focus { border-color: #7c83fd; }
.sql-actions { display: flex; align-items: center; gap: 10px; }
.exec-error { color: #e74c3c; font-size: 12px; }
.btn--sm { padding: 5px 14px; font-size: 13px; }
</style>
