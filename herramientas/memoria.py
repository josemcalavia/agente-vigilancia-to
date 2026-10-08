#!/usr/bin/env python3
"""
Memoria del boletin entre numeros.

`publicados.json` recuerda QUE articulos se han presentado. Esto recuerda QUE
SE PENSO de ellos: en que ambito cayeron y que temas tocaban. Sirve para lo que
un numero suelto no puede ver: que un asunto se repite, que un ambito se ha
secado o que una revista se esta convirtiendo en la fuente habitual.

Uso:  python3 herramientas/memoria.py   -> resumen legible para el agente

Agente de vigilancia de literatura en Terapia Ocupacional.
Diseno original: José María Calavia Balduz. Licencia CC BY-NC-SA 4.0.
"""
import os, sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import leer_json, escribir_json, rutas  # noqa: E402

VENTANA = 6          # cuantos numeros hacia atras se miran
MIN_RECURRENCIA = 2  # en cuantos numeros distintos tiene que salir un tema


def _ruta(carpeta_datos):
    return os.path.join(carpeta_datos, "memoria.json")


def cargar(carpeta_datos):
    return leer_json(_ruta(carpeta_datos), {"numeros": []}) or {"numeros": []}


def registrar(carpeta_datos, anio, numero, stamp, fichas):
    """Anota lo publicado. Idempotente: si el numero ya estaba, lo sustituye."""
    mem = cargar(carpeta_datos)
    entrada = {
        "anio": anio, "numero": numero, "fecha": stamp,
        "registrado": datetime.now().isoformat(timespec="seconds"),
        "articulos": [{
            "doi": f.get("doi"),
            "titulo": (f.get("title") or "").rstrip("."),
            "revista": f.get("journal"),
            "categoria": f.get("categoria"),
            "temas": [t.lower().strip() for t in (f.get("temas") or [])],
        } for f in fichas],
    }
    mem["numeros"] = [n for n in mem["numeros"] if not (n["anio"] == anio and n["numero"] == numero)]
    mem["numeros"].append(entrada)
    mem["numeros"].sort(key=lambda n: (n["anio"], n["numero"]))
    escribir_json(_ruta(carpeta_datos), mem)
    return mem


def recuento_por_categoria(carpeta_datos, excluir=None):
    """Articulos compartidos por ambito en los numeros ANTERIORES a `excluir`."""
    numeros = [n for n in cargar(carpeta_datos)["numeros"]
               if not excluir or (n["anio"], n["numero"]) < tuple(excluir)]
    return dict(Counter(a["categoria"] for n in numeros for a in n["articulos"])), len(numeros)


def temas_usados(carpeta_datos):
    return sorted({t for n in cargar(carpeta_datos)["numeros"]
                   for a in n["articulos"] for t in a["temas"]})


def resumen_legible(carpeta_datos):
    numeros = cargar(carpeta_datos)["numeros"][-VENTANA:]
    if not numeros:
        return ("Primer número: todavía no hay historial con el que comparar. "
                "Omite la sección de seguimiento.")
    por_numero = [set(t for a in n["articulos"] for t in a["temas"]) for n in numeros]
    cuenta = Counter(t for s in por_numero for t in s)
    recurrentes = [(t, c) for t, c in cuenta.most_common() if c >= MIN_RECURRENCIA][:8]
    revistas = [(r, c) for r, c in Counter(a["revista"] for n in numeros for a in n["articulos"]
                                           if a["revista"]).most_common(5) if c >= MIN_RECURRENCIA]
    lineas = [f"Mirando los {len(numeros)} números anteriores "
              f"(del {numeros[0]['numero']} al {numeros[-1]['numero']}):"]
    if recurrentes:
        lineas.append("  Temas que se repiten:")
        lineas += [f"    {t}: en {c} números" for t, c in recurrentes]
    else:
        lineas.append("  Ningún tema se repite todavía entre números.")
    if revistas:
        lineas.append("  Revistas habituales: " + ", ".join(f"{r} ({c})" for r, c in revistas))
    if len(numeros) >= 3:
        vistas = {a["categoria"] for n in numeros for a in n["articulos"]}
        recientes = {a["categoria"] for n in numeros[-2:] for a in n["articulos"]}
        if vistas - recientes:
            lineas.append("  Ámbitos sin nada en los dos últimos números: "
                          + ", ".join(sorted(vistas - recientes)))
    usados = temas_usados(carpeta_datos)
    if usados:
        lineas.append("  Etiquetas de temas ya usadas (reutilízalas): " + ", ".join(usados))
    return "\n".join(lineas)


if __name__ == "__main__":
    print(resumen_legible(rutas()["datos"]))
