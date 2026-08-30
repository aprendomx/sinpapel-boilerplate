import { defineStore } from 'pinia'
import { ref } from 'vue'

import { crearSolicitud, listarSolicitudes, obtenerSolicitud } from '@/api/solicitudes'

/**
 * Estado de la bandeja de solicitudes.
 *
 * Cubre solo la API de dominio. El seguimiento de una instancia (transiciones,
 * historial, documentos) lo gestiona `useSeguimientoStore` de sinpapel-vue, que
 * mantiene su propio estado por `(resource, pk)`.
 */
export const useSolicitudesStore = defineStore('solicitudes', () => {
  const solicitudes = ref([])
  const total = ref(0)
  const pagina = ref(1)
  const cargando = ref(false)
  const error = ref(null)

  /** Normaliza el error de axios a algo pintable. */
  function registrarError(e) {
    error.value = e.response?.data ?? { detail: e.message }
  }

  async function cargar(page = 1) {
    cargando.value = true
    error.value = null
    try {
      const data = await listarSolicitudes({ page })
      // Si el proxy no cubre la ruta, el dev server responde el index.html con
      // un 200 y `data` no tiene forma de página. Fallar aquí es preferible a
      // pintar una bandeja vacía como si no hubiera nada que mostrar.
      if (!Array.isArray(data?.results)) {
        throw new Error('La API devolvió una respuesta inesperada para la bandeja.')
      }
      solicitudes.value = data.results
      total.value = data.count
      pagina.value = page
    } catch (e) {
      registrarError(e)
    } finally {
      cargando.value = false
    }
  }

  async function cargarUna(id) {
    cargando.value = true
    error.value = null
    try {
      return await obtenerSolicitud(id)
    } catch (e) {
      registrarError(e)
      return null
    } finally {
      cargando.value = false
    }
  }

  /** Devuelve la solicitud creada, o `null` si el backend la rechazó. */
  async function crear(payload) {
    cargando.value = true
    error.value = null
    try {
      return await crearSolicitud(payload)
    } catch (e) {
      registrarError(e)
      return null
    } finally {
      cargando.value = false
    }
  }

  return { solicitudes, total, pagina, cargando, error, cargar, cargarUna, crear }
})
