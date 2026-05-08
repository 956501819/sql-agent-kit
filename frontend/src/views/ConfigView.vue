<template>
  <div>
    <div class="section-title">⚙️ 配置管理</div>

    <div v-if="loading" class="card">加载中...</div>
    <template v-else>
      <!-- LLM Config -->
      <div class="card">
        <div class="label">LLM 提供商</div>
        <select v-model="form.provider" class="input" style="width:200px;margin-bottom:16px">
          <option value="openai">OpenAI / 兼容接口</option>
          <option value="siliconflow">SiliconFlow</option>
          <option value="qwen">通义千问 (DashScope)</option>
          <option value="bailian">阿里云百炼</option>
        </select>

        <!-- OpenAI -->
        <div v-show="form.provider === 'openai'" class="provider-fields">
          <div class="field-row">
            <label class="label">API Key</label>
            <input v-model="form.openai.api_key" class="input" type="password" placeholder="sk-..." />
          </div>
          <div class="field-row">
            <label class="label">Base URL</label>
            <input v-model="form.openai.base_url" class="input" placeholder="https://api.openai.com/v1" />
          </div>
          <div class="field-row">
            <label class="label">Model</label>
            <input v-model="form.openai.model" class="input" placeholder="gpt-4o" />
          </div>
        </div>

        <!-- SiliconFlow -->
        <div v-show="form.provider === 'siliconflow'" class="provider-fields">
          <div class="field-row">
            <label class="label">API Key</label>
            <input v-model="form.siliconflow.api_key" class="input" type="password" placeholder="sk-..." />
          </div>
          <div class="field-row">
            <label class="label">Model</label>
            <input v-model="form.siliconflow.model" class="input" placeholder="Qwen/Qwen2.5-72B-Instruct" />
          </div>
        </div>

        <!-- Qwen -->
        <div v-show="form.provider === 'qwen'" class="provider-fields">
          <div class="field-row">
            <label class="label">DashScope API Key</label>
            <input v-model="form.qwen.api_key" class="input" type="password" placeholder="sk-..." />
          </div>
          <div class="field-row">
            <label class="label">Model</label>
            <input v-model="form.qwen.model" class="input" placeholder="qwen-plus" />
          </div>
        </div>

        <!-- Bailian -->
        <div v-show="form.provider === 'bailian'" class="provider-fields">
          <div class="field-row">
            <label class="label">API Key</label>
            <input v-model="form.bailian.api_key" class="input" type="password" placeholder="sk-..." />
          </div>
          <div class="field-row">
            <label class="label">Model</label>
            <input v-model="form.bailian.model" class="input" placeholder="qwen-plus" />
          </div>
        </div>

        <div class="btn-row">
          <button class="btn btn--ghost" :disabled="testingLLM" @click="testLLM">
            {{ testingLLM ? '测试中...' : '测试连接' }}
          </button>
          <span v-if="llmTestResult" :class="['alert', llmTestResult.success ? 'alert--success' : 'alert--error']">
            {{ llmTestResult.message }}
          </span>
        </div>
      </div>

      <!-- DB Config -->
      <div class="card">
        <div class="label">数据库配置</div>
        <div class="field-row">
          <label class="label">类型</label>
          <select v-model="form.db.type" class="input" style="width:160px">
            <option value="mysql">MySQL</option>
            <option value="postgresql">PostgreSQL</option>
            <option value="sqlite">SQLite</option>
          </select>
        </div>

        <template v-if="form.db.type !== 'sqlite'">
          <div class="field-row">
            <label class="label">Host</label>
            <input v-model="form.db.host" class="input" placeholder="127.0.0.1" />
          </div>
          <div class="field-row">
            <label class="label">Port</label>
            <input v-model="form.db.port" class="input" placeholder="3306" style="width:100px" />
          </div>
          <div class="field-row">
            <label class="label">用户名</label>
            <input v-model="form.db.user" class="input" placeholder="root" />
          </div>
          <div class="field-row">
            <label class="label">密码</label>
            <input v-model="form.db.password" class="input" type="password" />
          </div>
          <div class="field-row">
            <label class="label">数据库名</label>
            <input v-model="form.db.name" class="input" />
          </div>
        </template>
        <template v-else>
          <div class="field-row">
            <label class="label">SQLite 路径</label>
            <input v-model="form.db.sqlite_path" class="input" placeholder="./data/local.db" />
          </div>
        </template>

        <div class="btn-row">
          <button class="btn btn--ghost" :disabled="testingDB" @click="testDB">
            {{ testingDB ? '测试中...' : '测试连接' }}
          </button>
          <span v-if="dbTestResult" :class="['alert', dbTestResult.success ? 'alert--success' : 'alert--error']">
            {{ dbTestResult.message }}
          </span>
        </div>
      </div>

      <div class="btn-row">
        <button class="btn btn--primary" :disabled="saving" @click="save">
          {{ saving ? '保存中...' : '保存配置' }}
        </button>
        <span v-if="saveMsg" class="alert alert--success">{{ saveMsg }}</span>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { configApi } from '../api/index.js'

const loading = ref(true)
const saving = ref(false)
const saveMsg = ref('')
const testingLLM = ref(false)
const testingDB = ref(false)
const llmTestResult = ref(null)
const dbTestResult = ref(null)

const form = ref({
  provider: 'siliconflow',
  openai: { api_key: '', base_url: '', model: 'gpt-4o' },
  qwen: { api_key: '', model: 'qwen-plus' },
  siliconflow: { api_key: '', model: 'Qwen/Qwen2.5-72B-Instruct' },
  bailian: { api_key: '', model: 'qwen-plus' },
  db: { type: 'mysql', host: '127.0.0.1', port: '3306', user: '', password: '', name: '', sqlite_path: '' },
})

onMounted(async () => {
  try {
    const { data } = await configApi.get()
    Object.assign(form.value, data)
  } finally {
    loading.value = false
  }
})

async function save() {
  saving.value = true
  saveMsg.value = ''
  try {
    await configApi.save(form.value)
    saveMsg.value = '配置已保存'
    setTimeout(() => saveMsg.value = '', 3000)
  } finally {
    saving.value = false
  }
}

async function testLLM() {
  testingLLM.value = true
  llmTestResult.value = null
  const p = form.value.provider
  const payload = { provider: p, ...form.value[p] }
  try {
    const { data } = await configApi.testLLM(payload)
    llmTestResult.value = data
  } finally {
    testingLLM.value = false
  }
}

async function testDB() {
  testingDB.value = true
  dbTestResult.value = null
  try {
    const { data } = await configApi.testDB(form.value.db)
    dbTestResult.value = data
  } finally {
    testingDB.value = false
  }
}
</script>

<style scoped>
.provider-fields { margin-bottom: 12px; }
.field-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.field-row .label { width: 110px; margin: 0; flex-shrink: 0; }
.btn-row { display: flex; align-items: center; gap: 12px; margin-top: 12px; }
</style>
