"""Forma canónica de un flujo en JSON v0.2.

Comparar dos exportaciones byte a byte no sirve: `exported_at` cambia en cada
llamada y el orden de listas no es semántico — un flujo no cambia porque sus
requisitos vengan en otro orden. Canonizar deja fuera lo volátil y ordena lo
que es un conjunto, de modo que una diferencia real signifique de verdad un
cambio en el flujo.

Lo usan los gates `parity` y `roundtrip`, y también el guardado del designer
para no reescribir un archivo que no cambió.
"""

# Se recalcula en cada exportación: incluirlo haría que dos exportaciones del
# mismo flujo nunca coincidieran.
CLAVES_VOLATILES = frozenset({"exported_at"})


def _clave_transicion(t: dict) -> tuple:
    return (t.get("estado_origen", ""), t.get("estado_destino", ""))


def _clave_requisito(r: dict) -> tuple:
    return (r.get("estado", ""), r.get("tipo_documento", ""))


def _clave_condicion(c: dict) -> tuple:
    return (c.get("orden", 0), c.get("tipo", ""))


def _clave_sla(s: dict) -> tuple:
    return (s.get("accion_vencimiento", ""), s.get("dias_maximos", 0))


def _por_nombre(item: dict) -> str:
    # Los grupos usan `name` (convención de auth.Group); el resto, `nombre`.
    return item.get("nombre") or item.get("name") or ""


def canonizar(datos: dict) -> dict:
    """Devuelve el flujo en forma comparable.

    No muta la entrada.
    """
    resultado = {k: v for k, v in datos.items() if k not in CLAVES_VOLATILES}

    catalogos = resultado.get("catalogos")
    if isinstance(catalogos, dict):
        catalogos_ordenados = {}
        for seccion, items in sorted(catalogos.items()):
            if isinstance(items, list):
                items = [_canonizar_estado(i) for i in items]
                catalogos_ordenados[seccion] = sorted(items, key=_por_nombre)
            else:
                catalogos_ordenados[seccion] = items
        resultado["catalogos"] = catalogos_ordenados

    flujo = resultado.get("flujo")
    if isinstance(flujo, dict):
        flujo = dict(flujo)
        transiciones = [_canonizar_transicion(t) for t in flujo.get("transiciones", [])]
        flujo["transiciones"] = sorted(transiciones, key=_clave_transicion)
        flujo["requisitos"] = sorted(flujo.get("requisitos", []), key=_clave_requisito)
        resultado["flujo"] = flujo

    return resultado


def _canonizar_estado(estado: dict) -> dict:
    """Ordena los SLA de un estado, si trae."""
    if not isinstance(estado, dict) or "slas" not in estado:
        return estado
    copia = dict(estado)
    copia["slas"] = sorted(copia.get("slas") or [], key=_clave_sla)
    return copia


def _canonizar_transicion(transicion: dict) -> dict:
    copia = dict(transicion)
    copia["grupos_permitidos"] = sorted(copia.get("grupos_permitidos") or [])
    if "condiciones" in copia:
        copia["condiciones"] = sorted(copia.get("condiciones") or [], key=_clave_condicion)
    return copia


def diferencias(esperado: object, obtenido: object, ruta: str = "") -> list[str]:
    """Enumera en qué difieren dos flujos ya canonizados.

    Un `assert a == b` sobre dos JSON anidados produce un diff ilegible. Esto
    devuelve rutas concretas ("flujo.transiciones[0].requiere_firma"), que es
    lo que un gate necesita reportar para que el fallo sea accionable.
    """
    if type(esperado) is not type(obtenido):
        return [
            f"{ruta or '<raíz>'}: tipos distintos "
            f"({type(esperado).__name__} vs {type(obtenido).__name__})"
        ]

    if isinstance(esperado, dict):
        problemas = []
        for clave in sorted(set(esperado) | set(obtenido)):
            sub = f"{ruta}.{clave}" if ruta else clave
            if clave not in esperado:
                problemas.append(f"{sub}: sobra (valor {obtenido[clave]!r})")
            elif clave not in obtenido:
                problemas.append(f"{sub}: falta (esperaba {esperado[clave]!r})")
            else:
                problemas.extend(diferencias(esperado[clave], obtenido[clave], sub))
        return problemas

    if isinstance(esperado, list):
        if len(esperado) != len(obtenido):
            return [f"{ruta}: {len(esperado)} elementos esperados, {len(obtenido)} obtenidos"]
        problemas = []
        for i, (a, b) in enumerate(zip(esperado, obtenido, strict=True)):
            problemas.extend(diferencias(a, b, f"{ruta}[{i}]"))
        return problemas

    if esperado != obtenido:
        return [f"{ruta}: esperaba {esperado!r}, obtuvo {obtenido!r}"]
    return []


def describir(problemas: list[str], limite: int = 20) -> str:
    """Mensaje de fallo legible para un gate."""
    if not problemas:
        return ""
    mostrados = problemas[:limite]
    texto = "\n".join(f"  - {p}" for p in mostrados)
    if len(problemas) > limite:
        texto += f"\n  … y {len(problemas) - limite} diferencia(s) más"
    return texto
