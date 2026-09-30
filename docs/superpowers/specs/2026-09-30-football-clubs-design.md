# Escudos de clubes de fútbol — Diseño

Fecha: 2026-09-30
Estado: pendiente de revisión

## Objetivo

La app externa necesita el escudo correcto de cada club. Esta fase añade los clubes de las 25 ligas europeas que recoge [luukhopman/football-logos](https://github.com/luukhopman/football-logos), con un catálogo JSON que identifique cada club sin ambigüedad, y un script que permita actualizarlo cada temporada.

Se apoya en la fase anterior (`docs/superpowers/specs/2026-09-30-football-competitions-design.md`): mismo módulo de normalización, mismo criterio de logos (PNG transparente, lado mayor ≤ 1024 px) y misma validación en CI.

## Contexto

- luukhopman/football-logos (rama `master`):
  - `logos/<País> - <Liga>/<Club>.png`: temporada actual (2026/27), 25 ligas, 396 clubes.
  - `history/<temporada>/<País> - <Liga>/<Club>.png`: temporadas 2021/22 a 2025/26. Añade 301 clubes que ya no están en esas ligas (incluida la liga húngara, que salió del top 25).
  - Todas las imágenes son de 139×181 px: sirven para identificar la plantilla y como respaldo, no como escudo principal.
  - Un mismo club aparece a veces con nombres distintos según la temporada ("Beerschot VA" / "Beerschot V.A.", "Banik Ostrava" / "FC Banik Ostrava").
- football-logos.cc (sitio de `Leo4815162342/football-logos`, fuente de la fase anterior) tiene escudos de clubes a 1500×1500 px en `https://assets.football-logos.cc/logos/<país>/1500x1500/<slug>.<hash>.png`, listados en `https://football-logos.cc/<país>/`.
- Una comprobación inicial emparejó por nombre 383 clubes exactamente, 135 de forma aproximada y 179 sin coincidencia.

## Requisitos

1. Incluir los clubes de la temporada actual de las 25 ligas y los que han jugado en ellas desde 2021/22.
2. Escudo principal de football-logos.cc; si no existe, el de luukhopman.
3. Cada emparejamiento luukhopman ↔ football-logos.cc se confirma visualmente antes de publicarse.
4. Catálogo de clubes con id estable, nombre, alias, país, liga actual y ruta del escudo.
5. Índice de alias por país.
6. Añadir las 18 ligas que faltan al catálogo de competiciones, con logo.
7. Un script re-ejecutable cada temporada que solo pida revisar los clubes nuevos.
8. Validación automática en local y en CI.

## Estructura de carpetas

```text
football/clubs/<país>/<id>.png
```

`<país>` es el código de `country` en minúsculas: `es`, `gb-eng`, `gb-sct`, `tr`… Un club no cambia de carpeta al subir o bajar de categoría.

## Catálogo de clubes — `data/football/clubs.json`

```json
{
  "version": 1,
  "clubs": [
    {
      "id": "real-madrid",
      "name": "Real Madrid",
      "aliases": ["Real Madrid CF"],
      "country": "ES",
      "league": "laliga",
      "logo": "football/clubs/es/real-madrid.png"
    }
  ]
}
```

| Campo | Tipo | Reglas |
|---|---|---|
| `id` | string | kebab-case, único en todo el catálogo, estable una vez publicado; igual al nombre del archivo del escudo sin extensión |
| `name` | string | nombre del club |
| `aliases` | string[] | otros nombres; puede estar vacío |
| `country` | string | ISO 3166-1 alfa-2, o ISO 3166-2 para naciones del Reino Unido (`GB-ENG`, `GB-SCT`) |
| `league` | string \| null | id de una competición `type: "league"` del catálogo de competiciones; `null` si el club no está esta temporada en ninguna de las 25 ligas |
| `logo` | string \| null | `football/clubs/<country en minúsculas>/<id>.png`, o `null` si no hay escudo |

Orden: por `country` y, dentro de cada país, por `id`.

El script escribe este archivo. Los cambios manuales en `name` y `aliases` de un club existente se conservan en cada ejecución; `league` y `logo` los gestiona el script.

### Ids

- Por defecto, el slug del club en football-logos.cc (`arsenal`, `real-madrid`); si no hay escudo allí, el slug del nombre de luukhopman.
- Si el id ya existe en otro país, se añade el código de país: `<slug>-<country en minúsculas>`.
- Una vez publicado, un id no cambia aunque cambie la fuente.

### Alias automáticos

Para cada club nuevo el script añade como alias:

- todos los nombres con que aparece en luukhopman (temporada actual e historial),
- el nombre derivado del slug de football-logos.cc,
- cada uno de esos nombres sin los afijos habituales (`FC`, `CF`, `AFC`, `SC`, `AC`, `FK`, `SK`, `CD`, `UD`, `SV`, `BK`, `IF`, `NK`…), p. ej. "Arsenal FC" → "Arsenal".

Un alias automático que choque dentro del mismo país con otro club no se añade; el script lo lista en su salida.

## Índice de alias — `data/football/clubs-lookup.json`

Generado por `build_index.py`: `{ "<country>": { "<nombre normalizado>": "<id>" } }`, con `id`, `name` y `aliases` de cada club, usando la misma `normalize_name` de las competiciones. Claves ordenadas.

Uso previsto en la app: normalizar el nombre, buscar en el país del club → `id` → `logo` en `clubs.json`.

## Correspondencias — `data/football/clubs-mapping.json`

Registro de las decisiones de emparejamiento, mantenido por el flujo `plan` → revisión → `apply`:

```json
{
  "Spain|Real Madrid": {"id": "real-madrid", "source": "football-logos", "slug": "real-madrid"},
  "Belgium|Beerschot V.A.": {"id": "beerschot", "source": "football-logos", "slug": "beerschot"},
  "Belgium|Beerschot VA": {"id": "beerschot", "source": "football-logos", "slug": "beerschot"},
  "Hungary|Kecskeméti TE": {"id": "kecskemeti-te", "source": "luukhopman", "slug": null}
}
```

- Clave: `<carpeta de país de luukhopman>|<nombre del archivo sin extensión>`.
- Varias claves con el mismo `id` = el mismo club (unificación de nombres del historial).
- `source`: `football-logos` o `luukhopman`.

## `scripts/sync_clubs.py`

### `python scripts/sync_clubs.py plan`

1. Descarga el árbol de luukhopman (API de GitHub) y las páginas de país de football-logos.cc.
2. Para cada club de luukhopman sin entrada en `clubs-mapping.json`, propone un slug de football-logos.cc (coincidencia exacta del nombre normalizado sin afijos; si no, la más parecida por encima de un umbral) o ninguno.
3. Escribe las propuestas en `.cache/clubs/proposals.json` con el mismo formato de `clubs-mapping.json`.
4. Genera `.cache/clubs/review-<país>.jpg`: por cada propuesta, el escudo de luukhopman junto al de football-logos.cc, con la clave y el id propuesto.

### Revisión

Se revisan las hojas. Las propuestas correctas se copian a `clubs-mapping.json`; las incorrectas se corrigen (otro slug, `source: "luukhopman"`, o unificar con el `id` de otra clave). Nada se publica sin estar en `clubs-mapping.json`.

### `python scripts/sync_clubs.py apply`

1. Para cada `id` de `clubs-mapping.json`: si falta el escudo, lo descarga (football-logos.cc a 1500 px, o luukhopman), lo normaliza con `normalize_logo` y registra el origen en `data/sources.json`.
2. Actualiza `clubs.json`: añade los clubes nuevos (con alias automáticos), conserva `name` y `aliases` de los existentes y recalcula `league` a partir de la carpeta `logos/` actual de luukhopman.
3. Ejecuta `build_index.py`.
4. Termina con error si algún club de luukhopman no está en `clubs-mapping.json`.

La correspondencia carpeta de liga de luukhopman → id de competición y carpeta de país → código ISO (las 25 ligas más Hungría, `HU`, que solo aparece en el historial) se define como constantes en el script.

Si un club usa el escudo de luukhopman, se toma el de la temporada más reciente en que aparece.

## Competiciones nuevas (18)

Todas `type: "league"`, `scope: "club"`, `continent: "europe"`, `confederation: "UEFA"`, `collage: null`. Logos: primero repositorios (football-logos.cc), después Wikipedia/Wikimedia.

| id | name | aliases | country | carpeta luukhopman |
|---|---|---|---|---|
| austrian-bundesliga | Austrian Football Bundesliga | Admiral Bundesliga, Austrian Bundesliga | AT | Austria - Bundesliga |
| belgian-pro-league | Belgian Pro League | Jupiler Pro League, Belgian First Division A | BE | Belgium - Jupiler Pro League |
| bulgarian-first-league | Bulgarian First League | efbet Liga, First Professional Football League | BG | Bulgaria - efbet Liga |
| croatian-football-league | Croatian Football League | SuperSport HNL, HNL, Prva HNL | HR | Croatia - SuperSport HNL |
| czech-first-league | Czech First League | Chance Liga, Fortuna Liga | CZ | Czech Republic - Chance Liga |
| danish-superliga | Danish Superliga | 3F Superliga | DK | Denmark - Superliga |
| greek-super-league | Super League Greece | Super League 1, Stoiximan Super League | GR | Greece - Super League 1 |
| israeli-premier-league | Israeli Premier League | Ligat ha'Al | IL | Israel - Ligat ha'Al |
| eliteserien | Eliteserien | Norwegian Eliteserien | NO | Norway - Eliteserien |
| ekstraklasa | Ekstraklasa | PKO BP Ekstraklasa, Polish Ekstraklasa | PL | Poland - PKO BP Ekstraklasa |
| romanian-liga-1 | Liga I | Romanian SuperLiga, SuperLiga României | RO | Romania - SuperLiga |
| russian-premier-league | Russian Premier League | RPL, Mir Russian Premier League | RU | Russia - Premier Liga |
| scottish-premiership | Scottish Premiership | SPFL Premiership, William Hill Premiership | GB-SCT | Scotland - Scottish Premiership |
| serbian-superliga | Serbian SuperLiga | Super liga Srbije, Mozzart Bet Super liga | RS | Serbia - Super liga Srbije |
| allsvenskan | Allsvenskan | Swedish Allsvenskan | SE | Sweden - Allsvenskan |
| swiss-super-league | Swiss Super League | Brack Super League | CH | Switzerland - Super League |
| super-lig | Süper Lig | Turkish Super Lig, Trendyol Süper Lig | TR | Türkiye - Süper Lig |
| ukrainian-premier-league | Ukrainian Premier League | UPL, Ukrainian Premier Liha | UA | Ukraine - Premier Liga |

Las 7 ya existentes: `premier-league` (England - Premier League), `laliga` (Spain - LaLiga), `serie-a` (Italy - Serie A), `bundesliga` (Germany - Bundesliga), `ligue-1` (France - Ligue 1), `eredivisie` (Netherlands - Eredivisie), `liga-portugal` (Portugal - Liga Portugal).

La lista de alias genéricos prohibidos del test `RealCatalogTest` se amplía con "superliga", "super league", "premier liga" y "pro league", porque nombran ligas de varios países.

## Validación

Nuevo en `validate_assets.py` (recorre también `football/clubs/`):

Errores:

- Campo obligatorio ausente o de tipo incorrecto.
- `id` duplicado o que no es kebab-case.
- `country` con formato inválido.
- `logo` distinto de `football/clubs/<country en minúsculas>/<id>.png`, archivo inexistente o sin píxeles transparentes.
- `league` que no es un id de competición con `type: "league"`.
- Imagen en `football/clubs/` sin entrada en el catálogo.
- Dos clubes del mismo país con la misma clave normalizada.
- Un `id` de `clubs-mapping.json` que no está en `clubs.json`.

Avisos:

- Clubes con `logo: null`.
- Escudos con lado mayor < 400 px (respaldos de luukhopman), para saber cuáles mejorar.

## Índices generados

- `data/football/clubs-lookup.json` (nuevo).
- `data/all-assets.json` añade `clubs`: `{id: {name, path}}` para los clubes con `logo`.

## Tests

Unitarios, sin red:

- Emparejamiento: nombre normalizado sin afijos, coincidencia exacta, aproximada y ninguna.
- Ids: slug preferente, sufijo de país ante colisión, estabilidad de ids existentes.
- Fusión con el catálogo: conserva `name`/`aliases` manuales, añade clubes nuevos, recalcula `league`, `league: null` para clubes fuera de la temporada actual.
- Alias automáticos: quita afijos y descarta los que chocan dentro del país.
- Validación del catálogo de clubes y del lookup por país.

La descarga (GitHub, football-logos.cc) se aísla en funciones finas que no se testean; la lógica recibe datos ya descargados.

## Documentación

README: estructura de `football/clubs/`, esquema del catálogo, uso desde la app (nombre + país) y flujo `plan` → revisión → `apply` para cada temporada.

## Fuera de alcance

- Versiones antiguas de escudos (se usa el más reciente de cada club).
- Clubes de ligas fuera de las 25 de luukhopman.
- Selecciones nacionales.
- Variantes de escudo (monocromo, fondo oscuro).
