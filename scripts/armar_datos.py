"""Arma site/datos.json a partir de los números leídos de Meta.

Uso: py scripts/armar_datos.py lectura.json

lectura.json tiene, por período, la lista de anuncios con gasto, y los totales por día de cada cuenta:
  {"actualizado": "2026-11-06T18:40:00Z", "hoy": "2026-11-06",
   "periodos": {"maximum": [["c1", "id", "anuncio", "campaña", "ACTIVE", 17.85, 1, 17.85], ...], ...},
   "diario": [["c1", "2026-11-05", 5, 144.44], ...]}
Fila de anuncio: clave de cuenta, id, nombre, campaña, estado, gasto, compras, costo por compra (o null).
Fila diaria: clave de cuenta, fecha, compras, gasto (de la cuenta entera, nivel cuenta con time_increment 1).
Opcionales: "videos": {"nombres": {clave_video: nombre}, "anuncios": {id_anuncio: clave_video}},
"rechazados" y "problemas": [[clave de cuenta, id, anuncio, campaña], ...].
"""

import json
import sys
from pathlib import Path

PERIODOS = ["today", "yesterday", "last_7d", "last_30d", "maximum"]
NOMBRES = {"c1": "Cuenta 1", "c2": "Cuenta 2", "c3": "Cuenta 3", "cb": "ComboBiotina"}
SALIDA = Path(__file__).resolve().parent.parent / "site" / "datos.json"


def main():
    lectura = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    periodos = {}
    for p in PERIODOS:
        filas = []
        for clave, aid, anuncio, campana, estado, gasto, compras, cpa in lectura["periodos"].get(p, []):
            gasto = round(float(gasto or 0), 2)
            compras = int(compras or 0)
            if gasto <= 0:
                continue
            filas.append({
                "id": str(aid),
                "clave": clave,
                "cuenta": NOMBRES[clave],
                "campana": campana,
                "anuncio": anuncio,
                "estado": estado,
                "gasto": gasto,
                "compras": compras,
                "cpa": round(float(cpa), 2) if (cpa is not None and compras) else None,
            })
        periodos[p] = filas
    # Totales por día de cada cuenta completa (incluyen anuncios borrados, que no salen en la lista por anuncio).
    diario = []
    for clave, fecha, compras, gasto in lectura.get("diario", []):
        compras = int(compras or 0)
        gasto = round(float(gasto or 0), 2)
        if compras or gasto:
            diario.append({"clave": clave, "fecha": fecha, "compras": compras, "gasto": gasto})
    diario.sort(key=lambda r: (r["fecha"], r["clave"]))
    datos = {
        "estado": "ok",
        "actualizado": lectura["actualizado"],
        "hoy": lectura.get("hoy"),
        "cuentas": [{"clave": c, "nombre": n} for c, n in NOMBRES.items()],
        "errores": lectura.get("errores", []),
        "periodos": periodos,
        "diario": diario,
        # Qué video usa cada anuncio (sale del video de su creativo), para el ranking por video.
        "videos": lectura.get("videos", {"nombres": {}, "anuncios": {}}),
        # Anuncios rechazados por Meta y con problemas de entrega: [clave, id, anuncio, campaña].
        "rechazados": [dict(zip(("clave", "id", "anuncio", "campana"), r)) for r in lectura.get("rechazados", [])],
        "problemas": [dict(zip(("clave", "id", "anuncio", "campana"), r)) for r in lectura.get("problemas", [])],
    }
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    resumen = {p: (len(f), round(sum(r["gasto"] for r in f), 2)) for p, f in periodos.items()}
    print("anuncios y gasto por período:", resumen)
    print("días:", len(diario), "| compras:", sum(r["compras"] for r in diario), "| gasto:", round(sum(r["gasto"] for r in diario), 2))


if __name__ == "__main__":
    main()
