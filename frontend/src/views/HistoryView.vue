<template>
  <div>
    <div class="section-title">📋 查询历史</div>

    <div class="card">
      <div class="toolbar">
        <input v-model="keyword" class="input" style="max-width:300px" placeholder="搜索问题或SQL..." @input="onSearch" />
        <button class="btn btn--danger" @click="clearAll">清空全部</button>
      </div>
    </div>

    <div v-if="loading" class="card">加载中...</div>
    <div v-else-if="!records.length" class="card empty">暂无历史记录</div>
    <template v-else>
      <div v-for="(rec, i) in records" :key="i" class="card record-card">
        <div class="record-header">
          <span :class="['tag', rec.success ? 'tag--success' : 'tag--error']">
            {{ rec.success ? '成功' : '失败' }}
          </span>
          <span v-if="rec.judge_scores" class="tag tag--info">多Agent</span>
          <span class="record-ts">{{ rec.ts }}</span>
          <span class="record-meta">置信度 {{ (rec.confidence * 100).toFixed(0) }}%</span>
          <span class="record-meta">{{ rec.rows_count }} 行</span>
          <button class="btn btn--ghost btn--sm" @click="deleteRecord(i)">删除</button>
        </div>

        <div class="record-question">{{ rec.question }}</div>
        <SqlDisplay v-if="rec.sql" :sql="rec.sql" />

        <!-- 多Agent：图表 -->
        <div v-if="rec.chart_json" style="margin-top:12px">
          <div class="label">图表</div>
          <PlotlyChart :chart-data="parseChart(rec.chart_json)" />
        </div>

        <!-- 多Agent：结论 -->
        <div v-if="rec.summary" class="summary-block">
          <div class="label">分析结论</div>
          <p class="summary-text">{{ rec.summary }}</p>
        </div>

        <!-- 评分 -->
        <div v-if="rec.judge_scores" class="judge-inline">
          <span v-for="(v, k) in rec.judge_scores" :key="k" class="judge-chip">
            {{ judgeLabel[k] }}: {{ v }}/10
          </span>
        </div>
      </div>

      <div class="pagination">
        <button class="btn btn--ghost" :disabled="page === 1" @click="changePage(page - 1)">上一页</button>
        <span>{{ page }} / {{ totalPages }}</span>
        <button class="btn btn--ghost" :disabled="page === totalPages" @click="changePage(page + 1)">下一页</button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { historyApi } from '../api/index.js'
import SqlDisplay from '../components/SqlDisplay.vue'
import PlotlyChart from '../components/PlotlyChart.vue'

const keyword = ref('')
const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const judgeLabel = { sql_correctness: 'SQL', chart_fitness: '图表', summary_quality: '结论' }

function parseChart(chartJson) {
  if (!chartJson) return null
  try {
    return typeof chartJson === 'string' ? JSON.parse(chartJson) : chartJson
  } catch { return null }
}

async function load() {
  loading.value = true
  try {
    const { data } = await historyApi.list({ keyword: keyword.value, page: page.value, page_size: pageSize })
    records.value = data.records
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  load()
}

function changePage(p) {
  page.value = p
  load()
}

async function deleteRecord(index) {
  await historyApi.deleteOne(index, keyword.value)
  load()
}

async function clearAll() {
  if (!confirm('确认清空所有历史记录？')) return
  await historyApi.clearAll()
  page.value = 1
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; align-items: center; }
.empty { color: #aaa; text-align: center; }
.record-card { padding: 14px 16px; }
.record-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; flex-wrap: wrap; }
.record-ts { font-size: 12px; color: #aaa; }
.record-meta { font-size: 12px; color: #888; }
.record-question { font-size: 14px; font-weight: 600; margin-bottom: 8px; color: #1a1a2e; }
.summary-block { margin-top: 12px; }
.summary-text { font-size: 13px; line-height: 1.8; color: #333; margin-top: 4px; }
.judge-inline { display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }
.judge-chip { font-size: 11px; background: #f0f1ff; color: #7c83fd; padding: 2px 8px; border-radius: 4px; }
.pagination { display: flex; align-items: center; gap: 12px; justify-content: center; margin-top: 8px; font-size: 13px; color: #555; }
</style>
