import { createRouter, createWebHistory } from 'vue-router'

import BandejaPage from '@/pages/BandejaPage.vue'
import NuevaSolicitudPage from '@/pages/NuevaSolicitudPage.vue'
import SeguimientoPage from '@/pages/SeguimientoPage.vue'

export const routes = [
  { path: '/', name: 'bandeja', component: BandejaPage },
  { path: '/solicitudes/nueva', name: 'nueva-solicitud', component: NuevaSolicitudPage },
  {
    path: '/solicitudes/:id',
    name: 'seguimiento',
    component: SeguimientoPage,
    // `props: true` pasa el :id como prop en vez de leerlo del route dentro
    // del componente, lo que lo hace montable en un test sin router.
    props: true,
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
