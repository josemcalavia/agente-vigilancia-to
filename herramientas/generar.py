#!/usr/bin/env python3
"""
Maqueta el boletin en PDF: portada, presentacion, secciones fijas, indice por
ambito, una ficha por pagina y colofon. Cabecera y pie en todas las paginas.

Entradas:
  datos/volcados/volcado_AAAAMMDD-HHMM.json    lo que produce buscar.py
  datos/volcados/resumenes_AAAAMMDD-HHMM.json  lo que escribe el agente

Uso:
    python3 herramientas/generar.py <volcado.json> <resumenes.json>
    python3 herramientas/generar.py --muestra     # boletin de prueba para ver la estetica

Necesita Google Chrome, Chromium o Microsoft Edge instalado (se usa para pasar
el HTML a PDF) y la libreria pypdf (pip install pypdf).

Imprime en la ultima linea la ruta del PDF generado.

Agente de vigilancia de literatura en Terapia Ocupacional.
Diseno original: José María Calavia Balduz. Licencia CC BY-NC-SA 4.0.
"""
import base64, html, json, mimetypes, os, re, shutil, subprocess, sys, tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import (AUTORIA, LICENCIA, LICENCIA_URL, RAIZ, cargar_perfil,  # noqa: E402
                   escribir_json, leer_json, rutas)
import estetica  # noqa: E402
import memoria  # noqa: E402

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# Linea de autoria del agente. Es condicion de la licencia: no se quita, no se
# cambia y no depende del perfil. Ver LICENCIA.md.
LINEA_AUTORIA = f"Agente de vigilancia diseñado por {AUTORIA}"


# ------------------------------------------------------------------ utilidades
def limpia(t):
    if not t:
        return ""
    t = html.unescape(str(t))
    for a in ("\u202f", "\u2009", "\xa0"):
        t = t.replace(a, " ")
    t = re.sub(r"(\d)\s*[\u2014\u2013]\s*(\d)", r"\1-\2", t)   # rangos 2020–2025
    t = re.sub(r"(?<=\w)\u2013(?=\w)", "-", t)
    t = re.sub(r"\s*[\u2014\u2013]\s*", ", ", t)              # sin rayas: comas
    return puntuacion(re.sub(r"\s+", " ", t).strip())


def puntuacion(t):
    """Limpia choques de signos: comas dobladas, coma antes de otro signo..."""
    t = re.sub(r"\s+([,.;:)\]])", r"\1", t)
    t = re.sub(r",(?:\s*,)+", ",", t)
    t = re.sub(r",\s*([.;:)\]?!])", r"\1", t)
    t = re.sub(r"([;:])\s*,", r"\1", t)
    t = re.sub(r"([(\[\u00bf\u00a1])\s*,\s*", r"\1", t)
    t = re.sub(r"^\s*,\s*", "", t)
    t = re.sub(r",(?=[^\s\d])", ", ", t)
    return t.strip()


def esc(t):
    return html.escape(limpia(t))


def fecha_larga(d):
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def data_uri(ruta):
    if not ruta:
        return None
    ruta = ruta if os.path.isabs(ruta) else os.path.join(RAIZ, ruta)
    if not os.path.exists(ruta):
        print(f"AVISO: no encuentro el logo {ruta}; el boletín sale sin logo.")
        return None
    tipo = mimetypes.guess_type(ruta)[0] or "image/png"
    with open(ruta, "rb") as f:
        return f"data:{tipo};base64," + base64.b64encode(f.read()).decode()


def slug(t):
    import unicodedata
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9]+", "_", t).strip("_")[:40] or "Boletin"


# ----------------------------------------------------------------- numeracion
def asignar_numero(carpeta_datos, stamp):
    """El volumen es el ano y el numero es correlativo dentro del ano.
    Idempotente: regenerar el mismo volcado no gasta un numero nuevo."""
    p = os.path.join(carpeta_datos, "numeracion.json")
    est = leer_json(p, {"asignados": {}, "ultimo_por_anio": {}})
    if stamp in est["asignados"]:
        a = est["asignados"][stamp]
        return a["anio"], a["numero"]
    anio = stamp[:4]
    numero = int(est["ultimo_por_anio"].get(anio, 0)) + 1
    est["ultimo_por_anio"][anio] = numero
    est["asignados"][stamp] = {"anio": int(anio), "numero": numero}
    escribir_json(p, est)
    return int(anio), numero


# ------------------------------------------------------------------- acceso
def bloque_acceso(a):
    """El boletin se comparte: no dice nada de descargas locales. Solo si es de
    acceso abierto o no, y donde conseguirlo."""
    u = a.get("enlace_articulo") or a.get("oa_landing") or a.get("editor_url")
    if a.get("is_oa"):
        badge, etiqueta = '<span class="badge badge-ab">Acceso abierto</span>', "Leer el artículo"
    else:
        badge, etiqueta = '<span class="badge badge-ce">Acceso cerrado</span>', "Ir al artículo"
    if not u:
        return f'<div class="acc">{badge}</div>'
    t = re.sub(r"^https?://(www\.)?", "", u)
    t = t[:67] + "..." if len(t) > 70 else t
    return (f'<div class="acc">{badge}<span class="enlace"><span class="k">{esc(etiqueta)}</span>'
            f'<a href="{html.escape(u)}">{esc(t)}</a></span></div>')


# --------------------------------------------------------------------- HTML
def construir(volcado, resumenes, perfil, anio, numero, fecha, carpeta_datos):
    css = estetica.css(perfil)
    b = perfil["boletin"]
    ed = perfil.get("editor") or {}
    logo = data_uri(ed.get("logo") or (perfil.get("estetica") or {}).get("logo"))
    titulo = b["titulo"]
    subtitulo = b.get("subtitulo") or "Boletín de vigilancia científica en Terapia Ocupacional"
    ambitos = [a["nombre"] for a in perfil["ambitos"]]

    def doc(cuerpo, extra=""):
        return ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
                f'<title>{html.escape(titulo)}</title><style>' + css + extra +
                '</style></head><body>' + cuerpo + '</body></html>')

    arts, supl = volcado.get("articles") or [], volcado.get("suplentes") or []
    res_art = resumenes.get("articulos") or {}
    fichas = []
    for pref, lista, base in (("", arts, 0), ("s", supl, 1000)):
        for i, a in enumerate(lista, 1):
            r = res_art.get(f"{pref}{i}")
            if r:
                f = dict(a)
                f.update(r)
                f["_idx"] = base + i
                fichas.append(f)

    grupos = [(c, [f for f in fichas if f.get("categoria") == c]) for c in ambitos]
    grupos = [(c, it) for c, it in grupos if it]
    otros = [f for f in fichas if f.get("categoria") not in ambitos]
    if otros:
        grupos.append(("Otros", otros))
    num_ficha, k = {}, 0
    for _, items in grupos:
        for f in items:
            k += 1
            num_ficha[f["_idx"]] = k
    por_clave = {(str(i) if i < 1000 else f"s{i - 1000}"): n for i, n in num_ficha.items()}

    def fichas_en(t):
        """El agente cita fichas por su clave ("{8}", "{s2}"); aqui se cambia
        por el numero impreso, que va por ambito y no coincide con la clave."""
        def cambia(m):
            n = por_clave.get(m.group(1))
            if n is None:
                print(f"AVISO: el texto cita la ficha {{{m.group(1)}}}, que no está en el número")
                return "?"
            return "%02d" % n
        return re.sub(r"\{(s?\d+)\}", cambia, t or "")

    n_oa = sum(1 for f in fichas if f.get("is_oa"))
    fuentes = ", ".join(sorted((volcado.get("fuentes_consultadas") or {}).keys())) or "PubMed"
    desde = volcado.get("buscado_desde") or ""
    try:
        d_desde = datetime.strptime(desde[:10], "%Y-%m-%d")
        periodo = f"del {fecha_larga(d_desde)} al {fecha_larga(fecha)}"
    except ValueError:
        periodo = f"hasta el {fecha_larga(fecha)}"

    # ------------------------------------------------------------- portada
    editor = []
    if ed.get("nombre"):
        editor.append(f'<div class="editor">Edita: {esc(ed["nombre"])}</div>')
    extra_ed = " · ".join(x for x in (ed.get("institucion"), ed.get("contacto")) if x)
    if extra_ed:
        editor.append(f"<div>{esc(extra_ed)}</div>")
    est = estetica.resolver(perfil)
    C = ['<div class="pcont">',
         '<div class="banda"></div>' if est["banda_portada"] else "",
         f'<img class="logo" src="{logo}" alt="">' if logo else "",
         f'<div class="cabecera-numero">Año {anio} · Número {numero}</div>',
         f'<h1>{esc(titulo)}</h1>',
         f'<div class="psub">{esc(subtitulo)}</div>',
         '<div class="regla"></div>',
         f'<div class="pmeta"><b>Fecha</b> {fecha_larga(fecha)}<br>'
         f'<b>Periodo revisado</b> {esc(periodo)}<br>'
         f'<b>Ámbitos</b> {esc(", ".join(ambitos))}<br>'
         f'<b>Bases consultadas</b> {esc(fuentes)}</div>',
         '<div class="cifras">'
         f'<div class="cifra"><div class="n">{len(fichas)}</div><div class="l">artículos en este número</div></div>'
         f'<div class="cifra"><div class="n">{n_oa}</div><div class="l">de acceso abierto</div></div>'
         f'<div class="cifra"><div class="n">{len(fichas) - n_oa}</div><div class="l">de acceso cerrado</div></div>'
         '</div>',
         '<div class="pfoot">' + "".join(editor) +
         f'<div class="agente">{esc(LINEA_AUTORIA)} · Licencia {LICENCIA}</div></div>',
         '</div>']
    portada = doc("".join(C), "@page{size:A4;margin:0}")

    # ------------------------------------------------------- presentacion
    P = ['<h2 class="sec">Sobre este boletín</h2><div class="presentacion">']
    parrafos = perfil.get("presentacion") or [
        f"Este boletín reúne la investigación reciente que cruza la Terapia Ocupacional con "
        f"{', '.join(ambitos[:-1]) + ' y ' + ambitos[-1] if len(ambitos) > 1 else ambitos[0]}. "
        "Cada artículo lleva un resumen en español, una lectura de por qué importa en la "
        "práctica y el enlace para leerlo entero.",
        "No sustituye a leer los artículos: es un mapa para decidir cuál merece tu tiempo. "
        "Cuando un trabajo es un protocolo, un piloto muy pequeño o un preprint sin revisar, "
        "se indica en su ficha con una nota de cautela.",
    ]
    P += [f"<p>{esc(p)}</p>" for p in parrafos]
    P.append("</div>")

    previos, n_numeros = memoria.recuento_por_categoria(carpeta_datos, (anio, numero))
    acumulado = dict(previos)
    for f in fichas:
        acumulado[f.get("categoria")] = acumulado.get(f.get("categoria"), 0) + 1
    if n_numeros:
        P.append(f"<p>Llevamos {n_numeros + 1} números y {sum(acumulado.values())} artículos "
                 "compartidos. Así se reparten por ámbito:</p>")
    else:
        P.append("<p>Esto es lo que trae este primer número por ámbito:</p>")
    P.append('<div class="recuento">' + "".join(
        f'<div><span class="c">{esc(c)}</span><span class="n">{acumulado[c]}</span></div>'
        for c in ambitos + ["Otros"] if acumulado.get(c)) + "</div>")
    if any(f.get("cuartil_revista") for f in fichas):
        P.append("<p>Junto a la revista aparece su mejor cuartil <b>SJR</b> (SCImago Journal "
                 "Rank), calculado sobre datos de Scopus. No es el JCR de Clarivate.</p>")
    P.append('<div class="decl"><b>Declaración de uso de inteligencia artificial</b>'
             "Contenido elaborado con ayuda de IA generativa y revisado bajo la supervisión y "
             "responsabilidad de quien edita el boletín, conforme al artículo 50 del Reglamento "
             "(UE) 2024/1689. La búsqueda es automática y solo enlaza copias legales de los "
             "artículos. Esta declaración no exime de la responsabilidad sobre la exactitud, "
             "las fuentes y los derechos de autor del material citado.</div>")

    # ----------------------------------------------------- secciones fijas
    secciones = list(perfil.get("secciones") or [])
    textos = resumenes.get("secciones") or {}
    if perfil.get("seguimiento", True) and textos.get("seguimiento"):
        secciones.append({"clave": "seguimiento", "titulo": "Lo que se repite",
                          "subtitulo": "Visto sobre los números anteriores."})
    hay = [s for s in secciones if (textos.get(s["clave"]) or {}).get("texto")]
    if hay:
        titulo_sec = perfil.get("titulo_secciones") or "Destacados del número"
        P.append(f'<h2 class="sec saltop">{esc(titulo_sec)}</h2>')
        for s in hay:
            d = textos[s["clave"]]
            P.append(f'<div class="destacado"><h3><span class="marca"></span>{esc(s["titulo"])}</h3>')
            if s.get("subtitulo"):
                P.append(f'<div class="rotulo">{esc(s["subtitulo"])}</div>')
            for par in re.split(r"\n\s*\n", fichas_en(d.get("texto")).strip()):
                P.append(f"<p>{esc(par)}</p>")
            if d.get("ref"):
                P.append(f'<div class="ref">{esc(fichas_en(d["ref"]))}</div>')
            P.append("</div>")
    faltan = [s["clave"] for s in (perfil.get("secciones") or [])
              if not (textos.get(s["clave"]) or {}).get("texto")]
    if faltan:
        print("AVISO: secciones fijas sin texto en resumenes.json: " + ", ".join(faltan))

    # ------------------------------------------------------------- indice
    P.append('<h2 class="sec saltop">Índice por ámbito</h2>')
    P.append('<div class="intro"><p>Cada ficha ocupa una página: título, autores, revista, '
             'ámbito, resumen en español, por qué importa y enlace al artículo. Los resúmenes '
             'parten del resumen publicado y, cuando había texto completo en acceso abierto, '
             'se han afinado con él. No se añade ningún hallazgo que no esté en la fuente.</p></div>')
    n_conf = sum(1 for f in fichas if f.get("relevancia"))
    if n_conf:
        P.append('<div class="aviso"><b>Sobre el diseño de los estudios</b>'
                 f'{n_conf} ficha{"" if n_conf == 1 else "s"} lleva{"" if n_conf == 1 else "n"} una '
                 'nota de cautela: protocolos, pilotos muy pequeños o trabajos sin revisión por '
                 'pares, de los que aún no se pueden sacar conclusiones firmes.</div>')
    for cat, items in grupos:
        P.append(f'<div class="catbloque"><h3>{esc(cat)}<span class="cuenta">{len(items)} '
                 f'artículo{"" if len(items) == 1 else "s"}</span></h3><ol>')
        for f in items:
            P.append(f'<li><span class="num">{num_ficha[f["_idx"]]:02d}</span>'
                     f'<span>{esc((f.get("title") or "").rstrip("."))}</span></li>')
        P.append("</ol></div>")

    # -------------------------------------------------------------- fichas
    for cat, items in grupos:
        P.append(f'<div class="catsep saltop"><h2>{esc(cat)}<span class="cuenta">{len(items)} '
                 f'artículo{"" if len(items) == 1 else "s"}</span></h2></div>')
        for f in items:
            q = f.get("cuartil_revista")
            cuartil = f'<span class="cuartil">Q{q}</span>' if q in (1, 2, 3, 4) else ""
            P.append('<div class="ficha">')
            P.append(f'<div class="cabf"><span class="n">{num_ficha[f["_idx"]]:02d}</span>'
                     f'<h3>{esc((f.get("title") or "").rstrip("."))}</h3></div>')
            P.append(f'<div class="meta">{esc(", ".join(f.get("authors") or []))}<br>'
                     f'<span class="rev">{esc(f.get("journal"))}</span>{cuartil} · '
                     f'{esc(f.get("year") or "sin año")} · DOI {esc(f.get("doi") or "no disponible")}'
                     f'<br>Localizado en {esc(f.get("source") or "PubMed")}</div>')
            P.append('<div class="cuerpo">')
            P.append(f'<span class="tag">{esc(cat)}</span>')
            for t in (f.get("temas") or [])[:3]:
                P.append(f'<span class="tag">{esc(t)}</span>')
            if f.get("relevancia"):
                P.append(f'<div class="confirmar">{esc(f["relevancia"])}</div>')
            P.append(f"<p>{esc(f.get('resumen'))}</p>")
            if f.get("nota_pdf"):
                P.append(f'<div class="notapdf">{esc(f["nota_pdf"])}</div>')
            if f.get("porque_importa"):
                P.append(f'<div class="importa"><b>Por qué importa</b>{esc(f["porque_importa"])}</div>')
            P.append(bloque_acceso(f))
            P.append("</div></div>")

    # ------------------------------------------------------------- colofon
    quien = esc(ed.get("nombre")) if ed.get("nombre") else "la persona que lo edita"
    P.append('<div class="colofon saltop">')
    P.append(f'<h2 class="sec">Créditos</h2>')
    P.append(f"<p><b>{esc(titulo)}</b>. Año {anio}, número {numero}, {fecha_larga(fecha)}. "
             f"Selección y revisión de contenidos a cargo de {quien}.</p>")
    P.append(f"<p>Elaborado con el agente de vigilancia de literatura en Terapia Ocupacional "
             f"diseñado por <b>{esc(AUTORIA)}</b>, distribuido bajo licencia "
             f'<a href="{LICENCIA_URL}">Creative Commons Reconocimiento-NoComercial-CompartirIgual '
             f"4.0 Internacional</a> ({LICENCIA}).</p>")
    P.append("<p>Los artículos citados pertenecen a sus autores y editoriales. Los resúmenes son "
             "elaboración propia a partir de los resúmenes publicados.</p></div>")

    cuerpo = doc("\n".join(P))
    return portada, cuerpo, fichas, doc, logo, titulo


def sellos(doc, logo, titulo, anio, numero, total, pie=""):
    """Cabecera y pie de las paginas 2..total, cada una con su numero. El pie
    lleva a quien edita el boletin; la autoria del agente va en portada,
    creditos y metadatos, no en cada pagina."""
    pags = []
    for i in range(2, total + 1):
        cab = (f'<img src="{logo}" alt="">' if logo else "") + \
              f'<span class="t">{esc(titulo)} · Año {anio}, n.º {numero}</span>'
        pags.append(f'<div class="sello"><div class="scab">{cab}</div>'
                    f'<div class="spie"><span>{esc(pie)}</span>'
                    f'<span>{i} de {total}</span></div></div>')
    return doc("".join(pags), "@page{size:A4;margin:0}html,body{background:transparent}")


# --------------------------------------------------------------- render PDF
def buscar_navegador():
    if os.environ.get("CHROME_PATH") and os.path.exists(os.environ["CHROME_PATH"]):
        return os.environ["CHROME_PATH"]
    candidatos = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for c in candidatos:
        if os.path.exists(c):
            return c
    for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
              "microsoft-edge", "msedge", "chrome"):
        p = shutil.which(n)
        if p:
            return p
    print("ERROR: no encuentro Google Chrome, Chromium ni Microsoft Edge. Instala uno de "
          "ellos o indica la ruta en la variable CHROME_PATH.", file=sys.stderr)
    sys.exit(3)


def a_pdf(html_txt, destino, tmp, nav):
    ruta_html = os.path.join(tmp, os.path.basename(destino).replace(".pdf", ".html"))
    with open(ruta_html, "w", encoding="utf-8") as f:
        f.write(html_txt)
    url = "file:///" + ruta_html.replace(os.sep, "/").lstrip("/")
    subprocess.run([nav, "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                    f"--print-to-pdf={destino}", "--virtual-time-budget=20000", url],
                   check=True, capture_output=True)
    return destino


def montar(portada, cuerpo, doc, logo, titulo, salida, anio, numero, perfil):
    import pypdf
    nav = buscar_navegador()
    with tempfile.TemporaryDirectory() as tmp:
        p_pdf = a_pdf(portada, os.path.join(tmp, "portada.pdf"), tmp, nav)
        c_pdf = a_pdf(cuerpo, os.path.join(tmp, "cuerpo.pdf"), tmp, nav)
        cuer = pypdf.PdfReader(c_pdf)
        total = 1 + len(cuer.pages)
        ed = perfil.get("editor") or {}
        pie = " · ".join(x for x in (ed.get("nombre"), ed.get("institucion")) if x)
        s_pdf = a_pdf(sellos(doc, logo, titulo, anio, numero, total, pie),
                      os.path.join(tmp, "sellos.pdf"), tmp, nav)
        sel = pypdf.PdfReader(s_pdf)
        w = pypdf.PdfWriter()
        w.add_page(pypdf.PdfReader(p_pdf).pages[0])
        for i, pg in enumerate(cuer.pages):
            if i < len(sel.pages):
                pg.merge_page(sel.pages[i])
            w.add_page(pg)
        ed = (perfil.get("editor") or {}).get("nombre")
        w.add_metadata({
            "/Title": f"{titulo}. Año {anio}, número {numero}",
            "/Author": ed or AUTORIA,
            "/Subject": "Boletín de vigilancia científica en Terapia Ocupacional",
            "/Keywords": "Terapia Ocupacional, " + ", ".join(a["nombre"] for a in perfil["ambitos"]),
            "/Creator": f"{LINEA_AUTORIA}. Licencia {LICENCIA}",
        })
        with open(salida, "wb") as f:
            w.write(f)
    return salida, total


# --------------------------------------------------------------- revisiones
def revisar(pdf, resumenes):
    import pypdf
    r = pypdf.PdfReader(pdf)
    texto = " ".join((pg.extract_text() or "") for pg in r.pages)
    if AUTORIA.replace(" ", "") not in texto.replace(" ", "").replace("\n", ""):
        print("ERROR: el PDF no lleva la autoría del agente. Es condición de la licencia "
              "(ver LICENCIA.md); el boletín no es válido así.", file=sys.stderr)
        sys.exit(4)
    flojas = []
    for i, pg in enumerate(r.pages[1:], 2):
        lineas = [l for l in (pg.extract_text() or "").split("\n")
                  if AUTORIA not in l and "Año" not in l]
        if len(" ".join(lineas).split()) < 40:
            flojas.append(i)
    if flojas:
        print(f"AVISO de maqueta: páginas casi vacías: {', '.join(map(str, flojas))}. "
              "Suele arreglarse acortando el texto anterior.")

    textos = []
    for a in (resumenes.get("articulos") or {}).values():
        textos += [a.get(c) or "" for c in ("resumen", "porque_importa", "relevancia")]
    for v in (resumenes.get("secciones") or {}).values():
        textos.append((v or {}).get("texto") or "")
    t = " ".join(textos)
    letras = sum(1 for c in t if c.isalpha())
    if letras > 500 and sum(1 for c in t if c in "áéíóúüñÁÉÍÓÚÜÑ") / letras < 0.008:
        print("AVISO de redacción: el texto casi no lleva tildes. Revísalo antes de difundir.")
    malas = [x for x in textos if re.search(r"[—–]", re.sub(r"\d\s*[—–]\s*\d", "", x))
             or re.search(r",\s*,|,\s*[.;:]|\s,", x)]
    if malas:
        print(f"AVISO de puntuación: {len(malas)} textos con rayas o comas dobladas "
              "(corregidas al maquetar, pero conviene afinar la redacción).")


def marcar(carpeta_datos, fichas, archivo):
    """Anota lo publicado (o descartado) para no volver a traerlo."""
    import unicodedata

    def nt(t):
        t = unicodedata.normalize("NFKD", (t or "").lower())
        return re.sub(r"[^a-z0-9]+", "", "".join(c for c in t if not unicodedata.combining(c)))
    p = os.path.join(carpeta_datos, archivo)
    d = leer_json(p, {}) or {}
    dois, pmids, tits = set(d.get("dois") or []), set(d.get("pmids") or []), set(d.get("titulos") or [])
    for f in fichas:
        if f.get("doi"):
            dois.add(f["doi"].lower())
        if f.get("pmid"):
            pmids.add(f["pmid"])
        if f.get("title"):
            tits.add(nt(f["title"]))
    escribir_json(p, {"dois": sorted(dois), "pmids": sorted(pmids), "titulos": sorted(tits)})


# ------------------------------------------------------------------- muestra
def muestra(perfil):
    """Boletin de prueba con datos inventados y marcados como tales, para ver
    la estetica sin buscar nada. No gasta numero ni toca la memoria."""
    import copy
    ej = leer_json(os.path.join(RAIZ, "ejemplo", "volcado_muestra.json"))
    rs = leer_json(os.path.join(RAIZ, "ejemplo", "resumenes_muestra.json"))
    perfil = copy.deepcopy(perfil)
    cats = [a["nombre"] for a in perfil["ambitos"]]
    for i, a in enumerate(ej["articles"]):
        a["categoria"] = cats[i % len(cats)]
    textos = rs.setdefault("secciones", {})
    for s in perfil.get("secciones") or []:
        textos.setdefault(s["clave"], {"texto": (
            f"Texto de ejemplo para la sección «{s['titulo']}». "
            + (s.get("pauta") or "Aquí irá lo que el agente escriba en cada número.")
            + " Ronda las 120 a 145 palabras en dos párrafos."), "ref": "Ficha {1}"})
    tmp = tempfile.mkdtemp()
    r = rutas(perfil)
    portada, cuerpo, fichas, doc, logo, titulo = construir(
        ej, rs, perfil, datetime.now().year, 0, datetime.now(), tmp)
    salida = os.path.join(r["boletines"], "MUESTRA_estetica.pdf")
    salida, pags = montar(portada, cuerpo, doc, logo, titulo, salida, datetime.now().year, 0, perfil)
    print(f"Muestra generada ({pags} páginas, datos ficticios):")
    print(salida)


def main():
    perfil = cargar_perfil()
    if len(sys.argv) == 2 and sys.argv[1] == "--muestra":
        return muestra(perfil)
    if len(sys.argv) < 3:
        print("Uso: generar.py <volcado.json> <resumenes.json>  |  generar.py --muestra",
              file=sys.stderr)
        sys.exit(1)
    volcado = leer_json(sys.argv[1])
    resumenes = leer_json(sys.argv[2])
    if volcado is None or resumenes is None:
        print("ERROR: no puedo leer el volcado o los resúmenes (¿JSON mal formado?).",
              file=sys.stderr)
        sys.exit(1)
    r = rutas(perfil)

    decision = resumenes.get("decision") or {}
    if decision.get("publicar") is False:
        print("SIN_NUMERO")
        print(f"Motivo: {decision.get('motivo') or 'sin motivo indicado'}")
        print("No se genera PDF y no se gasta número de la serie.")
        return

    m = re.search(r"(\d{8}-\d{4})", os.path.basename(sys.argv[1]))
    stamp = m.group(1) if m else datetime.now().strftime("%Y%m%d-%H%M")
    fecha = datetime.strptime(stamp[:8], "%Y%m%d")
    anio, numero = asignar_numero(r["datos"], stamp)
    carpeta = os.path.join(r["boletines"], str(anio))
    os.makedirs(carpeta, exist_ok=True)
    salida = os.path.join(carpeta, f"{slug(perfil['boletin']['titulo'])}_{anio}-{numero:02d}"
                                   f"_{stamp[:8]}.pdf")

    portada, cuerpo, fichas, doc, logo, titulo = construir(
        volcado, resumenes, perfil, anio, numero, fecha, r["datos"])
    salida, paginas = montar(portada, cuerpo, doc, logo, titulo, salida, anio, numero, perfil)
    print(f"Año {anio}, número {numero}: {len(fichas)} artículos, {paginas} páginas")
    revisar(salida, resumenes)

    memoria.registrar(r["datos"], anio, numero, stamp, fichas)
    marcar(r["datos"], fichas, "publicados.json")
    arts, supl = volcado.get("articles") or [], volcado.get("suplentes") or []
    tirados = []
    for k in (resumenes.get("descartados") or {}):
        k = str(k)
        try:
            tirados.append(supl[int(k[1:]) - 1] if k.startswith("s") else arts[int(k) - 1])
        except (ValueError, IndexError):
            pass
    if tirados:
        marcar(r["datos"], tirados, "descartados.json")
    print(f"Memoria actualizada. Descartados anotados para no volver a traerlos: {len(tirados)}")
    print(salida)


if __name__ == "__main__":
    main()
