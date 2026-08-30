<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { listarDependencias } from '@/api/solicitudes'
import { useSolicitudesStore } from '@/stores/solicitudes'

const store = useSolicitudesStore()
const router = useRouter()

// Los mismos valores que `SCHEMA_METADATOS` declara en `choices`. Si cambian
// allá, cambian aquí: el backend rechaza cualquier otro con un 400.
const TIPOS = [
  { value: 'ESTUDIOS', label: 'De estudios' },
  { value: 'RESIDENCIA', label: 'De residencia' },
  { value: 'INGRESOS', label: 'De ingresos' },
]

const dependencias = ref([])
const dependencia = ref(null)
const curp = ref('')
const tipoConstancia = ref('ESTUDIOS')

onMounted(async () => {
  dependencias.value = await listarDependencias()
})

/** Errores por campo que devolvió el backend, para pintarlos junto al input. */
function errorDe(campo) {
  const detalle = store.error?.[campo]
  return Array.isArray(detalle) ? detalle.join(' ') : detalle
}

async function enviar() {
  const creada = await store.crear({
    dependencia: dependencia.value,
    metadatos: { curp: curp.value.toUpperCase(), tipo_constancia: tipoConstancia.value },
  })
  if (creada) {
    router.push({ name: 'seguimiento', params: { id: creada.id } })
  }
}
</script>

<template>
  <q-page class="q-pa-lg">
    <div class="text-h5 q-mb-md">
      Nueva solicitud de constancia
    </div>

    <q-form
      class="column q-gutter-md"
      style="max-width: 480px"
      @submit.prevent="enviar"
    >
      <q-select
        v-model="dependencia"
        :options="dependencias"
        option-value="id"
        option-label="nombre"
        emit-value
        map-options
        label="Dependencia que atiende"
        data-test="campo-dependencia"
        :error="!!errorDe('dependencia')"
        :error-message="errorDe('dependencia')"
      />

      <q-select
        v-model="tipoConstancia"
        :options="TIPOS"
        emit-value
        map-options
        label="Tipo de constancia"
        data-test="campo-tipo"
        :error="!!errorDe('tipo_constancia')"
        :error-message="errorDe('tipo_constancia')"
      />

      <q-input
        v-model="curp"
        label="CURP"
        hint="18 caracteres, como aparece en el documento oficial."
        maxlength="18"
        data-test="campo-curp"
        :error="!!errorDe('curp')"
        :error-message="errorDe('curp')"
      />

      <q-banner
        v-if="errorDe('detail')"
        dense
        class="bg-red-1 text-negative"
      >
        {{ errorDe('detail') }}
      </q-banner>

      <div class="row q-gutter-sm">
        <q-btn
          type="submit"
          color="primary"
          label="Presentar"
          :loading="store.cargando"
          data-test="enviar"
        />
        <q-btn
          flat
          label="Cancelar"
          :to="{ name: 'bandeja' }"
        />
      </div>
    </q-form>

    <q-banner
      dense
      class="bg-grey-2 q-mt-lg"
      style="max-width: 480px"
    >
      La solicitud queda en <strong>BORRADOR</strong>. Adjunta la identificación
      y el comprobante de domicilio desde la pantalla de seguimiento antes de
      presentarla en ventanilla.
    </q-banner>
  </q-page>
</template>
