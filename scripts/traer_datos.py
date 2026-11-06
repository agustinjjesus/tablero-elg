"""Trae de Meta el gasto, las compras y el costo por compra de cada anuncio y los guarda en site/datos.json.

Lo corre GitHub Actions cada 30 minutos. Necesita dos secretos del repositorio:
  META_TOKEN    clave de Meta de solo lectura (permiso ads_read sobre las cuentas)
  META_CUENTAS  las cuentas, así: c1:123456,c2:789012,c3:345678,cb:901234
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

VERSION = os.environ.get("META_API_VERSION", "v23.0")
PERIODOS = ["today", "yesterday", "last_7d", "last_30d", "maximum"]
NOMBRES = {"c1": "Cuenta 1", "c2": "Cuenta 2", "c3": "Cuenta 3", "cb": "ComboBiotina"}
TIPOS_COMPRA = ("omni_purchase", "purchase", "offsite_conversion.fb_pixel_purchase")
SALIDA = Path(__file__).resolve().parent.parent / "site" / "datos.json"


def pedir(url, params=None):
    """GET a la API de Meta con hasta 3 intentos. Nunca imprime la clave."""
    full = url + ("?" + urllib.parse.urlencode(params) if params else "")
    for intento in range(3):
        try:
            with urllib.request.urlopen(full, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", "replace")
            try:
                msg = json.loads(cuerpo).get("error", {}).get("message", "sin detalle")
            except ValueError:
                msg = "sin detalle"
            if e.code >= 500 and intento < 2:
                time.sleep(5)
                continue
            raise RuntimeError(f"Meta respondió {e.code}: {msg}") from None
        except urllib.error.URLError as e:
            if intento < 2:
                time.sleep(5)
                continue
            raise RuntimeError(f"No se pudo conectar con Meta: {e.reason}") from None


def todas(path, params):
    """Junta todas las páginas de una consulta."""
    datos = pedir(f"https://graph.facebook.com/{VERSION}/{path}", params)
    filas = list(datos.get("data", []))
    while datos.get("paging", {}).get("next"):
        datos = pedir(datos["paging"]["next"])
        filas += datos.get("data", [])
    return filas


def valor(lista, tipos):
    for tipo in tipos:
        for a in lista or []:
            if a.get("action_type") == tipo:
                return float(a.get("value") or 0)
    return None


def leer_cuentas(texto):
    cuentas = []
    for parte in (texto or "").replace("\n", ",").split(","):
        parte = parte.strip()
        if not parte:
            continue
        clave, _, cid = parte.partition(":")
        cid = cid.strip().removeprefix("act_")
        if clave.strip() and cid.isdigit():
            cuentas.append((clave.strip(), cid))
    return cuentas


def filas_de(clave, cid, token):
    estados = {
        a["id"]: a.get("effective_status", "")
        for a in todas(f"act_{cid}/ads", {"fields": "id,effective_status", "limit": 500, "access_token": token})
    }
    por_periodo = {}
    for periodo in PERIODOS:
        filas = todas(
            f"act_{cid}/insights",
            {
                "level": "ad",
                "fields": "ad_id,ad_name,campaign_name,spend,actions,cost_per_action_type",
                "date_preset": periodo,
                "limit": 500,
                "access_token": token,
            },
        )
        salida = []
        for f in filas:
            gasto = round(float(f.get("spend") or 0), 2)
            compras = int(valor(f.get("actions"), TIPOS_COMPRA) or 0)
            cpa = valor(f.get("cost_per_action_type"), TIPOS_COMPRA)
            if cpa is None and compras:
                cpa = gasto / compras
            salida.append({
                "id": str(f.get("ad_id", "")),
                "clave": clave,
                "cuenta": NOMBRES.get(clave, clave),
                "campana": f.get("campaign_name", ""),
                "anuncio": f.get("ad_name", ""),
                "estado": estados.get(f.get("ad_id"), ""),
                "gasto": gasto,
                "compras": compras,
                "cpa": round(cpa, 2) if (cpa is not None and compras) else None,
            })
        por_periodo[periodo] = salida
    return por_periodo


def guardar(datos):
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    token = os.environ.get("META_TOKEN", "").strip()
    cuentas = leer_cuentas(os.environ.get("META_CUENTAS", ""))
    if not token or not cuentas:
        print("Falta META_TOKEN o META_CUENTAS: la página muestra que falta conectar Meta.")
        guardar({"estado": "sin_clave", "actualizado": None, "cuentas": [], "errores": []})
        return

    resultado = {
        "estado": "ok",
        "actualizado": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "cuentas": [{"clave": c, "nombre": NOMBRES.get(c, c)} for c, _ in cuentas],
        "errores": [],
        "periodos": {p: [] for p in PERIODOS},
    }
    for clave, cid in cuentas:
        try:
            for periodo, filas in filas_de(clave, cid, token).items():
                resultado["periodos"][periodo] += filas
            print(f"{NOMBRES.get(clave, clave)}: ok")
        except Exception as e:  # una cuenta que falla no frena a las demás
            msg = str(e).replace(token, "***")[:300]
            resultado["errores"].append({"clave": clave, "cuenta": NOMBRES.get(clave, clave), "mensaje": msg})
            print(f"{NOMBRES.get(clave, clave)}: {msg}")

    if len(resultado["errores"]) == len(cuentas):
        print("No se pudo leer ninguna cuenta: se deja publicada la versión anterior.")
        sys.exit(1)
    guardar(resultado)


if __name__ == "__main__":
    main()
