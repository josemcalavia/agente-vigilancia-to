"""
Piezas compartidas por buscar.py, generar.py y memoria.py: rutas, lectura y
validacion del perfil, y la autoria del agente.

Agente de vigilancia de literatura en Terapia Ocupacional.
Diseno original: José María Calavia Balduz. Licencia CC BY-NC-SA 4.0.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(HERE)

# La autoria del agente. Es una condicion de la licencia (CC BY-NC-SA 4.0,
# clausula de reconocimiento) y aparece en portada, pagina de creditos y
# metadatos de cada boletin. No se configura desde el perfil: los datos de
# quien edita el boletin van aparte, en perfil["editor"], y no la sustituyen.
AUTORIA = "José María Calavia Balduz"
LICENCIA = "CC BY-NC-SA 4.0"
LICENCIA_URL = "https://creativecommons.org/licenses/by-nc-sa/4.0/deed.es"

# Terapia Ocupacional es el ancla obligatoria de todas las busquedas: el agente
# es de TO. Lo que elige cada persona son los ambitos con los que se cruza.
ANCLAS_TO = {
    "en": ["occupational therapy", "occupational therapist", "occupational therapists"],
    "es": ["terapia ocupacional", "terapeuta ocupacional", "terapeutas ocupacionales"],
    "pt": ["terapia ocupacional", "terapeuta ocupacional", "terapeutas ocupacionais"],
}

RUTA_PERFIL = os.path.join(RAIZ, "perfil.json")


def rutas(perfil=None):
    """Carpetas de trabajo. Por defecto todo vive dentro del paquete; el perfil
    puede mandar los boletines a otra carpeta."""
    datos = os.path.join(RAIZ, "datos")
    salida = (perfil or {}).get("carpeta_boletines") or os.path.join(RAIZ, "boletines")
    r = {
        "datos": datos,
        "volcados": os.path.join(datos, "volcados"),
        "articulos": os.path.join(RAIZ, "articulos"),
        "boletines": os.path.expanduser(salida),
    }
    for p in r.values():
        os.makedirs(p, exist_ok=True)
    return r


def cargar_perfil(ruta=None, obligatorio=True):
    ruta = ruta or RUTA_PERFIL
    if not os.path.exists(ruta):
        if obligatorio:
            print("NO_HAY_PERFIL: todavia no existe perfil.json. Hay que hacer la "
                  "configuracion inicial (ver INSTRUCCIONES.md, paso 1).", file=sys.stderr)
            sys.exit(2)
        return None
    with open(ruta, encoding="utf-8") as f:
        perfil = json.load(f)
    errores = validar(perfil)
    if errores:
        print("El perfil tiene problemas:", file=sys.stderr)
        for e in errores:
            print("  - " + e, file=sys.stderr)
        sys.exit(2)
    return perfil


def validar(p):
    errores = []
    b = p.get("boletin") or {}
    if not b.get("titulo"):
        errores.append("falta boletin.titulo")
    amb = p.get("ambitos") or []
    if not amb:
        errores.append("hace falta al menos un ambito en 'ambitos'")
    for i, a in enumerate(amb, 1):
        if not a.get("nombre"):
            errores.append(f"el ambito {i} no tiene nombre")
        if not (a.get("terminos_en") or []):
            errores.append(f"el ambito '{a.get('nombre', i)}' no tiene terminos_en "
                           "(las bases buscan sobre todo en ingles)")
    n = p.get("n_articulos")
    if not isinstance(n, int) or not 1 <= n <= 40:
        errores.append("n_articulos debe ser un entero entre 1 y 40")
    claves = [s.get("clave") for s in (p.get("secciones") or [])]
    if len(claves) != len(set(claves)):
        errores.append("hay dos secciones fijas con la misma clave")
    for s in p.get("secciones") or []:
        if not (s.get("clave") and s.get("titulo")):
            errores.append("cada seccion fija necesita 'clave' y 'titulo'")
    f = p.get("fuentes") or {}
    if f and not any(f.values()):
        errores.append("no hay ninguna base de datos activada en 'fuentes'")
    if not (p.get("email_apis") or "").count("@") == 1:
        errores.append("falta email_apis: OpenAlex, Crossref y Unpaywall piden un "
                       "correo de contacto en cada consulta (no se envia nada a nadie)")
    return errores


def leer_json(ruta, defecto=None):
    if os.path.exists(ruta):
        try:
            with open(ruta, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return defecto


def escribir_json(ruta, datos):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # python3 herramientas/comun.py  -> valida el perfil y dice si esta listo
    p = cargar_perfil()
    print(f"Perfil correcto: '{p['boletin']['titulo']}', {len(p['ambitos'])} ambitos, "
          f"{p['n_articulos']} articulos por numero, {len(p.get('secciones') or [])} "
          f"secciones fijas, descarga de PDF {'activada' if p.get('descargar_pdf') else 'desactivada'}.")
