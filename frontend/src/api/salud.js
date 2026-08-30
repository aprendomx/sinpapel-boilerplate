import { http } from '@/api/http'

/**
 * Consulta el health check del backend.
 *
 * Devuelve la etiqueta de estado para pintarla; no relanza, porque un backend
 * caído es información que la UI debe mostrar, no un fallo de la app.
 */
export async function consultarSalud() {
  try {
    const { data } = await http.get('/salud/')
    return data.estado
  } catch {
    return 'sin conexión'
  }
}
