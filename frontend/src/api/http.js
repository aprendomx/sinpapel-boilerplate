import axios from 'axios'

/**
 * Cliente HTTP compartido.
 *
 * `baseURL` vacío por defecto: en desarrollo el dev server proxea las rutas del
 * backend, así que las peticiones son del mismo origen y no hacen falta ni CORS
 * ni configuración de despliegue. Solo define `VITE_API_BASE` si sirves la API
 * desde otro origen, y entonces configura CORS en el backend.
 *
 * `withCredentials` es necesario porque el backend autentica por sesión de
 * Django: sin él la cookie no viaja y la API responde 403.
 */
export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
  withCredentials: true,
  // Django nombra la cookie `csrftoken` y espera la cabecera `X-CSRFToken`;
  // axios trae por defecto los nombres de otro framework (`XSRF-TOKEN` /
  // `X-XSRF-TOKEN`), así que sin esto NINGÚN POST funciona: el servidor
  // responde 403 "CSRF token missing" aunque la cookie esté presente.
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
})
