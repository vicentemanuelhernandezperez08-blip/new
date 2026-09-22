"""Búsqueda de productos: CSV de ejemplo o base Firebird de Eleventa (solo lectura)."""
import csv
import time
import unicodedata

import config

_cache = {"ts": 0, "rows": []}
CACHE_SECONDS = 300  # recarga el catálogo cada 5 min


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.lower().strip()


def _load_csv():
    with open(config.CATALOG_CSV, newline="", encoding="utf-8") as f:
        return [
            {"codigo": r["codigo"], "nombre": r["nombre"],
             "precio": float(r["precio"]), "existencia": float(r["existencia"])}
            for r in csv.DictReader(f)
        ]


def _load_firebird():
    from firebird.driver import connect  # pip install firebird-driver

    sql = (f"SELECT {config.FB_COL_CODE}, {config.FB_COL_NAME}, {config.FB_COL_PRICE}, "
           f"{config.FB_COL_STOCK} FROM {config.FB_TABLE}")
    with connect(config.FB_DSN, user=config.FB_USER, password=config.FB_PASSWORD,
                 charset="ISO8859_1") as con:
        cur = con.cursor()
        cur.execute(sql)
        return [
            {"codigo": str(c).strip(), "nombre": str(n).strip(),
             "precio": float(p or 0), "existencia": float(s or 0)}
            for c, n, p, s in cur.fetchall()
        ]


def _rows():
    if time.time() - _cache["ts"] > CACHE_SECONDS or not _cache["rows"]:
        loader = _load_firebird if config.CATALOG_SOURCE == "firebird" else _load_csv
        try:
            _cache["rows"] = loader()
            _cache["ts"] = time.time()
        except Exception as e:  # si falla, sigue con el caché anterior
            print("[catalog] error cargando catálogo:", e)
    return _cache["rows"]


def search(query: str, limit: int = 8):
    """Busca por palabras: todas deben aparecer en el nombre o código."""
    words = _norm(query).split()
    if not words:
        return []
    hits = []
    for r in _rows():
        text = _norm(r["nombre"] + " " + r["codigo"])
        if all(w in text for w in words):
            hits.append(r)
    if not hits:  # segunda pasada: cualquier palabra
        for r in _rows():
            text = _norm(r["nombre"])
            score = sum(w in text for w in words)
            if score:
                hits.append({**r, "_s": score})
        hits.sort(key=lambda r: -r["_s"])
    return [
        {"codigo": r["codigo"], "nombre": r["nombre"], "precio": r["precio"],
         "disponible": r["existencia"] > 0}
        for r in hits[:limit]
    ]


def get(codigo: str):
    for r in _rows():
        if r["codigo"] == str(codigo):
            return r
    return None
