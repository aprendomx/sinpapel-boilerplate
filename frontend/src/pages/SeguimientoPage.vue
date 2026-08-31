<script setup>
import { SeguimientoPanel } from '@aprendomx/sinpapel-vue'
import { computed, onMounted, onUnmounted, ref } from 'vue'

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

let interceptor = null

async function recargar() {
  solicitud.value = await store.cargarUna(props.id)
}

onMounted(async () => {
  await recargar()

  // El panel no emite nada: la librería documenta que gestiona todo en su store
  // interno, y tras una transición él mismo recarga estados e historial. Pero
  // `current-state` es una prop NUESTRA, así que sin hacer nada el badge se
  // quedaría con el estado anterior hasta recargar la página.
  //
  // La transición se detecta en el cliente HTTP, que es el único punto por el
  // que pasa, y basta con releer la solicitud: al cambiar la prop, el badge se
  // actualiza. NO se remonta el panel — hacerlo destruye el diálogo abierto y
  // reinicia la pestaña activa, que es peor experiencia y además redundante.
  interceptor = http.interceptors.response.use(async (respuesta) => {
    const esTransicion =
      respuesta.config?.method === 'post' &&
      respuesta.config?.url?.includes(`/${RECURSO}/${props.id}/transition/`)
    if (esTransicion && respuesta.status < 300) {
      await recargar()
    }
    return respuesta
  })
})

onUnmounted(() => {
  if (interceptor !== null) {
    http.interceptors.response.eject(interceptor)
  }
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

        El `:key` es obligatorio: el panel crea su store a partir de las props
        iniciales, así que sin remontar arrastraría el pk anterior al navegar
        entre solicitudes.
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
