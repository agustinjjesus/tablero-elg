"""Arma site/datos.json a partir de los números leídos de Meta.

Uso: py scripts/armar_datos.py lectura.json

lectura.json tiene, por período, la lista de anuncios con gasto:
  {"actualizado": "2026-11-06T18:40:00Z",
   "periodos": {"maximum": [["c1", "id", "anuncio", "campaña", "ACTIVE", 17.85, 1, 17.85], ...], ...}}
Cada fila: clave de cuenta, id del anuncio, nombre, campaña, estado, gasto, compras, costo por compra (o null).
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
    datos = {
        "estado": "ok",
        "actualizado": lectura["actualizado"],
        "cuentas": [{"clave": c, "nombre": n} for c, n in NOMBRES.items()],
        "errores": lectura.get("errores", []),
        "periodos": periodos,
    }
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    resumen = {p: (len(f), round(sum(r["gasto"] for r in f), 2)) for p, f in periodos.items()}
    print("anuncios y gasto por período:", resumen)


if __name__ == "__main__":
    main()
