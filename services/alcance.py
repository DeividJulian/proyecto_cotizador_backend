"""Análisis del alcance: detecta módulos, complejidad y confianza a partir de la descripción del proyecto."""
import re

from services.catalogo import MODULOS, SENALES_ALTA, SENALES_BAJA
from services.nlp import normalizar


def _patron(palabra: str) -> re.Pattern:
    return re.compile(r"(?<![a-z0-9])" + re.escape(normalizar(palabra)) + r"(?![a-z0-9])")


_PATRONES = {clave: [(p, _patron(p)) for p in datos["palabras"]] for clave, datos in MODULOS.items()}


def _frases(texto: str) -> list[str]:
    return [f.strip() for f in re.split(r"[.;\n!?]+", normalizar(texto)) if f.strip()]


def _senales(texto_normal: str, lista: list[str]) -> list[str]:
    return sorted({s for s in lista if s in texto_normal})


def analizar_alcance(texto: str) -> dict:
    normal = normalizar(texto)
    frases = _frases(texto)
    global_alta = _senales(normal, SENALES_ALTA)
    global_baja = _senales(normal, SENALES_BAJA)

    modulos = []
    for clave, patrones in _PATRONES.items():
        detectadas = [palabra for palabra, patron in patrones if patron.search(normal)]
        if not detectadas:
            continue

        frases_del_modulo = [f for f in frases if any(p.search(f) for _, p in patrones)]
        motivos = []
        if any(_senales(f, SENALES_ALTA) for f in frases_del_modulo):
            complejidad = "alta"
            motivos.append("the description calls it complex or large-scale")
        elif any(_senales(f, SENALES_BAJA) for f in frases_del_modulo):
            complejidad = "baja"
            motivos.append("the description calls it simple or basic")
        elif len(frases_del_modulo) >= 3:
            complejidad = "alta"
            motivos.append("it is mentioned in several parts of the scope")
        elif len(global_alta) >= 2:
            complejidad = "alta"
            motivos.append("the project as a whole is described as complex")
        elif global_baja:
            complejidad = "baja"
            motivos.append("the project as a whole is described as simple or a prototype")
        else:
            complejidad = "media"
            motivos.append("no signs of special complexity")

        modulos.append(
            {
                "clave": clave,
                "nombre": MODULOS[clave]["nombre"],
                "categoria": MODULOS[clave]["categoria"],
                "complejidad": complejidad,
                "palabras_detectadas": detectadas,
                "motivos": "; ".join(motivos),
            }
        )

    n = len(modulos)
    largo = len(texto.strip())
    advertencias = []
    if largo < 120:
        advertencias.append("The scope is very short: describe more features for a reliable estimate.")
    if n == 0:
        advertencias.append("No known module was detected (login, payments, reports, mobile app, etc.).")

    if n >= 4 and largo >= 300:
        confianza = "alta"
    elif n >= 2 and largo >= 120:
        confianza = "media"
    else:
        confianza = "baja"

    return {
        "modulos": modulos,
        "senales_complejidad_alta": global_alta,
        "senales_complejidad_baja": global_baja,
        "confianza": confianza,
        "advertencias": advertencias,
    }
