<script setup>
import { onMounted, ref } from 'vue'
import { RouterView } from 'vue-router'

import { consultarSalud } from '@/api/salud'

const estadoBackend = ref('consultando')

onMounted(async () => {
  estadoBackend.value = await consultarSalud()
})
</script>

<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated>
      <q-toolbar>
        <q-toolbar-title>Sistema de trámites</q-toolbar-title>
        <q-chip
          dense
          text-color="white"
          :color="estadoBackend === 'ok' ? 'positive' : 'negative'"
          :label="estadoBackend"
          data-test="estado-backend"
        >
          <q-tooltip>Estado del backend</q-tooltip>
        </q-chip>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <RouterView />
    </q-page-container>
  </q-layout>
</template>
