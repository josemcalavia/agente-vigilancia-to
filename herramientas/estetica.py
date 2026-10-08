#!/usr/bin/env python3
"""
Estetica del boletin: plantillas de partida y construccion del CSS final.

Cada persona elige una plantilla y, si quiere, cambia colores, tipografias y
logo en perfil.json -> "estetica". Las tipografias por defecto son del sistema
(no se reparte ningun archivo de fuente); si alguien quiere una propia, deja el
.ttf/.otf en la carpeta estilo/ y lo indica en el perfil.

Uso:  python3 herramientas/estetica.py   -> lista las plantillas disponibles

Agente de vigilancia de literatura en Terapia Ocupacional.
Diseno original: José María Calavia Balduz. Licencia CC BY-NC-SA 4.0.
"""
import base64, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import HERE, RAIZ  # noqa: E402

SANS = "'Helvetica Neue', Helvetica, 'Segoe UI', Arial, sans-serif"
SERIF = "Georgia, 'Times New Roman', serif"
HUMANISTA = "'Avenir Next', Avenir, 'Segoe UI', 'Trebuchet MS', sans-serif"

PLANTILLAS = {
    "azul": {
        "descripcion": "Azul marino con acento naranja, sin serifa. Limpia y sanitaria.",
        "colores": {"primario": "#1F4E79", "secundario": "#4F6D8A", "suave": "#C5D5E6",
                    "acento": "#E07A2E", "fondo": "#F3F6FA", "texto": "#1C2430"},
        "fuente_titulos": SANS, "fuente_texto": SANS,
    },
    "clasica": {
        "descripcion": "Tinta berenjena y dorado, con serifa. Aire de revista académica.",
        "colores": {"primario": "#3B2F5C", "secundario": "#655A80", "suave": "#D5D0E0",
                    "acento": "#B8862B", "fondo": "#F7F5EF", "texto": "#23202B"},
        "fuente_titulos": SERIF, "fuente_texto": SERIF,
    },
    "calida": {
        "descripcion": "Terracota y mostaza, tipografía humanista. Cercana, para divulgar.",
        "colores": {"primario": "#8C3B2A", "secundario": "#9A6152", "suave": "#E8D2C7",
                    "acento": "#D39B2A", "fondo": "#FBF6F1", "texto": "#2A1E1A"},
        "fuente_titulos": HUMANISTA, "fuente_texto": HUMANISTA,
    },
    "sobria": {
        "descripcion": "Grises con un solo acento azul. Discreta, imprime bien en blanco y negro.",
        "colores": {"primario": "#222222", "secundario": "#5C5C5C", "suave": "#D2D2D2",
                    "acento": "#0A72B8", "fondo": "#F4F4F4", "texto": "#1A1A1A"},
        "fuente_titulos": SANS, "fuente_texto": SERIF,
    },
}


def _hex(c):
    c = c.lstrip("#")
    if len(c) == 3:
        c = "".join(x * 2 for x in c)
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def mezcla(color, blanco):
    """Aclara un color mezclandolo con blanco en la proporcion `blanco` (0-1)."""
    r, g, b = _hex(color)
    return "#%02X%02X%02X" % tuple(round(x + (255 - x) * blanco) for x in (r, g, b))


def _fuente_propia(nombre, archivo):
    ruta = archivo if os.path.isabs(archivo) else os.path.join(RAIZ, archivo)
    if not os.path.exists(ruta):
        print(f"AVISO: no encuentro la tipografía {archivo}; uso la de la plantilla.")
        return None
    otf = ruta.lower().endswith(".otf")
    with open(ruta, "rb") as f:
        datos = base64.b64encode(f.read()).decode()
    return (f"@font-face{{font-family:'{nombre}';src:url(data:font/{'otf' if otf else 'ttf'};"
            f"base64,{datos}) format('{'opentype' if otf else 'truetype'}');font-weight:100 900}}")


def resolver(perfil):
    """Devuelve la estetica completa: plantilla + lo que el perfil sobrescriba."""
    est = (perfil or {}).get("estetica") or {}
    base = PLANTILLAS.get(est.get("plantilla") or "azul", PLANTILLAS["azul"])
    colores = dict(base["colores"])
    colores.update({k: v for k, v in (est.get("colores") or {}).items() if v})
    return {
        "colores": colores,
        "fuente_titulos": est.get("fuente_titulos") or base["fuente_titulos"],
        "fuente_texto": est.get("fuente_texto") or base["fuente_texto"],
        "archivo_titulos": est.get("archivo_fuente_titulos"),
        "archivo_texto": est.get("archivo_fuente_texto"),
        "banda_portada": est.get("banda_portada", True),
    }


def css(perfil):
    e = resolver(perfil)
    c = e["colores"]
    fuentes, f_tit, f_txt = [], e["fuente_titulos"], e["fuente_texto"]
    if e["archivo_titulos"]:
        ff = _fuente_propia("TitulosPropia", e["archivo_titulos"])
        if ff:
            fuentes.append(ff)
            f_tit = f"'TitulosPropia', {f_tit}"
    if e["archivo_texto"]:
        ff = _fuente_propia("TextoPropia", e["archivo_texto"])
        if ff:
            fuentes.append(ff)
            f_txt = f"'TextoPropia', {f_txt}"
    variables = {
        "--primario": c["primario"], "--secundario": c["secundario"], "--suave": c["suave"],
        "--acento": c["acento"], "--fondo": c["fondo"], "--texto": c["texto"],
        "--tinte": mezcla(c["suave"], 0.55), "--tinte-acento": mezcla(c["acento"], 0.85),
        "--linea": mezcla(c["suave"], 0.6), "--f-tit": f_tit, "--f-txt": f_txt,
    }
    with open(os.path.join(HERE, "estilo.css"), encoding="utf-8") as f:
        plantilla = f.read()
    return (plantilla.replace("__FUENTES__", "\n".join(fuentes))
            .replace("__VARIABLES__", ";".join(f"{k}:{v}" for k, v in variables.items())))


if __name__ == "__main__":
    for nombre, p in PLANTILLAS.items():
        print(f"{nombre:9} {p['descripcion']}")
        print(f"          colores: " + ", ".join(f"{k} {v}" for k, v in p["colores"].items()))
