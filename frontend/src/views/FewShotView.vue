<template>
  <div>
    <div class="section-title">📚 Few-shot 管理</div>

    <!-- Add form -->
    <div class="card">
      <div class="label">添加示例</div>
      <div class="field-row">
        <label class="label">问题</label>
        <input v-model="newQ" class="input" placeholder="例如：查询销售额最高的产品" />
      </div>
      <div class="field-row" style="align-items:flex-start">
        <label class="label" style="padding-top:8px">SQL</label>
        <textarea v-model="newSQL" class="textarea" rows="4" placeholder="SELECT ..." />
      </div>
      <button class="btn btn--primary" :disabled="!newQ.trim() || !newSQL.trim() || adding" @click="add">
        {{ adding ? '添加中...' : '添加示例' }}
      </button>
      <span v-if="addMsg" class="alert alert--success" style="margin-left:12px">{{ addMsg }}</span>
    </div>

    <!-- List -->
    <div v-if="loading" class="card">加载中...</div>
    <div v-else-if="!items.length" class="card empty">暂无示例</div>
    <div v-else>
      <div v-for="item in items" :key="item.id" class="card fewshot-card">
        <div class="fewshot-header">
          <span class="fewshot-q">{{ item.question }}</span>
          <button class="btn btn--ghost btn--sm" @click="remove(item.id)">删除</button>
        </div>
        <SqlDisplay :sql="item.sql" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fewshotApi } from '../api/index.js'
import SqlDisplay from '../components/SqlDisplay.vue'

const items = ref([])
const loading = ref(false)
const newQ = ref('')
const newSQL = ref('')
const adding = ref(false)
const addMsg = ref('')

async function load() {
  loading.value = true
  try {
    const { data } = await fewshotApi.list()
    items.value = data.items
  } finally {
    loading.value = false
  }
}

async function add() {
  adding.value = true
  addMsg.value = ''
  try {
    await fewshotApi.add(newQ.value.trim(), newSQL.value.trim())
    newQ.value = ''
    newSQL.value = ''
    addMsg.value = '已添加'
    setTimeout(() => addMsg.value = '', 2000)
    load()
  } finally {
    adding.value = false
  }
}

async function remove(index) {
  await fewshotApi.delete(index)
  load()
}

onMounted(load)
</script>

<style scoped>
.field-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.field-row .label { width: 50px; margin: 0; flex-shrink: 0; }
.empty { color: #aaa; text-align: center; }
.fewshot-card { padding: 14px 16px; }
.fewshot-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.fewshot-q { font-size: 14px; font-weight: 600; color: #1a1a2e; }
</style>
