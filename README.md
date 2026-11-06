# Tablero ELG

Página con el gasto y el costo por compra (CPA) de los anuncios de las cuatro cuentas de Meta.

- `site/index.html`: la página.
- `site/datos.json`: los números que muestra.
- `scripts/armar_datos.py`: arma `site/datos.json` a partir de una lectura de Meta.
- `.github/workflows/actualizar.yml`: publica la página en GitHub Pages cada vez que se sube un cambio.

Los números se actualizan a pedido: se leen de Meta, se arma `datos.json` y se sube al repositorio.
