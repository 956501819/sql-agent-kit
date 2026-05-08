<template>
  <div>
    <div class="section-title">🔧 Agent 参数</div>
    <div v-if="loading" class="card">加载中...</div>
    <div v-else class="card">
      <div class="param-row">
        <label class="label">最大重试次数 (max_retry)</label>
        <div class="slider-wrap">
          <input type="range" v-model.number="form.max_retry" min="1" max="10" step="1" />
          <span class="slider-val">{{ form.max_retry }}</span>
        </div>
      </div>
      <div class="param-row">
        <label class="label">置信度阈值 (confidence_threshold)</label>
        <div class="slider-wrap">
          <input type="range" v-model.number="form.confidence_threshold" min="0" max="1" step="0.05" />
          <span class="slider-val">{{ form.confidence_threshold.toFixed(2) }}</span>
        </div>
      </div>
      <div class="param-row">
        <label class="label">Prompt 最大表数 (max_tables_in_prompt)</label>
        <div class="slider-wrap">
          <input type="range" v-model.number="form.max_tables_in_prompt" min="1" max="30" step="1" />
          <span class="slider-val">{{ form.max_tables_in_prompt }}</span>
        </div>
      </div>
      <div class="param-row">
        <label class="label">查询超时秒数 (query_timeout)</label>
        <div class="slider-wrap">
          <input type="range" v-model.number="form.query_timeout" min="5" max="120" step="5" />
          <span class="slider-val">{{ form.query_timeout }}s</span>
        </div>
      </div>
      <div class="param-row">
        <label class="label">最大返回行数 (max_rows)</label>
        <div class="slider-wrap">
          <input type="range" v-model.number="form.max_rows" min="10" max="2000" step="10" />
          <span class="slider-val">{{ form.max_rows }}</span>
        </div>
      </div>

      <div class="btn-row">
        <button class="btn btn--primary" :disabled="saving" @click="save">
          {{ saving ? '保存中...' : '保存参数' }}
        </button>
        <span v-if="msg" :class="['alert', msgType]">{{ msg }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { paramsApi } from '../api/index.js'

const loading = ref(true)
const saving = ref(false)
const msg = ref('')
const msgType = ref('alert--success')

const form = ref({
  max_retry: 3,
  confidence_threshold: 0.6,
  max_tables_in_prompt: 10,
  query_timeout: 30,
  max_rows: 500,
})

onMounted(async () => {
  try {
    const { data } = await paramsApi.get()
    Object.assign(form.value, data)
  } finally {
    loading.value = false
  }
})

async function save() {
  saving.value = true
  msg.value = ''
  try {
    await paramsApi.save(form.value)
    msg.value = '参数已保存'
    msgType.value = 'alert--success'
  } catch (e) {
    msg.value = e.response?.data?.detail || e.message
    msgType.value = 'alert--error'
  } finally {
    saving.value = false
    setTimeout(() => msg.value = '', 3000)
  }
}
</script>

<style scoped>
.param-row { margin-bottom: 18px; }
.slider-wrap { display: flex; align-items: center; gap: 12px; margin-top: 6px; }
.slider-wrap input[type=range] { flex: 1; accent-color: #7c83fd; }
.slider-val { width: 50px; font-size: 13px; font-weight: 600; color: #7c83fd; text-align: right; }
.btn-row { display: flex; align-items: center; gap: 12px; margin-top: 8px; }
</style>
