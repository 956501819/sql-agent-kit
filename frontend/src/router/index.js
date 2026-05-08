import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/',            redirect: '/query' },
  { path: '/query',       component: () => import('../views/QueryView.vue'),       meta: { label: '单Agent查询',    icon: '💬' } },
  { path: '/analysis',    component: () => import('../views/AnalysisView.vue'),    meta: { label: '多Agent分析',    icon: '🧠' } },
  { path: '/config',      component: () => import('../views/ConfigView.vue'),      meta: { label: '配置管理',       icon: '⚙️' } },
  { path: '/history',     component: () => import('../views/HistoryView.vue'),     meta: { label: '查询历史',       icon: '📋' } },
  { path: '/tables',      component: () => import('../views/TablesView.vue'),      meta: { label: '表白名单',       icon: '🗂️' } },
  { path: '/annotations', component: () => import('../views/AnnotationsView.vue'), meta: { label: 'Schema注释',    icon: '🏷️' } },
  { path: '/params',      component: () => import('../views/ParamsView.vue'),      meta: { label: 'Agent参数',     icon: '🔧' } },
  { path: '/fewshot',     component: () => import('../views/FewShotView.vue'),     meta: { label: 'Few-shot管理',  icon: '📚' } },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
