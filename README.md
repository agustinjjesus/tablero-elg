# Tablero ELG

Página con el gasto y el costo por compra (CPA) de los anuncios de las cuatro cuentas de Meta.

- `site/index.html`: la página.
- `scripts/traer_datos.py`: trae los números de Meta y los guarda en `site/datos.json`.
- `.github/workflows/actualizar.yml`: corre el script cada 30 minutos y publica la página en GitHub Pages.

## Secretos del repositorio

En Settings → Secrets and variables → Actions:

- `META_TOKEN`: clave de Meta de solo lectura (permiso `ads_read` sobre las cuatro cuentas).
- `META_CUENTAS`: las cuentas, así: `c1:ID,c2:ID,c3:ID,cb:ID`.

Sin la clave, la página muestra que falta conectar Meta.
