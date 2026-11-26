"""Recolector del Brief fintech (versión gratuita, sin IA).

Lee feeds RSS de fuentes confiables y búsquedas de Google Noticias,
filtra por palabras clave, elimina duplicados y guarda docs/data/noticias.json.
"""
import calendar
import hashlib
import html
import json
import re
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote_plus

import feedparser

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "docs" / "data" / "noticias.json"
CONF = json.loads((RAIZ / "recolector" / "fuentes.json").read_text(encoding="utf-8"))
UA = "Mozilla/5.0 (compatible; BriefFintechBot/1.0)"
CATEGORIAS = {"reg", "emp", "ux", "ten"}
VALIDAS = CATEGORIAS | {"auto"}
socket.setdefaulttimeout(20)


def url_google(q, idioma):
    q = quote_plus(f"{q} when:{CONF['dias']}d")
    if idioma == "es":
        return f"https://news.google.com/rss/search?q={q}&hl=es-419&gl=AR&ceid=AR:es-419"
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def limpiar(texto, largo=200):
    texto = html.unescape(re.sub(r"<[^>]+>", " ", texto or ""))
    texto = re.sub(r"\s+", " ", texto).strip()
    if len(texto) > largo:
        texto = texto[:largo].rsplit(" ", 1)[0] + "…"
    return texto


def clave_titulo(t):
    return re.sub(r"[^a-z0-9áéíóúñü]", "", t.lower())[:80]


def fecha_de(entry):
    for campo in ("published_parsed", "updated_parsed"):
        v = entry.get(campo)
        if v:
            return datetime.fromtimestamp(calendar.timegm(v), tz=timezone.utc)
    return None


ENLACE_RE = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>(?:\s|&nbsp;)*(?:<font[^>]*>(.*?)</font>)?', re.S | re.I)


def dominio(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).lower().removeprefix("www.") if m else ""


def es_oficial(url):
    d = dominio(url)
    return any(d == o or d.endswith("." + o) for o in CONF.get("dominios_oficiales", []))


def enlaces_en_html(texto):
    """Pares (url, título, medio) de los enlaces dentro del HTML de un feed."""
    out = []
    for href, tit, medio in ENLACE_RE.findall(texto or ""):
        href = html.unescape(href)
        if href.startswith("http"):
            out.append((href, limpiar(tit, 140), limpiar(medio or "", 60)))
    return out


def categorizar(texto):
    """Para fuentes con "categoria": "auto" (bancos, fintech, proveedores): asigna el tema por palabras clave."""
    t = f" {texto.lower()} "
    for regla in CONF.get("reglas_categoria", []):
        if any(p in t for p in regla["palabras"]):
            return regla["categoria"]
    return CONF.get("categoria_por_defecto", "emp")


def palabras(t):
    return {w for w in re.findall(r"[a-z0-9áéíóúñü]+", t.lower()) if len(w) > 3}


def misma_noticia(a, b):
    if a["categoria"] != b["categoria"]:
        return False
    pa, pb = palabras(a["titulo"]), palabras(b["titulo"])
    if not pa or not pb:
        return False
    return len(pa & pb) / len(pa | pb) >= 0.6


def sumar_enlaces(destino, nuevos):
    urls = {e["url"] for e in destino["enlaces"]}
    for e in nuevos:
        if e["url"] not in urls and len(destino["enlaces"]) < 6:
            destino["enlaces"].append(e)
            urls.add(e["url"])


def leer_fuente(f, desde):
    url = url_google(f["q"], f.get("idioma", "es")) if f["tipo"] == "google" else f["url"]
    feed = feedparser.parse(url, agent=UA)
    if feed.bozo and not feed.entries:
        raise RuntimeError(str(feed.get("bozo_exception", "feed inválido")))
    filtro = f.get("filtro", [])
    if isinstance(filtro, str):
        filtro = CONF.get(filtro, [])
    filtro = [p.lower() for p in filtro]
    excluir = [p.lower() for p in CONF.get("excluir", [])]
    items = []
    for e in feed.entries:
        fecha = fecha_de(e)
        if not fecha or fecha < desde:
            continue
        titulo = limpiar(e.get("title", ""), 220)
        link = e.get("link", "")
        if not titulo or not link.startswith("http"):
            continue
        fuente = f["nombre"]
        resumen = ""
        enlaces = []
        if f["tipo"] == "google":
            # Google Noticias agrega " - Medio" al título; el medio real va en <source>.
            medio = (e.get("source") or {}).get("title", "")
            if medio and titulo.endswith(" - " + medio):
                titulo = titulo[: -len(medio) - 3]
            fuente = medio or "Google Noticias"
            enlaces.append({"nombre": fuente, "url": link, "tipo": "nota"})
            # Cuando varios medios cubren la misma noticia, Google los lista en la descripción.
            for href, _tit, otro in enlaces_en_html(e.get("summary", ""))[1:4]:
                if otro and otro != fuente:
                    enlaces.append({"nombre": otro, "url": href, "tipo": "cobertura"})
        else:
            resumen = limpiar(e.get("summary", ""))
            enlaces.append({"nombre": fuente, "url": link, "tipo": "nota"})
            # Documentos oficiales citados dentro de la nota (BCRA, CISA, Apple, etc.).
            cuerpo = e.get("summary", "") + "".join(c.get("value", "") for c in e.get("content", []))
            for href, tit, _m in enlaces_en_html(cuerpo):
                if es_oficial(href) and len(enlaces) < 4:
                    enlaces.append({"nombre": tit or dominio(href), "url": href, "tipo": "oficial"})
        texto = f" {titulo} {resumen} ".lower()
        if any(p in texto for p in excluir):
            continue
        if filtro:
            if not any(p in texto for p in filtro):
                continue
        categoria = f["categoria"]
        if categoria == "auto":
            categoria = categorizar(f"{titulo} {resumen}")
        items.append({
            "id": hashlib.sha1(link.encode()).hexdigest()[:12],
            "categoria": categoria,
            "fecha": fecha.isoformat(timespec="minutes"),
            "titulo": titulo,
            "resumen": resumen,
            "fuente": fuente,
            "url": link,
            "enlaces": enlaces,
            "region": "ar" if (f.get("region") == "ar" or dominio(link).endswith(".ar")) else "global",
        })
    return items


def main():
    ahora = datetime.now(timezone.utc)
    desde = ahora - timedelta(days=CONF["dias"])

    anteriores = []
    if SALIDA.exists():
        try:
            anteriores = json.loads(SALIDA.read_text(encoding="utf-8")).get("noticias", [])
        except Exception:
            pass

    nuevas, estado = [], []
    for f in CONF["fuentes"]:
        if f.get("categoria") not in VALIDAS:
            continue
        try:
            items = leer_fuente(f, desde)
            nuevas += items
            estado.append({"fuente": f["nombre"], "ok": True, "noticias": len(items)})
        except Exception as ex:
            estado.append({"fuente": f["nombre"], "ok": False, "error": str(ex)[:160]})
            print(f"Falló {f['nombre']}: {ex}")

    # Se conservan las anteriores dentro de la ventana, así no desaparecen si un feed rota.
    # Si varias fuentes publican la misma noticia, se unifica y se suman sus enlaces.
    final = []
    excluir = [p.lower() for p in CONF.get("excluir", [])]
    for n in nuevas + anteriores:
        if any(p in f" {n.get('titulo','')} {n.get('resumen','')} ".lower() for p in excluir):
            continue
        try:
            if datetime.fromisoformat(n["fecha"]) < desde:
                continue
        except Exception:
            continue
        n.setdefault("enlaces", [{"nombre": n["fuente"], "url": n["url"], "tipo": "nota"}])
        kt = clave_titulo(n["titulo"])
        igual = next((x for x in final if x["url"] == n["url"] or clave_titulo(x["titulo"]) == kt
                      or misma_noticia(x, n)), None)
        n.setdefault("region", "global")
        if igual:
            sumar_enlaces(igual, n["enlaces"])
            if n["region"] == "ar":
                igual["region"] = "ar"
            if not igual.get("resumen") and n.get("resumen"):
                igual["resumen"] = n["resumen"]
            continue
        final.append(n)

    final.sort(key=lambda n: n["fecha"], reverse=True)
    por_cat, recortado = {}, []
    for n in final:
        por_cat[n["categoria"]] = por_cat.get(n["categoria"], 0) + 1
        if por_cat[n["categoria"]] <= CONF["max_por_categoria"]:
            recortado.append(n)

    if not recortado and anteriores:
        print("No se obtuvo ninguna noticia; se mantiene la versión anterior.")
        return

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps({
        "actualizado": ahora.isoformat(timespec="minutes"),
        "noticias": recortado,
        "estado": estado,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for e in estado if e["ok"])
    print(f"{len(recortado)} noticias. Fuentes OK: {ok}/{len(estado)}")


if __name__ == "__main__":
    main()
