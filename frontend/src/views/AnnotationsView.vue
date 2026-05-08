<template>
  <div>
    <div class="section-title">🏷️ Schema 注释</div>

    <div class="card">
      <p class="hint">编辑字段业务含义，帮助 Agent 更准确地理解数据库结构。格式为 YAML。</p>

      <div class="btn-row" style="margin-bottom:12px">
        <button class="btn btn--ghost" :disabled="generating" @click="generate">
          {{ generating ? '生成中，请稍候...' : '🤖 自动生成注释' }}
        </button>
        <span class="hint" style="margin:0">连接数据库读取表结构和样本数据，由 AI 自动生成</span>
      </div>

      <!-- 预览区：AI 生成结果，确认后可覆盖到编辑器 -->
      <div v-if="preview" class="preview-block">
        <div class="preview-header">
          <span class="label" style="margin:0">AI 生成预览</span>
          <div class="preview-actions">
            <button class="btn btn--primary btn--sm" @click="applyPreview">覆盖到编辑器</button>
            <button class="btn btn--ghost btn--sm" @click="preview = ''">关闭</button>
          </div>
        </div>
        <pre class="preview-content">{{ preview }}</pre>
      </div>

      <div v-if="generateError" class="alert alert--error" style="margin-bottom:12px">{{ generateError }}</div>

      <textarea
        v-model="content"
        class="textarea"
        rows="20"
        placeholder="tables:&#10;  orders:&#10;    description: 订单表&#10;    columns:&#10;      status: 订单状态（pending=待付款, paid=已付款, cancelled=已取消）"
      />
      <div v-if="yamlError" class="alert alert--error" style="margin-top:8px">{{ yamlError }}</div>
      <div class="btn-row">
        <button class="btn btn--primary" :disabled="saving || !!yamlError" @click="save">
          {{ saving ? '保存中...' : '保存' }}
        </button>
        <span v-if="msg" :class="['alert', msgType]">{{ msg }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import yaml from 'js-yaml'
import { annotationsApi } from '../api/index.js'

const content = ref('')
const saving = ref(false)
const msg = ref('')
const msgType = ref('alert--success')
const yamlError = ref('')
const generating = ref(false)
const generateError = ref('')
const preview = ref('')

watch(content, (val) => {
  try { yaml.load(val); yamlError.value = '' }
  catch (e) { yamlError.value = e.message }
})

onMounted(async () => {
  const { data } = await annotationsApi.get()
  content.value = data.content || ''
})

async function generate() {
  generating.value = true
  generateError.value = ''
  preview.value = ''
  try {
    const { data } = await annotationsApi.generate()
    preview.value = data.content
  } catch (e) {
    generateError.value = e.response?.data?.detail || e.message
  } finally {
    generating.value = false
  }
}

function applyPreview() {
  content.value = preview.value
  preview.value = ''
}

async function save() {
  if (yamlError.value) return
  saving.value = true
  msg.value = ''
  try {
    await annotationsApi.save(content.value)
    msg.value = '注释已保存'
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
.hint { font-size: 13px; color: #888; margin-bottom: 10px; }
.btn-row { display: flex; align-items: center; gap: 12px; margin-top: 12px; }

.preview-block {
  border: 1px solid #7c83fd;
  border-radius: 8px;
  margin-bottom: 14px;
  overflow: hidden;
}
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f0f1ff;
  border-bottom: 1px solid #e0e1ff;
}
.preview-actions { display: flex; gap: 8px; }
.preview-content {
  margin: 0;
  padding: 14px;
  font-family: 'Menlo', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.7;
  max-height: 320px;
  overflow-y: auto;
  background: #fafafe;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
