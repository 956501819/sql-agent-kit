<template>
  <div>
    <div class="section-title">💬 单Agent查询</div>

    <div class="card">
      <div class="query-row">
        <input
          v-model="question"
          class="input"
          placeholder="输入自然语言问题，例如：查询销售额最高的前5个产品"
          @keydown.enter="runQuery"
        />
        <button class="btn btn--primary" :disabled="loading || !question.trim()" @click="runQuery">
          {{ loading ? '查询中...' : '查询' }}
        </button>
      </div>
    </div>

    <div v-if="result" class="card">
      <div class="result-header">
        <span :class="['tag', statusTag]">{{ statusText }}</span>
        <span class="result-meta">置信度</span>
        <ConfidenceBar :value="result.confidence" style="width:120px" />
        <span class="result-meta">重试 {{ result.retry_count }} 次</span>
      </div>

      <div v-if="editableSql" style="margin-top:12px">
        <div class="label">生成的 SQL
          <span class="hint-text">（可直接编辑后重新执行）</span>
        </div>
        <SqlDisplay
          :sql="editableSql"
          :editable="true"
          :intent="question"
          :chart-hint="result?.chart_hint || {}"
          @update:sql="editableSql = $event"
          @result="onSqlResult"
        />
        <div style="margin-top:8px;display:flex;gap:8px;align-items:center">
          <button class="btn btn--ghost btn--sm" @click="editableSql = result.sql">还原</button>
          <span v-if="rerunError" class="error-hint">{{ rerunError }}</span>
        </div>
      </div>

      <div v-if="result.status === 'need_confirm'" class="alert alert--warn" style="margin-top:12px">
        置信度较低，请确认 SQL 后再执行。
      </div>

      <div v-if="result.error" class="alert alert--error" style="margin-top:12px">{{ result.error }}</div>

      <div v-if="displayData?.length" style="margin-top:16px">
        <div class="label">查询结果
          <span v-if="rerunResult" class="hint-text">（已更新为手动执行结果）</span>
        </div>
        <ResultTable :data="displayData" />
      </div>
    </div>

    <div v-if="error" class="alert alert--error">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, computed, shallowRef } from 'vue'
import { queryApi } from '../api/index.js'
import SqlDisplay from '../components/SqlDisplay.vue'
import ResultTable from '../components/ResultTable.vue'
import ConfidenceBar from '../components/ConfidenceBar.vue'

const question = ref('')
const loading = ref(false)
const result = ref(null)
const error = ref('')
const editableSql = ref('')
const rerunResult = shallowRef(null)
const rerunError = ref('')

const statusTag = ref('tag--info')
const statusText = ref('')

const displayData = computed(() => rerunResult.value?.data ?? result.value?.data ?? [])

async function runQuery() {
  if (!question.value.trim() || loading.value) return
  loading.value = true
  result.value = null
  rerunResult.value = null
  rerunError.value = ''
  error.value = ''

  try {
    const { data } = await queryApi.run(question.value.trim())
    result.value = data
    editableSql.value = data.sql || ''
    if (data.status === 'success') { statusTag.value = 'tag--success'; statusText.value = '查询成功' }
    else if (data.status === 'need_confirm') { statusTag.value = 'tag--warn'; statusText.value = '需要确认' }
    else { statusTag.value = 'tag--error'; statusText.value = '查询失败' }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
}

function onSqlResult(data) {
  if (!data.success) {
    rerunError.value = data.error || '执行失败'
    return
  }
  rerunError.value = ''
  rerunResult.value = data
}
</script>

<style scoped>
.query-row { display: flex; gap: 10px; }
.result-header { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.result-meta { font-size: 12px; color: #888; }
.hint-text { font-size: 12px; color: #aaa; font-weight: normal; margin-left: 6px; }
.error-hint { font-size: 12px; color: #e74c3c; }
</style>
