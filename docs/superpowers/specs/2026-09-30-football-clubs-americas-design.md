# Escudos de clubes de América — Diseño

Fecha: 2026-09-30
Estado: pendiente de revisión

## Objetivo

Añadir los clubes de primera división de los 10 países de CONMEBOL y de 6 ligas de CONCACAF al catálogo de clubes, con el mismo formato, validación y flujo de actualización que las 25 ligas europeas (`docs/superpowers/specs/2026-09-30-football-clubs-design.md`).

## Contexto

- luukhopman/football-logos, la fuente de plantillas de la fase anterior, solo cubre ligas europeas.
- openfootball tiene datos parciales (faltan Chile, Perú, Uruguay, Bolivia, Venezuela, México y Centroamérica); no sirve como fuente única.
- Wikipedia tiene un artículo por liga y temporada, pero los títulos y las tablas de equipos cambian entre ligas; un scraper sería frágil.
- football-logos.cc tiene escudos de 1500×1500 px de los 16 países, mezclando todas las divisiones. Honduras, El Salvador y Jamaica solo tienen el de la selección, por eso quedan fuera.
- Los escudos de Toronto FC, Vancouver Whitecaps y CF Montréal están en la página de EE. UU. de football-logos.cc.

## Requisitos

1. Ligas: Brasil, Argentina, Uruguay, Colombia, Chile, Paraguay, Perú, Ecuador, Bolivia, Venezuela, México, MLS, Canadian Premier League, Costa Rica, Guatemala y Panamá.
2. Clubes de la temporada actual de cada liga y los que han jugado en ella desde 2022 (ligas de año natural) o 2022-23 (ligas que cruzan dos años).
3. El país de un club es el de su liga. Los clubes canadienses de la MLS llevan `US`.
4. Plantillas mantenidas a mano en el repo, tomadas de Wikipedia.
5. Escudo principal de football-logos.cc; si no hay uno válido, una URL indicada a mano (Wikimedia).
6. Cada emparejamiento se confirma visualmente antes de publicarse, igual que en Europa.
7. `sync_clubs.py plan|accept|apply` procesa luukhopman y las plantillas nuevas a la vez; volver a ejecutar `apply` no cambia nada.

## Plantillas — `data/football/rosters.json`

```json
{
  "brasileirao-serie-a": {
    "2022": ["Flamengo", "Palmeiras", "..."],
    "2026": ["..."]
  },
  "liga-mx": {
    "2022-23": ["..."],
    "2026-27": ["..."]
  }
}
```

- Clave de primer nivel: id de una competición de `competitions.json` con `type: league` y `country` no nulo. El país de todos sus clubes es el `country` de esa competición.
- Clave de temporada: `AAAA` o `AAAA-AA`. Dentro de una liga todas usan el mismo formato, así que el orden alfabético es el cronológico. La temporada actual es la mayor.
- Valores: nombres de club tal como aparecen en Wikipedia (en inglés), sin repetir dentro de la temporada.
- Apertura y Clausura cuentan como una única temporada.

## Integración con el sync

`scripts/football_clubs.py`:

- `COUNTRY_CODES` y `FL_COUNTRIES` añaden los 16 países (`"Brazil": "BR"` → `brazil`, `"United States": "US"` → `usa`, `"Costa Rica": "CR"` → `costa-rica`...).
- Nueva función `roster_index(rosters, competitions)` que devuelve entradas con la misma forma que `luuk_index`, con clave `"<país>|<nombre>"` (p. ej. `"Brazil|Flamengo"`):
  - `country_folder`: el nombre de país de `COUNTRY_CODES` correspondiente al `country` de la liga.
  - `latest_season`: la última temporada en la que aparece; `latest_path`: `null`.
  - Si el club está en la temporada actual de su liga, la entrada lleva esa liga como actual.
- Las entradas de los dos índices llevan un campo `league` (id de competición o `null`). `luuk_index` lo rellena con `LEAGUE_IDS`; `merge_clubs` usa ese campo en vez de consultar `LEAGUE_IDS`.
- Correspondencias (`clubs-mapping.json`): se admite `"source": "url"` con un campo `url`, para escudos que no están en football-logos.cc. `apply` descarga y normaliza esa URL y la anota en `sources.json`.

`scripts/sync_clubs.py`:

- `plan`, `accept [PAÍS]` y `apply` combinan los dos índices. `apply` falla antes de descargar si hay una clave sin correspondencia.
- La hoja de revisión muestra el nombre del club y el escudo propuesto; las entradas de plantilla no tienen imagen de luukhopman.
- Si una entrada de plantilla no tiene slug ni `url`, `apply` avisa y deja el club con `logo: null` (no hay respaldo de luukhopman).

## Competiciones nuevas (12)

Uruguay, Colombia, Chile, Paraguay, Perú, Ecuador, Bolivia, Venezuela, Canadian Premier League, Costa Rica, Guatemala y Panamá, con `type: league`, `scope: club`, confederación y continente correctos, y logo transparente de football-logos.cc o Wikimedia.

## Validación

`validate_assets.py` comprueba `rosters.json`:

- Cada clave es una competición de tipo `league` con `country`, y ese país tiene nombre en `COUNTRY_CODES`.
- Cada temporada tiene formato `AAAA` o `AAAA-AA`, todas con el mismo formato dentro de la liga.
- Cada temporada es una lista no vacía de nombres no vacíos, sin duplicados ni espacios al principio o al final.

Las correspondencias con `"source": "url"` deben tener `url`.

## Tests

- `roster_index`: temporada actual, clubes descendidos (`league: null`), clave y país derivados de la liga.
- `merge_clubs` con entradas de plantilla: club nuevo, club que desciende, nombre nuevo como alias.
- Validación de `rosters.json`: liga desconocida, liga que no es `league`, formato de temporada, duplicados.
- Catálogo real: `lookup["US"]["toronto fc"]` y `lookup["BR"]["flamengo"]` resuelven.

## Documentación

README: sección de clubes con las ligas de América y cómo añadir una temporada nueva a `rosters.json`.

## Fuera de alcance

- Honduras, El Salvador, Jamaica y el resto de CONCACAF.
- Segundas divisiones.
- Scraper automático de Wikipedia.
