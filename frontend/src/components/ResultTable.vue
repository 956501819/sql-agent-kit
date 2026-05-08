<template>
  <div v-if="data && data.length" class="table-wrap">
    <div class="table-meta">共 {{ data.length }} 行 × {{ columns.length }} 列</div>
    <div class="table-scroll">
      <table class="result-table">
        <thead>
          <tr>
            <th v-for="col in columns" :key="col">{{ col }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in pagedData" :key="i">
            <td v-for="col in columns" :key="col">{{ row[col] ?? '' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="totalPages > 1" class="pagination">
      <button class="btn btn--ghost" :disabled="page === 1" @click="page--">上一页</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button class="btn btn--ghost" :disabled="page === totalPages" @click="page++">下一页</button>
    </div>
  </div>
  <div v-else class="empty">暂无数据</div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
  pageSize: { type: Number, default: 20 },
})

const page = ref(1)

watch(() => props.data, () => { page.value = 1 })

const columns = computed(() => {
  if (!props.data?.length) return []
  return Object.keys(props.data[0])
})

const totalPages = computed(() => Math.ceil(props.data.length / props.pageSize))

const pagedData = computed(() => {
  const start = (page.value - 1) * props.pageSize
  return props.data.slice(start, start + props.pageSize)
})
</script>

<style scoped>
.table-wrap { overflow: hidden; }
.table-meta { font-size: 12px; color: #888; margin-bottom: 8px; }
.table-scroll { overflow-x: auto; }

.result-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.result-table th {
  background: #f0f1ff;
  color: #1a1a2e;
  font-weight: 600;
  padding: 8px 12px;
  text-align: left;
  border-bottom: 2px solid #e0e0f0;
  white-space: nowrap;
}
.result-table td {
  padding: 7px 12px;
  border-bottom: 1px solid #f0f0f0;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.result-table tr:hover td { background: #fafafe; }

.pagination {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: center;
  margin-top: 12px;
  font-size: 13px;
  color: #555;
}

.empty { color: #aaa; font-size: 13px; padding: 16px 0; text-align: center; }
</style>
