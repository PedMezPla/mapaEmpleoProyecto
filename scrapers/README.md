# Scrapers para empleo España

Esta carpeta contiene el esqueleto de los scrapers y el flujo de exportación que puede ejecutar un GitHub Action.

## Objetivo
- Extraer ofertas de los portales principales.
- Normalizar datos en un JSON único.
- Publicar el JSON en GitHub Pages cada madrugada y a mediodía.

## Estructura
- `infojobs_scraper.py` — scraper específico para InfoJobs con extracción de título, empresa, ubicación, categoría y tipo.
- `generic_scraper.py` — plantilla para portar otros portales.
- `export_json.py` — une y normaliza múltiples archivos JSON en un único `jobs.json` y genera `communities.json` + `jobs/<slug>.json`.
- `requirements.txt` — dependencias básicas.

## Esquema recomendado de salida
Cada oferta debe incluir al menos:
- `id` — identificador único
- `title`
- `company`
- `location`
- `province`
- `community`
- `category`
- `type`
- `portal`
- `status` — por ejemplo, `active`, `expired`
- `lat`, `lng`
- `url`
- `updated_at`

## Notas de diseño
- El scraper no debe depender solo de HTML estático: si el portal usa JavaScript, hay que usar API interna o headless.
- Para SEO, el JSON alimenta la app, pero se recomienda también generar páginas estáticas por comunidad/sector.
- Con millones de ofertas, se debe mantener un pipeline de deduplicación y expiración.

## Recomendación de portales
- InfoJobs
- Indeed
- LinkedIn (si es viable y legal)
- Trabajos.com / Jobandtalent / Tecnoempleo

## Workflow
- `GH Action` ejecuta los scrapers.
- Los datos se normalizan y se exportan a `public/jobs.json`.
- `peaceiris/actions-gh-pages` despliega `public/` a la rama `gh-pages`.

## Uso desde frontend externo
- Si alojas el HTML en otro host, apunta la URL del JSON a la ruta de GitHub Pages.
- Ejemplo: `https://<tu-usuario>.github.io/<tu-repo>/jobs.json`.
- El frontend puede ser estático en otro dominio y consumir solo el `jobs.json` publicado.
- En `script.js` se usa `window.JOBS_JSON_URL || 'jobs.json'`, por lo que puedes definir la URL remota antes de cargar el script.

## JSON segmentado por comunidad
- `export_json.py` ahora genera `public/communities.json` con el índice de comunidades.
- Además crea `public/jobs/<slug-comunidad>.json` para cada comunidad.
- El frontend carga solo la comunidad seleccionada y reduce la sobrecarga de datos.
