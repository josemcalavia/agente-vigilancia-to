#!/usr/bin/env python3
"""
Capa mecanica de la vigilancia: busca, filtra, deduplica y resuelve el acceso.

  1. Busca cada ambito del perfil cruzado con Terapia Ocupacional en las bases
     que la persona haya elegido (perfil.json -> fuentes). Por defecto, las
     abiertas: PubMed, Europe PMC, OpenAlex (que incluye SciELO y la literatura
     en espanol y portugues) y Crossref. Opcionales: Semantic Scholar, arXiv,
     DOAJ y, con clave propia en claves.json, Scopus, Web of Science, IEEE
     Xplore y Consensus. Lista completa: buscar.py --bases
  2. Exige que el articulo nombre de verdad Terapia Ocupacional y el ambito en
     titulo o resumen: las bases generalistas devuelven mucho ruido.
  3. Deduplica por DOI, PMID y titulo, fusionando los datos de cada copia.
  4. Quita lo ya publicado en numeros anteriores y lo ya descartado.
  5. Resuelve el acceso abierto con Unpaywall y, si el perfil lo pide, descarga
     los PDF que tienen copia legal. Nunca usa Sci-Hub ni fuentes similares.
  6. Escribe datos/volcados/volcado_AAAAMMDD-HHMM.json para que el agente
     juzgue, resuma y genere el boletin.

NO juzga relevancia ni redacta: eso lo hace el agente siguiendo INSTRUCCIONES.md.

Uso:
    python3 herramientas/buscar.py                 # periodo por defecto del perfil
    python3 herramientas/buscar.py --dias 90
    python3 herramientas/buscar.py --desde 2026-01-01

Agente de vigilancia de literatura en Terapia Ocupacional.
Diseno original: José María Calavia Balduz. Licencia CC BY-NC-SA 4.0.
"""
import argparse, json, os, sys, re, time, unicodedata
import urllib.request, urllib.parse, urllib.error
from collections import Counter
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import ANCLAS_TO, cargar_perfil, rutas, leer_json, escribir_json  # noqa: E402

UA = "VigilanciaTO/1.0 (agente de vigilancia en Terapia Ocupacional)"


# ---------------------------------------------------------------- utilidades
def http_json(url, timeout=30, headers=None):
    h = {"User-Agent": UA, "Accept": "application/json"}
    h.update(headers or {})
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout))


def http_text(url, timeout=30, headers=None):
    h = {"User-Agent": UA}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")


def _clean(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&lt;", "<"), ("&gt;", ">"), ("&amp;", "&"),
                 ("&#x2019;", "'"), ("&quot;", '"'), ("&apos;", "'"), ("&nbsp;", " ")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def _tag(s, t):
    m = re.search(rf"<{t}[^>]*>(.*?)</{t}>", s, re.S)
    return _clean(m.group(1)) if m else None


def norm_doi(doi):
    if not doi:
        return None
    d = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", doi.strip().lower())
    return d or None


def norm_title(t):
    if not t:
        return ""
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", t)


def year_of(s):
    m = re.search(r"(19|20)\d{2}", str(s or ""))
    return m.group(0) if m else None


# --------------------------------------------------------------- relevancia
def _aparece(termino, texto):
    """El termino tiene que empezar palabra: "robot" vale para "robotic", pero
    "IA" no debe casar dentro de "familia"."""
    return re.search(r"(?<![\w])" + re.escape(termino.lower()), texto) is not None


def relevante(rec, anclas, terminos, filtro_comun):
    """Tiene que nombrar Terapia Ocupacional Y algun termino de los ambitos (y,
    si el perfil lo define, alguno del filtro comun). Sin resumen, que pasa
    mucho con Crossref, las senales se exigen en el titulo."""
    titulo = (rec.get("title") or "").lower()
    resumen = (rec.get("abstract") or "").lower()
    texto = f"{titulo} {resumen}" if resumen else titulo
    if not any(a.lower() in texto for a in anclas):
        return False
    if not any(_aparece(t, texto) for t in terminos):
        return False
    if filtro_comun and not any(_aparece(t, texto) for t in filtro_comun):
        return False
    return True


def ambito_de(rec, ambitos):
    """Primer ambito cuyos terminos aparezcan, respetando el orden del perfil."""
    texto = f"{rec.get('title') or ''} {rec.get('abstract') or ''}".lower()
    for a in ambitos:
        todos = (a.get("terminos_en") or []) + (a.get("terminos_es") or []) + \
                (a.get("terminos_pt") or [])
        if any(_aparece(t, texto) for t in todos):
            return a["nombre"]
    return "General"


def _y(*grupos):
    """Une grupos de terminos con AND; cada grupo va con OR dentro."""
    return " AND ".join("(" + " OR ".join(f'"{t}"' for t in g) + ")" for g in grupos if g)


# ================================================================== PubMed
def src_pubmed(grupos, desde, retmax):
    partes = " AND ".join("(" + " OR ".join(f'"{t}"[Title/Abstract]' for t in g) + ")"
                          for g in grupos if g)
    term = f'({partes}) AND ("{desde}"[Date - Publication] : "3000"[Date - Publication])'
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(
        {"db": "pubmed", "term": term, "retmax": str(retmax), "retmode": "json", "sort": "date"})
    try:
        ids = http_json(url)["esearchresult"].get("idlist", [])
    except Exception as e:
        print(f"    ! pubmed: {e}", file=sys.stderr)
        return []
    return pubmed_fetch(ids)


def _pubmed_fecha(art):
    bloque = (re.search(r"<ArticleDate[^>]*>(.*?)</ArticleDate>", art, re.S)
              or re.search(r"<PubDate>(.*?)</PubDate>", art, re.S))
    if not bloque:
        return _tag(art, "Year")
    b = bloque.group(1)
    y = _tag(b, "Year") or ""
    if not y:
        return _tag(art, "Year")
    MES = {"jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
           "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"}
    m = (_tag(b, "Month") or "").lower()
    m = MES.get(m[:3], m if m.isdigit() else "")
    d = _tag(b, "Day") or ""
    return "-".join(x for x in (y, m.zfill(2) if m else "", d.zfill(2) if d else "") if x)


def pubmed_fetch(pmids):
    if not pmids:
        return []
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urllib.parse.urlencode(
        {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"})
    try:
        xml = http_text(url)
    except Exception as e:
        print(f"    ! pubmed efetch: {e}", file=sys.stderr)
        return []
    out = []
    for art in re.findall(r"<PubmedArticle>.*?</PubmedArticle>", xml, re.S):
        m = re.search(r"<PMID[^>]*>(\d+)</PMID>", art)
        if not m:
            continue
        pmid = m.group(1)
        doi_m = re.search(r'<ArticleId IdType="doi">(.*?)</ArticleId>', art)
        pmc_m = re.search(r'<ArticleId IdType="pmc">(PMC\d+)</ArticleId>', art)
        autores = []
        for a in re.findall(r"<Author[^>]*>(.*?)</Author>", art, re.S):
            ln, ini = _tag(a, "LastName"), _tag(a, "Initials")
            if ln:
                autores.append(f"{ln} {ini}".strip())
        out.append({
            "source": "PubMed", "pmid": pmid,
            "doi": norm_doi(doi_m.group(1)) if doi_m else None,
            "pmcid": pmc_m.group(1) if pmc_m else None,
            "title": _tag(art, "ArticleTitle"),
            "abstract": " ".join(_clean(x) for x in re.findall(
                r"<AbstractText[^>]*>(.*?)</AbstractText>", art, re.S)),
            "journal": _tag(art, "Title") or _tag(art, "ISOAbbreviation"),
            "year": _tag(art, "Year"),
            "fecha": _pubmed_fecha(art),
            "authors": autores[:8],
            "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })
    return out


# =============================================================== Europe PMC
def src_europepmc(grupos, desde, retmax):
    partes = " AND ".join("(" + " OR ".join(f'TITLE_ABS:"{t}"' for t in g) + ")" for g in grupos if g)
    q = f"({partes}) AND (FIRST_PDATE:[{desde} TO 3000-12-31])"
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(
        {"query": q, "format": "json", "pageSize": str(retmax),
         "resultType": "core", "sort": "P_PDATE_D desc"})
    try:
        res = http_json(url).get("resultList", {}).get("result", [])
    except Exception as e:
        print(f"    ! europepmc: {e}", file=sys.stderr)
        return []
    out = []
    for r in res:
        autores = [a.get("fullName") or "" for a in
                   (r.get("authorList") or {}).get("author", [])][:8]
        pmid = r.get("pmid")
        out.append({
            "source": "Europe PMC", "pmid": pmid,
            "doi": norm_doi(r.get("doi")), "pmcid": r.get("pmcid"),
            "title": _clean(r.get("title")),
            "abstract": _clean(r.get("abstractText")),
            "journal": _clean((r.get("journalInfo") or {}).get("journal", {}).get("title")),
            "year": year_of(r.get("firstPublicationDate") or r.get("pubYear")),
            "fecha": r.get("firstPublicationDate") or year_of(r.get("pubYear")),
            "authors": [a for a in autores if a],
            "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
            "europepmc_url": (f"https://europepmc.org/article/{r.get('source')}/{r.get('id')}"
                              if r.get("source") and r.get("id") else None),
        })
    return out


# ================================================================= OpenAlex
def _openalex_abstract(inv):
    """OpenAlex guarda el resumen como indice invertido; hay que rearmarlo."""
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return _clean(" ".join(pos[i] for i in sorted(pos)))


def src_openalex(grupos, desde, retmax, email):
    filtro = (f"title_and_abstract.search:{_y(*grupos)},"
              f"from_publication_date:{desde},type:article")
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode({
        "filter": filtro, "per-page": str(retmax),
        "sort": "publication_date:desc", "mailto": email})
    res = []
    for intento in range(3):
        try:
            res = http_json(url).get("results", [])
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and intento < 2:
                time.sleep(2 + 3 * intento)
                continue
            print(f"    ! openalex: {e}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"    ! openalex: {e}", file=sys.stderr)
            return []
    out = []
    for r in res:
        ids = r.get("ids") or {}
        pmid = (ids.get("pmid") or "").rsplit("/", 1)[-1] or None
        pmcid = (ids.get("pmcid") or "").rsplit("/", 1)[-1] or None
        loc = (r.get("primary_location") or {}).get("source") or {}
        out.append({
            "source": "OpenAlex", "pmid": pmid, "pmcid": pmcid,
            "doi": norm_doi(r.get("doi")),
            "title": _clean(r.get("display_name")),
            "abstract": _openalex_abstract(r.get("abstract_inverted_index")),
            "journal": _clean(loc.get("display_name")),
            "year": year_of(r.get("publication_date") or r.get("publication_year")),
            "fecha": r.get("publication_date"),
            "authors": [_clean((a.get("author") or {}).get("display_name"))
                        for a in (r.get("authorships") or [])][:8],
            "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
            "openalex_url": r.get("id"),
        })
    return out


# ================================================================= Crossref
def src_crossref(grupos, desde, retmax, email):
    consulta = " ".join(g[0] for g in grupos if g)
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode({
        "query.bibliographic": consulta,
        "filter": f"from-pub-date:{desde},type:journal-article",
        "rows": str(retmax), "mailto": email})
    try:
        items = http_json(url)["message"].get("items", [])
    except Exception as e:
        print(f"    ! crossref: {e}", file=sys.stderr)
        return []
    out = []
    for r in items:
        fecha = r.get("published-print") or r.get("published-online") or r.get("issued") or {}
        partes = (fecha.get("date-parts") or [[None]])[0]
        out.append({
            "source": "Crossref", "pmid": None, "pmcid": None,
            "doi": norm_doi(r.get("DOI")),
            "title": _clean(" ".join(r.get("title") or [])),
            "abstract": _clean(r.get("abstract")),
            "journal": _clean(" ".join(r.get("container-title") or [])),
            "year": year_of(partes[0]),
            "fecha": "-".join(f"{p:02d}" if i else str(p) for i, p in enumerate(partes) if p),
            "authors": [_clean(f"{a.get('family','')} {(a.get('given','') or '')[:1]}").strip()
                        for a in (r.get("author") or [])][:8],
            "pubmed_url": None,
        })
    return out


# ============================================================ arXiv y DOAJ
def src_arxiv(grupos, desde, retmax):
    q = " AND ".join("(" + " OR ".join(f'all:"{t}"' for t in g[:4]) + ")" for g in grupos if g)
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode({
        "search_query": q, "max_results": str(retmax),
        "sortBy": "submittedDate", "sortOrder": "descending"})
    try:
        xml = http_text(url)
    except Exception as e:
        print(f"    ! arxiv: {e}", file=sys.stderr)
        return []
    out = []
    for e in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        pub = (_tag(e, "published") or "")[:10]
        if pub and pub < desde:
            continue
        aid = (_tag(e, "id") or "").rstrip("/")
        doi_m = re.search(r"<arxiv:doi[^>]*>(.*?)</arxiv:doi>", e, re.S)
        out.append({
            "source": "arXiv", "pmid": None, "pmcid": None,
            "doi": norm_doi(doi_m.group(1)) if doi_m else None,
            "title": _tag(e, "title"), "abstract": _tag(e, "summary"),
            "journal": "arXiv, preprint sin revisión por pares",
            "year": year_of(pub), "fecha": pub,
            "authors": [_clean(n) for n in re.findall(r"<name>(.*?)</name>", e, re.S)][:8],
            "pubmed_url": None, "arxiv_url": aid,
            "arxiv_pdf": aid.replace("/abs/", "/pdf/") if "/abs/" in aid else None,
        })
    return out


def src_doaj(grupos, desde, retmax):
    q = " AND ".join(f'bibjson.abstract:("{g[0]}")' for g in grupos if g)
    url = f"https://doaj.org/api/search/articles/{urllib.parse.quote(q)}?pageSize={retmax}"
    try:
        res = http_json(url).get("results", [])
    except Exception as e:
        print(f"    ! doaj: {e}", file=sys.stderr)
        return []
    out = []
    for r in res:
        b = r.get("bibjson") or {}
        if year_of(b.get("year")) and year_of(b.get("year")) < desde[:4]:
            continue
        doi = next((i.get("id") for i in (b.get("identifier") or []) if i.get("type") == "doi"), None)
        pdf = next((l.get("url") for l in (b.get("link") or []) if l.get("type") == "fulltext"), None)
        out.append({
            "source": "DOAJ", "pmid": None, "pmcid": None, "doi": norm_doi(doi),
            "title": _clean(b.get("title")), "abstract": _clean(b.get("abstract")),
            "journal": _clean((b.get("journal") or {}).get("title")),
            "year": year_of(b.get("year")), "fecha": year_of(b.get("year")),
            "authors": [_clean(a.get("name")) for a in (b.get("author") or [])][:8],
            "pubmed_url": None, "doaj_pdf": pdf,
        })
    return out


# ========================================================= Semantic Scholar
def src_semanticscholar(grupos, desde, retmax, clave=None):
    """Gratuita y sin clave (con clave va mas holgada). Usa la busqueda masiva,
    que admite booleanos: + es AND, | es OR."""
    q = " + ".join("(" + " | ".join(f'"{t}"' for t in g) + ")" for g in grupos if g)
    url = "https://api.semanticscholar.org/graph/v1/paper/search/bulk?" + urllib.parse.urlencode({
        "query": q, "publicationDateOrYear": f"{desde}:", "sort": "publicationDate:desc",
        "fields": "title,abstract,year,publicationDate,authors,venue,externalIds,openAccessPdf"})
    h = {"x-api-key": clave} if clave else None
    datos = []
    for intento in range(3):
        try:
            datos = http_json(url, headers=h).get("data") or []
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and intento < 2:
                time.sleep(4 + 4 * intento)
                continue
            print(f"    ! semantic scholar: {e}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"    ! semantic scholar: {e}", file=sys.stderr)
            return []
    out = []
    for r in datos[:retmax]:
        ids = r.get("externalIds") or {}
        pmid = ids.get("PubMed")
        out.append({
            "source": "Semantic Scholar", "pmid": pmid,
            "pmcid": f"PMC{ids['PubMedCentral']}" if ids.get("PubMedCentral") else None,
            "doi": norm_doi(ids.get("DOI")),
            "title": _clean(r.get("title")), "abstract": _clean(r.get("abstract")),
            "journal": _clean(r.get("venue")),
            "year": year_of(r.get("year")), "fecha": r.get("publicationDate") or year_of(r.get("year")),
            "authors": [_clean(a.get("name")) for a in (r.get("authors") or [])][:8],
            "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
        })
    return out


# ======================================== bases con licencia (necesitan clave)
def src_scopus(grupos, desde, retmax, clave):
    q = f"TITLE-ABS-KEY({_y(*grupos)}) AND PUBYEAR > {int(desde[:4]) - 1}"
    url = "https://api.elsevier.com/content/search/scopus?" + urllib.parse.urlencode(
        {"query": q, "count": str(retmax), "sort": "-coverDate"})
    try:
        d = http_json(url, headers={"X-ELS-APIKey": clave})
    except Exception as e:
        print(f"    ! scopus: {e}", file=sys.stderr)
        return []
    return [{
        "source": "Scopus", "pmid": r.get("pubmed-id"), "pmcid": None,
        "doi": norm_doi(r.get("prism:doi")),
        "title": _clean(r.get("dc:title")), "abstract": _clean(r.get("dc:description")),
        "journal": _clean(r.get("prism:publicationName")),
        "year": year_of(r.get("prism:coverDate")), "fecha": r.get("prism:coverDate"),
        "authors": [_clean(r.get("dc:creator"))] if r.get("dc:creator") else [],
        "pubmed_url": None,
    } for r in (d.get("search-results") or {}).get("entry", []) if r.get("dc:title")]


def src_wos(grupos, desde, retmax, clave):
    q = f"TS=({_y(*grupos)}) AND PY=({desde[:4]}-{datetime.now().year})"
    url = "https://api.clarivate.com/apis/wos-starter/v1/documents?" + urllib.parse.urlencode(
        {"q": q, "limit": str(min(retmax, 50)), "sortField": "PY+D", "db": "WOS"})
    try:
        hits = http_json(url, headers={"X-ApiKey": clave}).get("hits", [])
    except Exception as e:
        print(f"    ! web of science: {e}", file=sys.stderr)
        return []
    out = []
    for r in hits:
        ids = r.get("identifiers") or {}
        src = r.get("source") or {}
        out.append({
            "source": "Web of Science", "pmid": ids.get("pmid"), "pmcid": None,
            "doi": norm_doi(ids.get("doi")), "title": _clean(r.get("title")), "abstract": "",
            "journal": _clean(src.get("sourceTitle")), "year": year_of(src.get("publishYear")),
            "fecha": year_of(src.get("publishYear")),
            "authors": [_clean(a.get("displayName")) for a in
                        (r.get("names") or {}).get("authors", [])][:8],
            "pubmed_url": None,
        })
    return out


def src_ieee(grupos, desde, retmax, clave):
    q = " AND ".join("(" + " OR ".join(f'"{t}"' for t in g) + ")" for g in grupos if g)
    url = "https://ieeexploreapi.ieee.org/api/v1/search/articles?" + urllib.parse.urlencode({
        "apikey": clave, "querytext": q, "start_year": desde[:4],
        "max_records": str(retmax), "sort_field": "publication_year", "sort_order": "desc"})
    try:
        arts = http_json(url).get("articles", [])
    except Exception as e:
        print(f"    ! ieee: {e}", file=sys.stderr)
        return []
    return [{
        "source": "IEEE Xplore", "pmid": None, "pmcid": None, "doi": norm_doi(r.get("doi")),
        "title": _clean(r.get("title")), "abstract": _clean(r.get("abstract")),
        "journal": _clean(r.get("publication_title")),
        "year": year_of(r.get("publication_year")), "fecha": year_of(r.get("publication_year")),
        "authors": [_clean(a.get("full_name")) for a in
                    (r.get("authors") or {}).get("authors", [])][:8],
        "pubmed_url": None,
    } for r in arts]


def src_consensus(grupos, desde, retmax, clave):
    """Busqueda semantica: encuentra trabajos que no contienen literalmente los
    terminos. Consulta en lenguaje natural, no booleana."""
    consulta = " ".join(g[0] for g in grupos if g)
    url = "https://api.consensus.app/v1/search?" + urllib.parse.urlencode(
        {"query": consulta[:500], "year_min": int(desde[:4])})
    try:
        d = http_json(url, timeout=45, headers={"x-api-key": clave})
    except Exception as e:
        print(f"    ! consensus: {e}", file=sys.stderr)
        return []
    out = []
    for r in (d.get("results") or [])[:retmax]:
        autores = r.get("authors") or []
        autores = [autores] if isinstance(autores, str) else autores
        out.append({
            "source": "Consensus", "pmid": None, "pmcid": None, "doi": norm_doi(r.get("doi")),
            "title": _clean(r.get("title")), "abstract": _clean(r.get("abstract")),
            "journal": _clean(r.get("journal_name")),
            "year": year_of(r.get("publish_year")),
            "fecha": (r.get("publish_date") or "")[:10] or year_of(r.get("publish_year")),
            "authors": [_clean(a) for a in autores][:8], "pubmed_url": None,
            "cuartil_revista": r.get("sjr_best_quartile"),
        })
    return out


# Catalogo de bases. "clave": None = gratuita sin clave; "opcional" = funciona
# sin clave pero va mejor con ella; "obligatoria" = no funciona sin clave.
BASES = {
    "pubmed":          {"nombre": "PubMed", "clave": None, "defecto": True},
    "europepmc":       {"nombre": "Europe PMC", "clave": None, "defecto": True},
    "openalex":        {"nombre": "OpenAlex", "clave": None, "defecto": True},
    "crossref":        {"nombre": "Crossref", "clave": None, "defecto": True},
    "semanticscholar": {"nombre": "Semantic Scholar", "clave": "opcional", "defecto": False},
    "arxiv":           {"nombre": "arXiv", "clave": None, "defecto": False},
    "doaj":            {"nombre": "DOAJ", "clave": None, "defecto": False},
    "scopus":          {"nombre": "Scopus", "clave": "obligatoria", "defecto": False},
    "wos":             {"nombre": "Web of Science", "clave": "obligatoria", "defecto": False},
    "ieee":            {"nombre": "IEEE Xplore", "clave": "obligatoria", "defecto": False},
    "consensus":       {"nombre": "Consensus", "clave": "obligatoria", "defecto": False},
}


def clave_de(base):
    """Las claves NO van en perfil.json: van en claves.json (que no se comparte)
    o en una variable de entorno VIGILANCIA_<BASE>_KEY."""
    env = os.environ.get(f"VIGILANCIA_{base.upper()}_KEY")
    if env:
        return env.strip()
    from comun import RAIZ
    return ((leer_json(os.path.join(RAIZ, "claves.json"), {}) or {}).get(base) or "").strip()


# ============================================== cuartiles SJR (opcional)
def _norm_revista(nombre, recortar):
    if not nombre:
        return ""
    t = unicodedata.normalize("NFKD", str(nombre).lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    if recortar:
        t = re.sub(r"\([^)]*\)", " ", t)
        t = re.sub(r"\[[^]]*\]", " ", t)
        t = re.split(r"\s*[:;]\s*", t)[0]
        t = re.sub(r"^\s*(the|la|el|le|les|der|die|das)\s+", " ", t)
    return re.sub(r"[^a-z0-9]+", "", t)


def cargar_sjr(carpeta_datos):
    """Cuartiles SJR, solo si la persona ha descargado el CSV de SCImago y lo ha
    dejado en datos/sjr.csv (scimagojr.com/journalrank.php, "Download data").
    El paquete no lo incluye: son datos de SCImago con sus propias condiciones."""
    ruta = os.path.join(carpeta_datos, "sjr.csv")
    if not os.path.exists(ruta):
        return None
    exactas, cortas = {}, {}
    try:
        import csv
        with open(ruta, encoding="utf-8-sig", errors="replace") as f:
            muestra = f.read(4096)
            f.seek(0)
            sep = ";" if muestra.count(";") > muestra.count(",") else ","
            for fila in csv.DictReader(f, delimiter=sep):
                nombre = fila.get("Title") or ""
                m = re.match(r"Q([1-4])", (fila.get("SJR Best Quartile") or "").strip())
                if not (nombre and m):
                    continue
                q = int(m.group(1))
                ke, kc = _norm_revista(nombre, False), _norm_revista(nombre, True)
                if ke:
                    exactas.setdefault(ke, q)
                if kc and kc != ke:
                    cortas.setdefault(kc, q)
    except Exception as e:
        print(f"    ! no se pudo leer datos/sjr.csv: {e}", file=sys.stderr)
        return None
    return exactas, cortas


def aplicar_sjr(tablas, registros):
    if not tablas:
        return 0
    puestos = 0
    for r in registros:
        claves = [k for k in dict.fromkeys([_norm_revista(r.get("journal"), False),
                                            _norm_revista(r.get("journal"), True)]) if k]
        for tabla in tablas:
            q = next((tabla[k] for k in claves if k in tabla), None)
            if q:
                r["cuartil_revista"] = q
                puestos += 1
                break
    return puestos


# =============================================================== Unpaywall
def unpaywall(doi, email):
    vacio = {"is_oa": False, "locations": [], "landing": None, "doi_url": None}
    if not doi:
        return vacio
    try:
        d = http_json(f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={email}")
    except Exception:
        return vacio
    locs = [{"host_type": l.get("host_type"), "url_for_pdf": l.get("url_for_pdf"),
             "url": l.get("url")} for l in (d.get("oa_locations") or [])]
    # los repositorios bloquean mucho menos que las webs de los editores
    locs.sort(key=lambda l: 0 if l["host_type"] == "repository" else 1)
    best = d.get("best_oa_location") or {}
    return {"is_oa": bool(d.get("is_oa")), "locations": locs,
            "landing": best.get("url") or d.get("doi_url"), "doi_url": d.get("doi_url")}


# ================================================================= Descarga
def safe_name(title, ident):
    base = re.sub(r"[^\w\s-]", "", (title or "articulo"))[:80].strip().replace(" ", "_")
    return f"{base}__{ident}.pdf"


def _bajar(url, path, timeout=60):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/pdf,*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
        if data[:4] != b"%PDF":
            return False, "la respuesta no es un PDF"
        with open(path, "wb") as f:
            f.write(data)
        return True, None
    except Exception as e:
        return False, str(e)


def pdf_desde_landing(url_landing):
    """Casi todos los editores declaran su PDF en <meta name="citation_pdf_url">."""
    try:
        h = http_text(url_landing, timeout=30, headers={"Accept": "text/html"})
    except Exception:
        return None
    m = (re.search(r'citation_pdf_url"[^>]*content="([^"]+)"', h)
         or re.search(r'content="([^"]+)"[^>]*name="citation_pdf_url"', h))
    return m.group(1) if m else None


def descargar(rec, oa, carpeta):
    """Prueba las copias legales conocidas. Devuelve (ruta, motivo_fallo)."""
    candidatas = [u for u in (rec.get("arxiv_pdf"), rec.get("doaj_pdf")) if u]
    candidatas += [l["url_for_pdf"] for l in oa["locations"] if l.get("url_for_pdf")]
    candidatas += [l["url"] for l in oa["locations"] if l.get("url") and l["url"] not in candidatas]
    ident = rec.get("pmid") or re.sub(r"[^\w]", "", rec.get("doi") or "sin_id")[-12:]
    destino = os.path.join(carpeta, safe_name(rec.get("title"), ident))
    if os.path.exists(destino):
        return destino, None
    motivos = []
    for u in candidatas[:6]:
        ok, err = _bajar(u, destino)
        if ok:
            return destino, None
        motivos.append(f"{urllib.parse.urlparse(u).netloc}: {err}")
        time.sleep(0.4)
    for loc in oa["locations"][:3]:
        u = pdf_desde_landing(loc["url"]) if loc.get("url") else None
        if not u or u in candidatas:
            continue
        ok, err = _bajar(u, destino)
        if ok:
            return destino, None
        motivos.append(f"{urllib.parse.urlparse(u).netloc}: {err}")
    if not motivos:
        return None, "acceso abierto pero sin enlace directo al PDF"
    return None, "; ".join(motivos[:3])


# ================================================================== Memoria
def enriquecer(base, otro):
    """Vuelca en base los campos que le falten, tomandolos de otra copia del
    mismo articulo. El resumen mas largo gana."""
    for campo in ("doi", "pmid", "pmcid", "journal", "year", "fecha", "pubmed_url",
                  "europepmc_url", "arxiv_url", "arxiv_pdf", "doaj_pdf", "openalex_url"):
        if not base.get(campo) and otro.get(campo):
            base[campo] = otro[campo]
    if len(otro.get("abstract") or "") > len(base.get("abstract") or ""):
        base["abstract"] = otro["abstract"]
    if len(otro.get("authors") or []) > len(base.get("authors") or []):
        base["authors"] = otro["authors"]
    fuentes = base.get("source", "")
    if otro.get("source") and otro["source"] not in fuentes:
        base["source"] = f"{fuentes} y {otro['source']}" if fuentes else otro["source"]


def cargar_vistos(carpeta_datos):
    """Lo ya publicado (publicados.json) y lo descartado (descartados.json).
    Ninguno de los dos vuelve a aparecer en un numero nuevo."""
    d = {"dois": [], "pmids": [], "titulos": []}
    for nombre in ("publicados.json", "descartados.json"):
        x = leer_json(os.path.join(carpeta_datos, nombre), {}) or {}
        for k in d:
            d[k] += x.get(k) or []
    return d


def seleccionar(unicos, n, tope_ambito):
    """Lo mas reciente primero, con un tope por ambito para que un solo tema no
    se coma el numero. Si sobran plazas, se completan por fecha."""
    elegidos, cuenta, sobras = [], Counter(), []
    for r in unicos:
        if len(elegidos) < n and cuenta[r["categoria"]] < tope_ambito:
            elegidos.append(r)
            cuenta[r["categoria"]] += 1
        else:
            sobras.append(r)
    for r in sobras:
        if len(elegidos) >= n:
            break
        elegidos.append(r)
    return elegidos, [r for r in unicos if r not in elegidos]


def resolver_acceso(m, email, descargar_pdf, carpeta):
    oa = unpaywall(m.get("doi"), email)
    rec = dict(m)
    rec["is_oa"] = oa["is_oa"] or bool(m.get("arxiv_pdf")) or bool(m.get("doaj_pdf"))
    rec["oa_landing"] = oa["landing"]
    rec["editor_url"] = (oa.get("doi_url") or (f"https://doi.org/{m['doi']}" if m.get("doi") else None)
                         or m.get("pubmed_url") or m.get("europepmc_url")
                         or m.get("arxiv_url") or m.get("openalex_url"))
    rec["oa_pdf_url"] = next((l["url_for_pdf"] for l in oa["locations"] if l.get("url_for_pdf")), None)
    rec["enlace_articulo"] = rec.get("arxiv_url") or rec["oa_pdf_url"] or oa["landing"] or rec["editor_url"]
    rec["pdf_path"], rec["download_note"] = None, None
    if rec["is_oa"] and descargar_pdf:
        ruta, motivo = descargar(rec, oa, carpeta)
        rec["pdf_path"], rec["download_note"] = ruta, motivo
    return rec


# ===================================================================== Main
def main():
    ap = argparse.ArgumentParser(description="Busqueda de la vigilancia en TO")
    ap.add_argument("--dias", type=int, help="buscar lo publicado en los ultimos N dias")
    ap.add_argument("--desde", help="buscar desde esta fecha (AAAA-MM-DD)")
    ap.add_argument("--bases", action="store_true", help="lista las bases disponibles")
    args = ap.parse_args()
    if args.bases:
        for k, b in BASES.items():
            c = {None: "gratuita, sin clave", "opcional": "gratuita, clave opcional",
                 "obligatoria": "necesita clave"}[b["clave"]]
            print(f"{k:16} {b['nombre']:17} {c}{'  (activa por defecto)' if b['defecto'] else ''}")
        return

    perfil = cargar_perfil()
    r = rutas(perfil)
    email = perfil["email_apis"]
    fuentes = perfil.get("fuentes") or {}
    activa = lambda k: fuentes.get(k, BASES[k]["defecto"])  # noqa: E731
    claves = {}
    for k, b in BASES.items():
        if activa(k) and b["clave"]:
            claves[k] = clave_de(k)
            if b["clave"] == "obligatoria" and not claves[k]:
                print(f"  - {b['nombre']} está activada pero no tiene clave en claves.json: "
                      "se salta.")

    if args.desde:
        desde = args.desde
    else:
        dias = args.dias or int(perfil.get("periodo_dias") or 30)
        desde = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
    print(f"Buscando lo publicado desde {desde}")

    ambitos = perfil["ambitos"]
    filtro = perfil.get("filtro_comun") or {}
    filtro_en, filtro_es = filtro.get("terminos_en") or [], \
        (filtro.get("terminos_es") or []) + (filtro.get("terminos_pt") or [])
    anclas_es = sorted(set(ANCLAS_TO["es"] + ANCLAS_TO["pt"]))
    crudos, por_fuente = [], Counter()

    def add(nombre, recs):
        if recs:
            por_fuente[nombre] += len(recs)
            crudos.extend(recs)

    for a in ambitos:
        print(f"[{a['nombre']}]")
        g_en = [ANCLAS_TO["en"], a["terminos_en"], filtro_en]
        tope = 100
        if activa("pubmed"):
            add("PubMed", src_pubmed(g_en, desde, tope)); time.sleep(0.4)
        if activa("europepmc"):
            add("Europe PMC", src_europepmc(g_en, desde, tope)); time.sleep(0.3)
        if activa("openalex"):
            add("OpenAlex", src_openalex(g_en, desde, tope, email)); time.sleep(0.3)
            t_es = (a.get("terminos_es") or []) + (a.get("terminos_pt") or [])
            if t_es:
                add("OpenAlex (es/pt)", src_openalex([anclas_es, t_es, filtro_es or None],
                                                     desde, tope, email))
                time.sleep(0.3)
        if activa("crossref"):
            add("Crossref", src_crossref(g_en, desde, 60, email)); time.sleep(0.3)
        if activa("semanticscholar"):
            add("Semantic Scholar", src_semanticscholar(g_en, desde, tope,
                                                        claves.get("semanticscholar")))
            time.sleep(1.2)            # sin clave, Semantic Scholar pide calma
        if activa("arxiv"):
            add("arXiv", src_arxiv(g_en, desde, 30)); time.sleep(0.5)
        if activa("doaj"):
            add("DOAJ", src_doaj(g_en, desde, 30)); time.sleep(0.3)
        for k, fn in (("scopus", src_scopus), ("wos", src_wos), ("ieee", src_ieee),
                      ("consensus", src_consensus)):
            if activa(k) and claves.get(k):
                add(BASES[k]["nombre"], fn(g_en, desde, 25, claves[k]))
                time.sleep(0.5)

    print("\nResultados crudos por fuente:")
    for k, v in por_fuente.most_common():
        print(f"  {k:18} {v}")
    print(f"  {'TOTAL':18} {len(crudos)}")
    alertas = [f"{k} no ha devuelto nada: puede estar caida o haber cambiado su API."
               for k in ("PubMed", "Europe PMC", "OpenAlex", "Crossref")
               if activa(k.lower().replace(" ", "")) and not por_fuente.get(k)]

    # Puerta de relevancia
    anclas = ANCLAS_TO["en"] + anclas_es
    terminos = [t for a in ambitos for k in ("terminos_en", "terminos_es", "terminos_pt")
                for t in (a.get(k) or [])]
    comun = filtro_en + filtro_es
    con_tema = [x for x in crudos if x.get("title") and relevante(x, anclas, terminos, comun)]
    print(f"Pasan la puerta de relevancia (TO + ámbito en título o resumen): {len(con_tema)}")

    def en_plazo(x):
        f = (x.get("fecha") or x.get("year") or "")[:10]
        return not f or (f >= desde[:4] if len(f) == 4 else f >= desde)
    con_tema = [x for x in con_tema if en_plazo(x)]

    # Deduplicar fusionando las copias, y quitar lo ya publicado o descartado
    vistos = cargar_vistos(r["datos"])
    v_doi = set(norm_doi(d) for d in vistos["dois"] if d)
    v_pmid, v_tit = set(vistos["pmids"]), set(vistos["titulos"])
    idx_doi, idx_pmid, idx_tit, unicos, fusiones, repetidos = {}, {}, {}, [], 0, 0
    for x in sorted(con_tema, key=lambda y: (y.get("fecha") or y.get("year") or ""), reverse=True):
        doi, pmid, nt = x.get("doi"), x.get("pmid"), norm_title(x.get("title"))
        if (doi and doi in v_doi) or (pmid and pmid in v_pmid) or (nt and nt in v_tit):
            repetidos += 1
            continue
        previo = (idx_doi.get(doi) if doi else None) or (idx_pmid.get(pmid) if pmid else None) \
            or (idx_tit.get(nt) if nt else None)
        if previo is not None:
            enriquecer(previo, x)
            fusiones += 1
            continue
        for idx, k in ((idx_doi, doi), (idx_pmid, pmid), (idx_tit, nt)):
            if k:
                idx[k] = x
        unicos.append(x)
    for x in unicos:
        x["categoria"] = ambito_de(x, ambitos)
    print(f"Únicos: {len(unicos)} ({fusiones} duplicados fusionados, "
          f"{repetidos} ya publicados o descartados antes)")

    # Sin resumen no hay ficha posible
    sin_resumen = [x for x in unicos if not (x.get("abstract") or "").strip()]
    unicos = [x for x in unicos if (x.get("abstract") or "").strip()]
    if sin_resumen:
        print(f"Apartados por no traer resumen: {len(sin_resumen)}")

    n = perfil["n_articulos"]
    n_supl = int(perfil.get("n_suplentes") or max(3, n // 2))
    tope_ambito = max(2, -(-n * 2 // max(1, len(ambitos))))   # el doble del reparto justo
    candidatos, resto = seleccionar(unicos, n, tope_ambito)
    suplentes = resto[:n_supl]
    print(f"Titulares: {len(candidatos)} de {n} pedidos. Suplentes: {len(suplentes)}. "
          f"En cola: {len(resto)}.")
    for c, k in Counter(x["categoria"] for x in candidatos).most_common():
        print(f"    {c}: {k}")

    tablas = cargar_sjr(r["datos"])
    if tablas:
        print(f"Cuartiles SJR puestos: {aplicar_sjr(tablas, candidatos + suplentes)}")

    descargar_pdf = bool(perfil.get("descargar_pdf"))
    resultados = []
    for m in candidatos:
        resultados.append(resolver_acceso(m, email, descargar_pdf, r["articulos"]))
        time.sleep(0.3)
    suplentes_out = []
    for m in suplentes:
        rec = resolver_acceso(m, email, False, r["articulos"])
        rec["es_suplente"] = True
        suplentes_out.append(rec)
        time.sleep(0.2)

    n_oa = sum(1 for x in resultados if x["is_oa"])
    n_desc = sum(1 for x in resultados if x["pdf_path"])
    fallos = [{"title": x.get("title"), "enlace": x.get("oa_landing") or x.get("editor_url"),
               "motivo": x["download_note"]} for x in resultados if x.get("download_note")]
    print(f"\nAcceso abierto: {n_oa} de {len(resultados)}"
          + (f" | PDF descargados: {n_desc} | no se pudieron bajar: {len(fallos)}"
             if descargar_pdf else " | descarga de PDF desactivada en el perfil"))
    for a in alertas:
        print(f"  ! {a}")

    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    salida = os.path.join(r["volcados"], f"volcado_{stamp}.json")
    escribir_json(salida, {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "buscado_desde": desde,
        "fuentes_consultadas": dict(por_fuente),
        "alertas_fuentes": alertas,
        "en_cola": len(resto),
        "total_filtrados": len(unicos),
        "resumen_acceso": {"abiertos": n_oa, "descargados": n_desc,
                           "descargas_fallidas": len(fallos)},
        "descargas_fallidas": fallos,
        "articles": resultados,
        "suplentes": suplentes_out,
    })
    # Aqui NO se marca nada como publicado: lo hace generar.py, y solo con lo
    # que sale de verdad en el boletin.
    print(salida)


if __name__ == "__main__":
    main()
