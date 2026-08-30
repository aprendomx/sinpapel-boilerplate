import { createRouter, createWebHistory } from 'vue-router'

import InicioPage from '@/pages/InicioPage.vue'

export const routes = [{ path: '/', name: 'inicio', component: InicioPage }]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
