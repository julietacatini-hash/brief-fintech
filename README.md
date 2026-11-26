# Brief fintech — app gratuita

App de noticias sobre diseño y desarrollo de apps mobile y web para banca digital y fintech: regulación y ciberseguridad, bancos y fintech (con IA y lanzamientos) y experiencia de usuario. Se instala en el celular como cualquier app y no tiene ningún costo.

## Cómo funciona

- Cada 4 horas, GitHub Actions ejecuta `recolector/recolectar.py`.
- El script lee feeds RSS de fuentes confiables (Apple Developer, Android Developers, Nielsen Norman Group, Krebs on Security, etc.) y búsquedas de Google Noticias por tema, filtra por palabras clave, saca duplicados y guarda `docs/data/noticias.json`.
- Cada noticia lleva uno o más enlaces para consultar las bases:
  - **Nota:** el artículo original de cada medio que la publicó. Si dos fuentes cubren la misma noticia, se unifican en una sola con ambos enlaces.
  - **Otra cobertura:** otros medios que Google Noticias agrupa bajo la misma noticia.
  - **Documento oficial:** enlaces citados dentro de la nota que apuntan a organismos o documentación oficial (BCRA, CISA, Apple Developer, etc.). La lista está en `dominios_oficiales` de `recolector/fuentes.json`.
- Cada fuente tiene una región (`"region": "ar"` o `"global"` en `fuentes.json`). Las notas de sitios `.ar` se marcan como Argentina aunque vengan de una fuente global.
- GitHub Pages publica la carpeta `docs/`, que es la app. Muestra los últimos 7 días.

## Cómo se usa

- **Origen:** el selector de arriba arranca en Argentina. "Todo el mundo" suma las fuentes internacionales.
- **Categorías:** tres chips (Regulación y ciberseguridad, Bancos y fintech, Experiencia de usuario) que filtran por tema y se pueden combinar.
- **Limpiar filtros:** aparece cuando hay algo filtrado y vuelve a Argentina con todas las categorías.
- **Nuevas y anteriores:** cada vez que entrás, arriba aparecen destacadas las noticias que llegaron desde tu última visita. Las demás quedan plegadas en "Anteriores" y se abren con un toque. Si la app queda abierta en segundo plano más de 30 minutos, al volver cuenta como una visita nueva.
- **Memoria:** la app recuerda tus filtros y qué noticias ya viste, en el dispositivo.
- No usa IA ni claves de ninguna API: GitHub Actions y Pages son gratis para repositorios públicos.

## Puesta en marcha (una sola vez, unos 10 minutos)

1. **Crear el repositorio.** En GitHub, creá un repositorio público nuevo y subí todo el contenido de esta carpeta, incluida la carpeta oculta `.github`.
2. **Dar permiso de escritura.** En Settings › Actions › General › Workflow permissions, elegí "Read and write permissions" y guardá.
3. **Activar la web.** En Settings › Pages, elegí "Deploy from a branch", rama `main`, carpeta `/docs`. GitHub te da el link, del tipo `https://tu-usuario.github.io/brief-fintech/`.
4. **Primera carga.** En la pestaña Actions, abrí "Actualizar noticias" y tocá "Run workflow". En un par de minutos la app muestra las noticias del momento.

## Instalarla en el celular

- **iPhone:** abrí el link en Safari › Compartir › Agregar a inicio.
- **Android:** abrí el link en Chrome › menú › Instalar app.

Se abre a pantalla completa, con su ícono, y funciona sin conexión con lo último que cargó.

## Personalizar

Todo está en `recolector/fuentes.json`:

- **Agregar un medio:** sumá una fuente `"tipo": "rss"` con su URL de feed y la categoría.
- **Filtrar un medio general:** agregá `"filtro"` con palabras clave; solo entran las notas que las mencionan.
- **Seguir un tema nuevo:** sumá una fuente `"tipo": "google"` con la búsqueda en `"q"` (admite `OR`, comillas y paréntesis) e `"idioma"` `es` o `en`.
- **Ventana de días y cantidad por categoría:** `"dias"` y `"max_por_categoria"`.
- **Bancos, fintech y proveedores:** las fuentes con `"categoria": "auto"` siguen empresas (Galicia, Mercado Pago, Ualá, Red Link, Revolut, Stripe, Visa y otras). Cada noticia se ubica sola en un tema según sus palabras (`"reglas_categoria"`): fraude, seguridad o normativa van a "Regulación y ciberseguridad"; diseño, experiencia o reclamos, a "Experiencia de usuario"; y el resto, incluidas IA y lanzamientos, a "Bancos y fintech". Para sumar una empresa, agregala entre comillas dentro del `OR` de la búsqueda correspondiente. Las búsquedas argentinas excluyen notas de tasas, plazo fijo, dólar y acciones; esas exclusiones se sacan borrando los términos con `-` del final de la búsqueda.

La frecuencia se cambia en la línea `cron` de `.github/workflows/actualizar.yml`.

Si un feed deja de funcionar, la app sigue andando con el resto. El detalle de cada fuente queda en la sección `estado` de `docs/data/noticias.json`.

## Compartir

- **Para que otros la usen:** pasá el link. Cada persona la instala desde su celular y marca sus propias leídas.
- **Para que otros armen su versión:** marcá el repositorio como plantilla (Settings › Template repository). Cada persona crea su copia con "Use this template" y edita `fuentes.json` con sus temas.

## Limitaciones

- Los títulos y resúmenes son los que publica cada medio; no hay análisis ni resumen propio.
- El filtro por palabras clave puede dejar pasar alguna nota que no aplica o perder alguna que sí. Se ajusta en `fuentes.json`.
- Los enlaces de Google Noticias pasan por Google antes de abrir la nota original.
