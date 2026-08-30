import { http } from '@/api/http'

const BASE = '/api/tramite/solicitudes-constancia'

/**
 * Cliente de la API de dominio del trámite.
 *
 * Es distinta de la API de workflow que consume `sinpapel-vue`: aquí viven la
 * bandeja y el alta, que `sinpapel-drf` no genera. Los widgets de seguimiento
 * hablan con `/sinpapel/api/` por su cuenta.
 */
export async function listarSolicitudes({ page = 1 } = {}) {
  const { data } = await http.get(`${BASE}/`, { params: { page } })
  return data
}

export async function obtenerSolicitud(id) {
  const { data } = await http.get(`${BASE}/${id}/`)
  return data
}

export async function crearSolicitud({ dependencia, metadatos }) {
  const { data } = await http.post(`${BASE}/`, { dependencia, metadatos })
  return data
}

export async function listarDependencias() {
  const { data } = await http.get('/api/tramite/dependencias/')
  return data.results
}
