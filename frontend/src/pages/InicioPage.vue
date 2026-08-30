<script setup>
import { onMounted, ref } from 'vue'

import { consultarSalud } from '@/api/salud'

const estado = ref('consultando')

onMounted(async () => {
  estado.value = await consultarSalud()
})
</script>

<template>
  <q-page class="q-pa-lg">
    <div class="text-h5 q-mb-md">
      Sistema de trámites
    </div>
    <p>
      Esqueleto del template. Los trámites se añaden copiando la vertical slice
      canónica; consulta el README antes de empezar.
    </p>
    <q-banner
      dense
      class="bg-grey-2"
    >
      Estado del backend: <strong data-test="estado-backend">{{ estado }}</strong>
    </q-banner>
  </q-page>
</template>
