<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { useSolicitudesStore } from '@/stores/solicitudes'

const store = useSolicitudesStore()
const router = useRouter()

const columnas = [
  { name: 'folio', label: 'Folio', field: 'folio', align: 'left', sortable: true },
  { name: 'estado', label: 'Estado', field: (f) => f.estado.nombre, align: 'left' },
  { name: 'tipo', label: 'Tipo', field: (f) => f.metadatos.tipo_constancia, align: 'left' },
  { name: 'solicitante', label: 'Solicitante', field: 'solicitante', align: 'left' },
  { name: 'dependencia', label: 'Dependencia', field: 'dependencia_nombre', align: 'left' },
  { name: 'creado', label: 'Presentada', field: 'creado', align: 'left' },
]

onMounted(() => store.cargar())

function abrir(solicitud) {
  router.push({ name: 'seguimiento', params: { id: solicitud.id } })
}

function fecha(iso) {
  return new Date(iso).toLocaleDateString('es-MX')
}
</script>

<template>
  <q-page class="q-pa-lg">
    <div class="row items-center q-mb-md">
      <div class="text-h5">
        Bandeja de solicitudes
      </div>
      <q-space />
      <q-btn
        color="primary"
        icon="add"
        label="Nueva solicitud"
        :to="{ name: 'nueva-solicitud' }"
      />
    </div>

    <q-banner
      v-if="store.error"
      dense
      class="bg-red-1 text-negative q-mb-md"
    >
      No se pudo cargar la bandeja: {{ store.error.detail || 'error desconocido' }}
    </q-banner>

    <q-table
      :rows="store.solicitudes"
      :columns="columnas"
      row-key="id"
      :loading="store.cargando"
      :rows-per-page-options="[0]"
      hide-pagination
      data-test="tabla-solicitudes"
      @row-click="(_evt, fila) => abrir(fila)"
    >
      <template #body-cell-estado="props">
        <q-td :props="props">
          <q-chip
            dense
            :style="{ backgroundColor: props.row.estado.color, color: '#1d1d1d' }"
            :icon="props.row.estado.icono"
            :label="props.row.estado.nombre.replace('_', ' ')"
          />
          <q-icon
            v-if="props.row.alerta_sla"
            name="schedule"
            color="negative"
            size="xs"
            class="q-ml-xs"
          >
            <q-tooltip>Excedió el plazo de atención</q-tooltip>
          </q-icon>
        </q-td>
      </template>

      <template #body-cell-creado="props">
        <q-td :props="props">
          {{ fecha(props.row.creado) }}
        </q-td>
      </template>

      <template #no-data>
        <div class="full-width text-center q-pa-md text-grey-7">
          Todavía no hay solicitudes visibles para tu cuenta.
        </div>
      </template>
    </q-table>

    <div
      v-if="store.total > store.solicitudes.length"
      class="q-mt-md text-caption text-grey-7"
    >
      Mostrando {{ store.solicitudes.length }} de {{ store.total }}.
    </div>
  </q-page>
</template>
