"""Arma site/datos.json a partir de las respuestas de Meta tal como vienen del conector "ads".

Uso: py scripts/armar_desde_meta.py meta.json

meta.json (las listas son las de "ad_entities" o "ad_creatives", copiadas tal cual):
{
  "hoy": "2026-11-06",                       # fecha de hoy en las cuentas
  "anuncios": {"c1": {"today": [...], "yesterday": [...], "last_7d": [...], "last_30d": [...], "maximum": [...]}, ...},
  "diario":   {"c1": [...], ...},            # nivel cuenta, time_increment 1 (date_start, omni_purchase, amount_spent)
  "estados":  {"c1": [...], ...},            # todos los anuncios: id, name, campaign_name, effective_status, creative_id
  "creativos": [...]                         # opcional: ads_get_creatives de creativos nuevos (id, object_type, video_id)
}
Las claves de cuenta son c1, c2, c3 y cb (ComboBiotina).
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "site" / "datos.json"
VIDEOS = RAIZ / "scripts" / "videos.json"
PERIODOS = ["today", "yesterday", "last_7d", "last_30d", "maximum"]
NOMBRES = {"c1": "Cuenta 1", "c2": "Cuenta 2", "c3": "Cuenta 3", "cb": "ComboBiotina"}


def lista(x):
    """Acepta la lista sola, la respuesta entera del conector o la lista como texto JSON."""
    if x is None:
        return []
    if isinstance(x, str):
        x = json.loads(x)
    if isinstance(x, dict):
        for k in ("ad_entities", "ad_creatives", "data"):
            if k in x:
                return lista(x[k])
        return []
    return list(x)


def monto(v):
    if isinstance(v, dict):
        v = v.get("value")
    try:
        return round(float(v or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def entero(v):
    try:
        return int(float(v or 0))
    except (TypeError, ValueError):
        return 0


def main():
    meta = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    videos = json.loads(VIDEOS.read_text(encoding="utf-8"))
    videos.setdefault("porAnuncio", {})

    # Estados, rechazados y problemas, a partir de la lista completa de anuncios.
    estado, nombre_ad, campana_ad, creativo_ad = {}, {}, {}, {}
    rechazados, problemas = [], []
    for clave, filas in meta.get("estados", {}).items():
        for a in lista(filas):
            aid = str(a.get("id"))
            estado[aid] = a.get("effective_status", "")
            nombre_ad[aid] = a.get("name", "")
            campana_ad[aid] = a.get("campaign_name", "")
            if a.get("creative_id"):
                creativo_ad[aid] = str(a["creative_id"])
            fila = {"clave": clave, "id": aid, "anuncio": a.get("name", ""), "campana": a.get("campaign_name", "")}
            if estado[aid] == "DISAPPROVED":
                rechazados.append(fila)
            elif estado[aid] == "WITH_ISSUES":
                problemas.append(fila)

    # Creativos nuevos: qué video usan.
    for c in lista(meta.get("creativos")):
        cid = str(c.get("id"))
        if cid in videos["porCreativo"]:
            continue
        vid = str(c.get("video_id") or "")
        if vid and vid in videos["porVideoId"]:
            videos["porCreativo"][cid] = videos["porVideoId"][vid]
        elif c.get("object_type") == "POST_DELETED":
            videos["porCreativo"][cid] = "borrado-" + cid
            videos["nombres"]["borrado-" + cid] = "Video con publicación borrada"
        elif vid:
            videos["porCreativo"][cid] = "vid-" + vid
            videos["porVideoId"][vid] = "vid-" + vid

    def video_de(aid, nombre):
        cid = creativo_ad.get(aid)
        k = videos["porCreativo"].get(cid) if cid else None
        if not k:
            k = videos["porAnuncio"].get(aid)
        if not k:
            m = re.fullmatch(r"\s*(\d{1,3})\s*", nombre or "")
            k = "v" + m.group(1) if m else "a" + aid
        if k not in videos["nombres"]:
            m = re.fullmatch(r"v(\d{1,3})", k)
            videos["nombres"][k] = m.group(1) if m else (nombre or k)
        videos["porAnuncio"][aid] = k
        return k

    # Anuncios con gasto, por período.
    periodos = {p: [] for p in PERIODOS}
    anuncios_video = {}
    for clave, por_periodo in meta.get("anuncios", {}).items():
        for p in PERIODOS:
            for a in lista(por_periodo.get(p)):
                gasto = monto(a.get("amount_spent"))
                if gasto <= 0:
                    continue
                aid = str(a.get("id"))
                compras = entero(a.get("omni_purchase"))
                cpa = monto(a.get("cost_per_omni_purchase")) if a.get("cost_per_omni_purchase") else None
                if cpa is None and compras:
                    cpa = round(gasto / compras, 2)
                nombre = a.get("name", nombre_ad.get(aid, ""))
                anuncios_video[aid] = video_de(aid, nombre)
                periodos[p].append({
                    "id": aid,
                    "clave": clave,
                    "cuenta": NOMBRES.get(clave, clave),
                    "campana": a.get("campaign_name", campana_ad.get(aid, "")),
                    "anuncio": nombre,
                    "estado": estado.get(aid, a.get("effective_status", "")),
                    "gasto": gasto,
                    "compras": compras,
                    "cpa": cpa if compras else None,
                })

    # Totales diarios de cada cuenta completa.
    diario = []
    for clave, filas in meta.get("diario", {}).items():
        for d in lista(filas):
            compras = entero(d.get("omni_purchase"))
            gasto = monto(d.get("amount_spent"))
            if compras or gasto:
                diario.append({"clave": clave, "fecha": d.get("date_start"), "compras": compras, "gasto": gasto})
    diario.sort(key=lambda r: (r["fecha"], r["clave"]))

    if not any(periodos.values()) and not diario:
        print("No llegó ningún número de Meta: no se cambia la página.")
        sys.exit(1)

    VIDEOS.write_text(json.dumps(videos, ensure_ascii=False, indent=1), encoding="utf-8")
    datos = {
        "estado": "ok",
        "actualizado": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "hoy": meta.get("hoy") or (diario[-1]["fecha"] if diario else None),
        "cuentas": [{"clave": c, "nombre": n} for c, n in NOMBRES.items()],
        "errores": meta.get("errores", []),
        "periodos": periodos,
        "diario": diario,
        "videos": {"nombres": videos["nombres"], "anuncios": anuncios_video},
        "rechazados": rechazados,
        "problemas": problemas,
    }
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print("anuncios por período:", {p: len(f) for p, f in periodos.items()})
    print("días:", len(diario), "| clientes:", sum(r["compras"] for r in diario),
          "| gasto:", round(sum(r["gasto"] for r in diario), 2),
          "| rechazados:", len(rechazados), "| con problemas:", len(problemas))


if __name__ == "__main__":
    main()
