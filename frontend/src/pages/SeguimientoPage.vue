<script setup>
import { SeguimientoPanel } from '@aprendomx/sinpapel-vue'
import { computed, onMounted, ref } from 'vue'

import { http } from '@/api/http'
import { useSolicitudesStore } from '@/stores/solicitudes'

const props = defineProps({
  // Llega de la ruta como string.
  id: { type: [String, Number], required: true },
})

const store = useSolicitudesStore()
const solicitud = ref(null)

// `resource` es el `effective_slug` del modelo decorado con
// @workflow_enabled: la librería no lo auto-descubre, lo pasa el consumidor.
const RECURSO = 'solicitudes-constancia'

const puedeEvaluarSla = computed(() => Boolean(solicitud.value?.puede_evaluar_sla))

onMounted(async () => {
  solicitud.value = await store.cargarUna(props.id)
})
</script>

<template>
  <q-page class="q-pa-lg">
    <q-banner
      v-if="store.error"
      dense
      class="bg-red-1 text-negative"
    >
      No se pudo abrir la solicitud: {{ store.error.detail || 'no disponible' }}
    </q-banner>

    <template v-else-if="solicitud">
      <div class="row items-center q-mb-md">
        <div>
          <div
            class="text-h5"
            data-test="folio"
          >
            {{ solicitud.folio }}
          </div>
          <div class="text-caption text-grey-7">
            {{ solicitud.dependencia_nombre }} · {{ solicitud.solicitante }}
          </div>
        </div>
        <q-space />
        <q-btn
          flat
          icon="arrow_back"
          label="Bandeja"
          :to="{ name: 'bandeja' }"
        />
      </div>

      <!--
        SeguimientoPanel compone el badge de estado y las pestañas de historial,
        requisitos, documentos, previsualización, metadatos y SLA, más el
        diálogo de transición con su firma polimórfica.

        `:key` es obligatorio: el panel crea su store a partir de las props
        iniciales, así que sin remontar se quedaría con el pk anterior al
        navegar entre solicitudes.
      -->
      <SeguimientoPanel
        :key="solicitud.id"
        :axios="http"
        base-path="/sinpapel/api"
        :resource="RECURSO"
        :pk="solicitud.id"
        :current-state="solicitud.estado.nombre"
        :can-evaluate-sla="puedeEvaluarSla"
        locale="es"
      />
    </template>

    <q-inner-loading :showing="store.cargando" />
  </q-page>
</template>
