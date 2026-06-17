import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/',           name: 'Dashboard',  component: () => import('../views/Dashboard.vue') },
  { path: '/sources',    name: 'SourceData', component: () => import('../views/SourceData.vue') },
  { path: '/logs',       name: 'LogData',    component: () => import('../views/LogData.vue') },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
