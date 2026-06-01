import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue') },
  { path: '/devices/:id', name: 'DeviceDetail', component: () => import('../views/DeviceDetail.vue') },
  { path: '/workorders', name: 'WorkOrders', component: () => import('../views/WorkOrders.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
