<template>
  <div>
    <div class="section-title">🗂️ 表白名单</div>
    <div class="card">
      <p class="hint">每行一个表名，只有白名单内的表才会被 Agent 使用。</p>
      <textarea
        v-model="tableText"
        class="textarea"
        rows="12"
        placeholder="users&#10;orders&#10;products"
      />
      <div class="btn-row">
        <button class="btn btn--primary" :disabled="saving" @click="save">
          {{ saving ? '保存中...' : '保存' }}
        </button>
        <span v-if="msg" :class="['alert', msgType]">{{ msg }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { tablesApi } from '../api/index.js'

const tableText = ref('')
const saving = ref(false)
const msg = ref('')
const msgType = ref('alert--success')

onMounted(async () => {
  const { data } = await tablesApi.get()
  tableText.value = (data.tables || []).join('\n')
})

async function save() {
  saving.value = true
  msg.value = ''
  try {
    const tables = tableText.value.split('\n').map(s => s.trim()).filter(Boolean)
    await tablesApi.save(tables)
    msg.value = '白名单已保存'
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
</style>
