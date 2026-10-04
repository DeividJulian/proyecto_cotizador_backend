"""Estimación de esfuerzo con el método de tres puntos (PERT)."""
from services.catalogo import (
    DISTRIBUCION_ESTANDAR,
    FACTORES_COMPLEJIDAD,
    MODULOS,
    RANGO_PERT,
    ROLES,
    TRANSVERSALES,
)


def pert(optimista: float, probable: float, pesimista: float) -> float:
    """Valor esperado PERT: (O + 4M + P) / 6."""
    return (optimista + 4 * probable + pesimista) / 6


def _horas(probable: float, complejidad: str) -> dict:
    factor_o, factor_p = RANGO_PERT[complejidad]
    optimista, pesimista = probable * factor_o, probable * factor_p
    return {
        "horas_optimista": round(optimista, 1),
        "horas_probable": round(probable, 1),
        "horas_pesimista": round(pesimista, 1),
        "horas_esperadas": round(pert(optimista, probable, pesimista), 1),
    }


def item_desde_modulo(modulo: dict) -> dict:
    """Convierte un módulo detectado por el análisis de alcance en una línea de cotización."""
    datos = MODULOS[modulo["clave"]]
    probable = datos["horas"] * FACTORES_COMPLEJIDAD[modulo["complejidad"]]
    return {
        "nombre": modulo["nombre"],
        "categoria": modulo["categoria"],
        "complejidad": modulo["complejidad"],
        "origen": "ia",
        "distribucion": dict(datos["distribucion"]),
        "motivos": modulo["motivos"],
        **_horas(probable, modulo["complejidad"]),
    }


def item_manual(nombre: str, categoria: str, complejidad: str, horas_probable: float, distribucion: dict | None) -> dict:
    return {
        "nombre": nombre,
        "categoria": categoria,
        "complejidad": complejidad,
        "origen": "manual",
        "distribucion": distribucion or dict(DISTRIBUCION_ESTANDAR),
        "motivos": "Added manually",
        **_horas(horas_probable, complejidad),
    }


def items_transversales(items_desarrollo: list[dict]) -> list[dict]:
    """QA, gestión y despliegue se calculan como porcentaje del trabajo de desarrollo."""
    resultado = []
    for t in TRANSVERSALES:
        suma = {k: sum(i[k] for i in items_desarrollo) for k in ("horas_optimista", "horas_probable", "horas_pesimista")}
        o, m, p = (max(t["minimo"] * f, suma[k] * t["porcentaje"]) for k, f in
                   (("horas_optimista", 0.8), ("horas_probable", 1.0), ("horas_pesimista", 1.5)))
        resultado.append(
            {
                "nombre": t["nombre"],
                "categoria": "Cross-cutting",
                "complejidad": "media",
                "origen": "ia",
                "distribucion": {t["rol"]: 1.0},
                "motivos": f"{round(t['porcentaje'] * 100)}% of development hours (minimum {t['minimo']} h)",
                "horas_optimista": round(o, 1),
                "horas_probable": round(m, 1),
                "horas_pesimista": round(p, 1),
                "horas_esperadas": round(pert(o, m, p), 1),
            }
        )
    return resultado


def construir_items(modulos: list[dict]) -> list[dict]:
    desarrollo = [item_desde_modulo(m) for m in modulos]
    return desarrollo + items_transversales(desarrollo)


def horas_por_rol(items: list) -> dict:
    """Suma las horas de todas las líneas repartidas por rol, en los tres escenarios y el esperado."""
    totales = {rol: {"optimista": 0.0, "probable": 0.0, "pesimista": 0.0, "esperadas": 0.0} for rol in ROLES}
    for item in items:
        get = item.get if isinstance(item, dict) else lambda k, i=item: getattr(i, k)
        for rol, fraccion in (get("distribucion") or {}).items():
            fila = totales.setdefault(rol, {"optimista": 0.0, "probable": 0.0, "pesimista": 0.0, "esperadas": 0.0})
            fila["optimista"] += get("horas_optimista") * fraccion
            fila["probable"] += get("horas_probable") * fraccion
            fila["pesimista"] += get("horas_pesimista") * fraccion
            fila["esperadas"] += get("horas_esperadas") * fraccion
    return {
        rol: {k: round(v, 1) for k, v in fila.items()} for rol, fila in totales.items() if fila["probable"] > 0
    }


def resumen_estimacion(items: list, confianza: str = "media") -> dict:
    por_rol = horas_por_rol(items)
    suma = lambda clave: round(sum(f[clave] for f in por_rol.values()), 1)  # noqa: E731
    return {
        "por_rol": por_rol,
        "horas_optimista": suma("optimista"),
        "horas_probable": suma("probable"),
        "horas_pesimista": suma("pesimista"),
        "horas_esperadas": suma("esperadas"),
        "confianza": confianza,
    }
