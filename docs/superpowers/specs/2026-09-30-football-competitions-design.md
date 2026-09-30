# Competiciones de fútbol por continente — Diseño

Fecha: 2026-09-30
Estado: pendiente de revisión

## Objetivo

Una app externa leerá las imágenes de este repositorio (vía jsDelivr/raw de GitHub). Necesita un catálogo JSON que identifique cada competición sin ambigüedad para no mostrar un logo equivocado.

Esta fase cubre solo **competiciones** de fútbol. Los escudos de clubes de las 5 grandes ligas son la fase siguiente y quedan fuera de este diseño.

## Contexto

- `football/competitions/` contiene hoy 17 imágenes planas.
- 11 de ellas no son logos, sino collages de FootyLogos.com (logo de liga + escudos de todos los clubes, fondo blanco, marca de agua): Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Eredivisie, Liga Portugal, Brasileirão Série A, Liga Profesional Argentina, Liga MX y MLS.
- Las otras 6 parecen logos sueltos: UEFA Champions League, UEFA Europa League, UEFA Conference League, Copa del Rey, Copa Libertadores y FIFA Club World Cup. Se revisarán una a una antes de aceptarlas.
- `data/competitions.json` se genera a partir del nombre del archivo (produce nombres incorrectos como "Laliga" o "Liga Mx").
- La app todavía no consume el repositorio, así que no hay que mantener compatibilidad con rutas antiguas.

## Requisitos

1. Organizar los logos de competiciones en carpetas por continente.
2. Conservar los collages (no borrarlos) en una ubicación separada.
3. Un catálogo JSON con id estable, nombre oficial y alias de cada competición.
4. Un índice alias → id para que la app resuelva nombres procedentes de otras fuentes.
5. Logos limpios buscados en internet: sin marca de agua, fondo transparente.
6. Validación automática (local y en GitHub Actions) que impida publicar un catálogo inconsistente.

## Estructura de carpetas

```text
football/
├── competitions/
│   ├── europe/
│   ├── south-america/
│   ├── north-america/
│   ├── asia/
│   └── world/
└── collages/
```

- Las carpetas `africa/` y `oceania/` no se crean hasta que haya alguna competición de esos continentes.
- Los torneos de selecciones van en el continente de su confederación (Eurocopa → `europe`, Copa América → `south-america`, Gold Cup → `north-america`). Los torneos FIFA van en `world/`.
- Los 11 collages se mueven a `football/collages/<id>.png` sin modificarlos.

## Formato de las imágenes

- PNG con canal alfa (fondo transparente).
- Recortado a los márgenes del contenido.
- Lado mayor de 1024 px como máximo; no se amplían imágenes más pequeñas.
- Nombre de archivo: `<id>.png`.
- Fuente preferida: SVG o PNG oficial de alta resolución. Nada con marca de agua.

Un script `scripts/normalize_logo.py <entrada> <salida>` aplica el recorte y el redimensionado. Usa Pillow (se añade `requirements.txt`).

## Catálogo — `data/football/competitions.json`

Es la fuente de verdad. No lo genera ningún script: lo mantiene Claude a petición del propietario del repositorio (o el propietario directamente).

```json
{
  "version": 1,
  "competitions": [
    {
      "id": "laliga",
      "name": "LaLiga",
      "aliases": ["La Liga", "LaLiga EA Sports", "Spanish La Liga"],
      "type": "league",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "ES",
      "logo": "football/competitions/europe/laliga.png",
      "collage": "football/collages/laliga.png"
    }
  ]
}
```

Campos:

| Campo | Tipo | Reglas |
|---|---|---|
| `id` | string | kebab-case, único, estable una vez publicado; igual al nombre del archivo del logo sin extensión |
| `name` | string | nombre oficial actual |
| `aliases` | string[] | otros nombres habituales (patrocinadores, idiomas, nombres antiguos); puede estar vacío |
| `type` | enum | `league`, `cup`, `super-cup`, `international` (torneos entre clubes o selecciones de varios países; `scope` los distingue) |
| `scope` | enum | `club`, `national-team` |
| `continent` | enum | `europe`, `south-america`, `north-america`, `asia`, `africa`, `oceania`, `world` |
| `confederation` | enum | `UEFA`, `CONMEBOL`, `CONCACAF`, `AFC`, `CAF`, `OFC`, `FIFA` |
| `country` | string \| null | ISO 3166-1 alfa-2, o ISO 3166-2 para naciones del Reino Unido (`GB-ENG`); `null` en torneos internacionales |
| `logo` | string \| null | ruta relativa a la raíz del repositorio; `null` mientras falte el logo limpio |
| `collage` | string \| null | ruta del collage, o `null` si no existe |

Las entradas se ordenan por continente y, dentro de cada uno, en el orden de la lista siguiente.

## Competiciones incluidas (36)

**europe (24)**

| id | name | type | scope | country |
|---|---|---|---|---|
| uefa-champions-league | UEFA Champions League | international | club | null |
| uefa-europa-league | UEFA Europa League | international | club | null |
| uefa-conference-league | UEFA Conference League | international | club | null |
| uefa-super-cup | UEFA Super Cup | super-cup | club | null |
| premier-league | Premier League | league | club | GB-ENG |
| laliga | LaLiga | league | club | ES |
| serie-a | Serie A | league | club | IT |
| bundesliga | Bundesliga | league | club | DE |
| ligue-1 | Ligue 1 | league | club | FR |
| eredivisie | Eredivisie | league | club | NL |
| liga-portugal | Liga Portugal | league | club | PT |
| fa-cup | FA Cup | cup | club | GB-ENG |
| efl-cup | EFL Cup | cup | club | GB-ENG |
| community-shield | FA Community Shield | super-cup | club | GB-ENG |
| copa-del-rey | Copa del Rey | cup | club | ES |
| supercopa-de-espana | Supercopa de España | super-cup | club | ES |
| coppa-italia | Coppa Italia | cup | club | IT |
| supercoppa-italiana | Supercoppa Italiana | super-cup | club | IT |
| dfb-pokal | DFB-Pokal | cup | club | DE |
| dfl-supercup | DFL-Supercup | super-cup | club | DE |
| coupe-de-france | Coupe de France | cup | club | FR |
| trophee-des-champions | Trophée des Champions | super-cup | club | FR |
| uefa-euro | UEFA European Championship | international | national-team | null |
| uefa-nations-league | UEFA Nations League | international | national-team | null |

**south-america (5)**

| id | name | type | scope | country |
|---|---|---|---|---|
| copa-libertadores | CONMEBOL Libertadores | international | club | null |
| copa-sudamericana | CONMEBOL Sudamericana | international | club | null |
| brasileirao-serie-a | Campeonato Brasileiro Série A | league | club | BR |
| liga-profesional-argentina | Liga Profesional de Fútbol | league | club | AR |
| copa-america | Copa América | international | national-team | null |

**north-america (4)**

| id | name | type | scope | country |
|---|---|---|---|---|
| liga-mx | Liga MX | league | club | MX |
| mls | Major League Soccer | league | club | US |
| concacaf-champions-cup | Concacaf Champions Cup | international | club | null |
| concacaf-gold-cup | Concacaf Gold Cup | international | national-team | null |

**asia (1)**

| id | name | type | scope | country |
|---|---|---|---|---|
| saudi-pro-league | Saudi Pro League | league | club | SA |

**world (2)**

| id | name | type | scope | country |
|---|---|---|---|---|
| fifa-world-cup | FIFA World Cup | international | national-team | null |
| fifa-club-world-cup | FIFA Club World Cup | international | club | null |

Los ids de las 17 competiciones actuales se mantienen igual que sus nombres de archivo de hoy. MLS tiene `country: "US"` aunque incluye clubes de Canadá.

## Índice de alias — `data/football/competitions-lookup.json`

Lo genera `scripts/build_index.py` a partir del catálogo. Es un objeto plano `clave normalizada → id`. Por cada competición se incluyen su `id`, su `name` y todos sus `aliases`.

Normalización (la misma que debe aplicar la app antes de buscar):

1. Descomposición Unicode NFKD y eliminación de marcas diacríticas.
2. Minúsculas.
3. Todo carácter que no sea `a-z` o `0-9` se sustituye por un espacio.
4. Espacios repetidos se colapsan y se recortan los extremos.

Ejemplo: `"LaLiga EA Sports"` → `"laliga ea sports"`; `"Primera División"` → `"primera division"`; `"laliga"` (id) → `"laliga"`.

Uso previsto en la app:

1. Normalizar el nombre recibido.
2. Buscarlo en `competitions-lookup.json` → `id`.
3. Buscar el `id` en `competitions.json` → `logo`.
4. Construir la URL: `https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@<tag>/<logo>`.

El JSON se escribe con claves ordenadas para que la regeneración sea determinista (la CI compara con `git diff`).

## Cambios en scripts existentes

`scripts/build_index.py`:

- Deja de generar `data/competitions.json` (se elimina el archivo).
- Genera `data/football/competitions-lookup.json`.
- `data/all-assets.json` incluye `competitions` con `{id: {name, path}}` tomado del catálogo, solo para las entradas con `logo`. Las colecciones de UFC no cambian.

`scripts/validate_assets.py` mantiene las comprobaciones actuales y recorre también `football/competitions/*/` y `football/collages/`. Añade:

Errores (fallan la validación):

- El catálogo no es JSON válido o le falta un campo obligatorio.
- Un valor de `type`, `scope`, `continent` o `confederation` fuera de los permitidos.
- `id` duplicado o que no cumple kebab-case.
- `logo` no es `football/competitions/<continent>/<id>.png`, o el archivo no existe.
- `collage` no es `football/collages/<id>.png`, o el archivo no existe.
- Una imagen en `football/competitions/` o `football/collages/` sin entrada en el catálogo.
- Una imagen directamente en `football/competitions/` (fuera de una carpeta de continente).
- Dos competiciones distintas producen la misma clave normalizada.
- Un logo sin canal alfa.

Avisos (no fallan):

- Competiciones con `logo: null`.

GitHub Actions instala `requirements.txt` antes de validar, porque la comprobación de canal alfa usa Pillow.

## Obtención de logos

- Se buscan en internet: webs oficiales de las competiciones y federaciones, press kits, Wikimedia Commons y repositorios de logos sin marca de agua.
- Cada logo aceptado se registra en `data/sources.json`, indexado por ruta: `{"url": ..., "retrieved": "YYYY-MM-DD", "license": ... | null, "notes": ... | null}`.
- Las 6 imágenes actuales que parecen logos se revisan visualmente; si tienen marca de agua, fondo no transparente o están desactualizadas, se sustituyen.
- Si no se encuentra un logo aceptable, la entrada queda con `logo: null` y se informa al propietario.

## Documentación

El `README.md` se actualiza con la nueva estructura, el esquema del catálogo, las reglas de normalización y el ejemplo de uso desde la app.

## Fuera de alcance

- Escudos de clubes (siguiente fase).
- Variantes de logo (monocromo, fondo oscuro) y formato SVG.
- Script para dar de alta competiciones (descartado por el propietario).
- Cambios en los assets o scripts de UFC, salvo lo imprescindible en `build_index.py` y `validate_assets.py`.
