# Sports Assets CDN

Repositorio de recursos visuales deportivos preparado para usarse directamente desde GitHub o jsDelivr.

## Estructura

```text
sports-assets/
├── football/
│   ├── competitions/
│   │   ├── europe/
│   │   ├── south-america/
│   │   ├── north-america/
│   │   ├── asia/
│   │   └── world/
│   ├── clubs/                          # <país>/<id>.png (es, gb-eng, pt…)
│   └── collages/
├── ufc/
│   ├── fighters/
│   └── logos/
├── baseball/                            # MLB: competitions/ y teams/<país>/
├── basketball/                          # NBA: competitions/ y teams/<país>/
├── hockey/                              # NHL: competitions/ y teams/<país>/
├── american-football/                   # NFL: competitions/ y teams/us/
├── data/
│   ├── football/
│   │   ├── competitions.json          # catálogo (fuente de verdad, se edita a mano)
│   │   ├── competitions-lookup.json   # generado: nombre normalizado → id
│   │   ├── clubs.json                 # catálogo de clubes (lo actualiza sync_clubs.py)
│   │   ├── clubs-mapping.json         # emparejamientos club → escudo, revisados
│   │   ├── rosters.json               # clubes por liga y temporada de las ligas de América (a mano)
│   │   ├── clubs-lookup.json          # generado: país → nombre normalizado → id
│   │   └── domestic-coverage.json     # auditoría de ligas y copas, incluidos clasificatorios
│   ├── fighters.json
│   ├── ufc-logos.json
│   ├── ufc-fighters-seed.json
│   ├── all-assets.json
│   └── sources.json
├── scripts/
│   ├── build_index.py
│   ├── football_catalog.py
│   ├── football_clubs.py
│   ├── sync_clubs.py
│   ├── normalize_logo.py
│   ├── download_ufc_fighters.py
│   └── validate_assets.py
└── tests/
```

## Convención de nombres

Usa minúsculas, guiones y extensiones web comunes.

```text
uefa-champions-league.png
laliga.png
ilia-topuria.jpg
islam-makhachev.jpg
alex-pereira.jpg
```

Evita espacios, tildes y caracteres especiales.

## Uso mediante jsDelivr

### Peleadores UFC

La extensión depende de la imagen reutilizable disponible en Wikimedia Commons. Consulta `data/fighters.json` para obtener la ruta exacta.

Ejemplo:

```text
https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@main/ufc/fighters/ilia-topuria.jpg
```

### Competiciones

Consulta `data/football/competitions.json` para obtener la ruta exacta (ver [Competiciones de fútbol](#competiciones-de-fútbol)).

```text
https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@main/football/competitions/europe/uefa-champions-league.png
```

Para producción, es recomendable usar un tag en vez de `main`, por ejemplo `@v1.0.0`.

## Competiciones de fútbol

Los logos están en `football/competitions/<continente>/<id>.png`: PNG transparente con un lado mayor de 1024 px como máximo. Los collages antiguos (liga + escudos de clubes) se conservan en `football/collages/`.

`data/football/competitions.json` es el catálogo. Cada competición tiene:

| Campo | Descripción |
|---|---|
| `id` | identificador estable; coincide con el nombre del archivo |
| `name` | nombre oficial |
| `aliases` | otros nombres habituales |
| `type` | `league`, `cup`, `super-cup` o `international` |
| `scope` | `club` o `national-team` |
| `continent` | carpeta del logo |
| `confederation` | `UEFA`, `CONMEBOL`, `CONCACAF`, `AFC`, `CAF`, `OFC` o `FIFA` |
| `country` | código ISO (`ES`, `GB-ENG`…) o `null` si es internacional |
| `logo` | ruta del logo, o `null` si todavía no hay uno limpio |
| `collage` | ruta del collage, o `null` |

### Uso desde una app

1. Normaliza el nombre que recibes: quita tildes, translitera letras como ł, ø, æ o ı, pasa a minúsculas, cambia todo lo que no sea letra o número por un espacio y colapsa los espacios (`"LaLiga EA Sports"` → `"laliga ea sports"`).
2. Búscalo en `data/football/competitions-lookup.json` para obtener el `id`.
3. Busca ese `id` en `data/football/competitions.json` para obtener `logo`.
4. Si tu fuente indica el país, compáralo con `country` (o con `confederation` en torneos internacionales). Si no coinciden, trátalo como "sin logo": nombres como "Premier League", "Serie A", "Bundesliga" o "Ligue 1" también los usan ligas de otros países.
5. Construye la URL:

```text
https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@main/football/competitions/europe/laliga.png
```

### Añadir o sustituir un logo

Busca primero en repositorios de logos (por ejemplo [football-logos](https://github.com/Leo4815162342/football-logos)) y, si no aparece limpio, en Wikipedia/Wikimedia Commons. Descarta cualquier imagen con marca de agua o fondo opaco.

```bash
python scripts/normalize_logo.py descarga.png football/competitions/europe/laliga.png
```

Después actualiza `logo` en el catálogo, registra el origen en `data/sources.json` y ejecuta `python scripts/build_index.py`.

## Clubes de fútbol

Clubes de 41 ligas (temporada actual e historial desde 2021/22 en Europa o 2022
en América), además de participantes en las copas domésticas de Inglaterra,
España, Italia, Alemania y Francia, incluidas sus rondas clasificatorias.

- **Europa (25 ligas):** la lista de clubes viene de [luukhopman/football-logos](https://github.com/luukhopman/football-logos).
- **América (16 ligas: los 10 países de CONMEBOL, Liga MX, MLS, Canadian Premier League, Costa Rica, Guatemala y Panamá):** la lista de clubes está en `data/football/rosters.json`, mantenido a mano a partir de Wikipedia.

Las imágenes vienen de [football-logos.cc](https://github.com/Leo4815162342/football-logos) (1024 px). Si un club no está allí, se usa el PNG de luukhopman (139×181) o, en América, el escudo de su artículo de Wikipedia; la validación avisa de los que tienen baja resolución. Algunos clubes históricos no tienen escudo disponible (`logo: null`).

El país de un club es el de su liga: Toronto FC, Vancouver Whitecaps y CF Montréal juegan la MLS y tienen país `US`.

Los escudos están en `football/clubs/<país>/<id>.png`. La carpeta no cambia cuando un club sube o baja de categoría.

`data/football/clubs.json`:

| Campo | Descripción |
|---|---|
| `id` | identificador estable; coincide con el nombre del archivo |
| `name` | nombre del club |
| `aliases` | otros nombres habituales |
| `country` | código ISO (`ES`, `GB-ENG`, `GB-SCT`…) |
| `league` | id de su liga en `competitions.json` esta temporada, o `null` si no juega en ninguna de las 41 |
| `logo` | ruta del escudo |

### Uso desde una app

1. Normaliza el nombre igual que con las competiciones: quita tildes, translitera letras como ł, ø, æ o ı (`"Wisła Kraków"` → `"wisla krakow"`), pasa a minúsculas y cambia lo que no sea letra o número por un espacio.
2. Búscalo en `data/football/clubs-lookup.json` **dentro de su país**: `lookup["ES"]["real madrid"]` → `real-madrid`. Hay nombres que se repiten entre países ("Sporting", "Dinamo"), por eso el país es obligatorio. Solo se encuentran el `id`, el `name` y los `aliases` del club; si tu fuente usa otro nombre, añádelo como alias en `clubs.json`.
3. Busca ese `id` en `data/football/clubs.json` para obtener `logo`.
4. Construye la URL:

```text
https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@main/football/clubs/es/real-madrid.png
```

### Actualizar cada temporada

```bash
python scripts/sync_clubs.py plan      # propone escudos para los clubes nuevos y genera .cache/clubs/review-*.jpg
python scripts/sync_clubs.py accept    # copia las propuestas a data/football/clubs-mapping.json
# revisa las hojas y corrige en clubs-mapping.json los emparejamientos incorrectos
python scripts/sync_clubs.py apply     # descarga escudos, actualiza clubs.json y la liga de cada club, y regenera índices
```

`apply` no sobrescribe escudos existentes ni los nombres y alias que se hayan editado a mano en `clubs.json`.

En América, antes de `plan` hay que añadir la temporada nueva de cada liga a `data/football/rosters.json`:

```json
"liga-mx": {
  "2026-27": ["América", "Atlas", "..."]
}
```

- La temporada es `AAAA` en las ligas de año natural y `AAAA-AA` en Liga MX, Costa Rica y Guatemala (Apertura y Clausura juntos). La más reciente es la actual.
- Usa el nombre del club tal como aparece en la Wikipedia en inglés y escríbelo igual en todas las temporadas.
- Si football-logos.cc no tiene el escudo, pon en `clubs-mapping.json` `"source": "url"` con la URL https de un PNG de Wikipedia/Wikimedia, o `"source": "none"` si no hay ninguno.

### Cobertura de las competiciones domésticas de fútbol

`data/football/domestic-coverage.json` conserva la auditoría de 2026/27,
comprobada el 30 de octubre de 2026: fuentes, ids de clubes por competición,
fase de entrada cuando está disponible y lista explícita de escudos pendientes.

| Competición | Entrantes catalogados | Cobertura de la lista |
|---|---:|---|
| Premier League / LaLiga / Serie A | 20 cada una | completa |
| Bundesliga / Ligue 1 | 18 cada una | completa |
| FA Cup | 743 | lista oficial de admitidos, desde extra preliminary round |
| EFL Cup | 92 | completa |
| Copa del Rey | 126 | incluye los 20 de la previa y sus 10 perdedores |
| Coppa Italia | 44 | incluye el turno preliminar; sin equipos ficticios TBD |
| DFB-Pokal | 64 | completa |
| Supercopas de los cinco países | 2 cada una; España 4 | participantes ya cubiertos |
| Coupe de France | 7.031 | parcial: 7.002 identidades FFF regionales más otros entrantes nacionales |

`complete` se refiere a la **lista de participantes**, no a la disponibilidad
de sus imágenes. Un club sin escudo transparente verificado usa `logo: null`;
no se publica como recurso visual en `all-assets.json`. No se usan imágenes
genéricas, escudos de otro club ni fondos blancos convertidos automáticamente.

En Francia se consultaron 190 páginas de partidos de 19 grupos, incluidas
Mayotte y Réunion, mediante el espejo TheFootData de la competición FFF 449168.
La lista no sustituye al registro completo: por ejemplo, LAURA ofrece 892
clubes en partidos frente a 897 inscritos oficialmente. Faltan reconciliaciones
de bajas antes de jugar, exentos y fases locales de Nueva Caledonia, Polinesia
y Saint-Pierre-et-Miquelon. El archivo marca esta competición como incompleta.

La participación en una copa va en la auditoría; `league` conserva solo la
liga actual o `null` para los clubes fuera de las ligas cubiertas. Las cinco
primeras divisiones se revisaron con listas de 2026/27. Los campos opcionales
`external_ids.espn` y `external_ids.fff` registran identidades del proveedor,
sin reemplazar el id estable del CDN.

Se mantienen separados AFC Liverpool y Liverpool FC, AFC Mansfield y Mansfield
Town, o AS Strasbourg y RC Strasbourg. Las grafías con AFC al final (Leeds United
AFC, Wrexham AFC, etc.) son alias del mismo club. Si dos clubes FFF tienen un
nombre indistinguible, el catálogo añade su identificador FFF como desambiguación
y evita un alias ambiguo.

Para mejorar un escudo pendiente, identifica primero el club en la fuente de la
auditoría, registra el origen en `data/sources.json`, normaliza el PNG con
`scripts/normalize_logo.py` y actualiza `logo`. Regenera los índices y actualiza
`missing_logos` en la auditoría. Los tests protegen la cobertura y la separación
de clubes distintos. El flujo `sync_clubs.py` conserva los clubes y alias
existentes editados a mano.

## MLB — béisbol

Los 30 equipos de MLB y el logo de la liga siguen las convenciones de los
catálogos de fútbol: ids estables, alias explícitos, PNG transparente recortado,
lado mayor de 1024 px como máximo y origen en `data/sources.json`.
Las imágenes actuales proceden de ESPN (500 px antes del recorte, sin ampliar);
los nombres, ids y divisiones se contrastaron con MLB Stats API para 2026.

```text
baseball/
├── competitions/north-america/mlb.png
└── teams/
    ├── us/<id>.png
    └── ca/toronto-blue-jays.png
data/baseball/
├── competitions.json
├── competitions-lookup.json       # generado: nombre normalizado → id
├── teams.json
└── teams-lookup.json              # generado: liga → nombre normalizado → id
```

`competitions.json` y `teams.json` son los catálogos editables, con `version: 1`
y listas `competitions` / `teams`. Cada equipo tiene `id`, `name`, `aliases`,
`abbreviation`, `mlb_id`, `country`, `league`, `division` y `logo`.
`mlb_id` es el identificador numérico oficial; `league` es `mlb` y `division`
usa `AL East`, `AL Central`, `AL West`, `NL East`, `NL Central` o `NL West`.
Aquí `country` indica la ubicación del equipo: Toronto usa `CA`, los demás `US`.
MLB tiene `country: null` porque incluye equipos de ambos países.

Normaliza el nombre con las mismas reglas que fútbol y busca en
`teams-lookup.json["mlb"]`: `"nyy"` → `"new-york-yankees"`.
Después toma `logo` del catálogo. Las abreviaturas también se indexan.
El nombre actual es `Athletics`; `Oakland Athletics`, `OAK` y `A's` son alias
del mismo equipo, no entradas históricas ni logos antiguos.

```text
https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@main/baseball/teams/us/new-york-yankees.png
https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@main/baseball/competitions/north-america/mlb.png
```

`data/all-assets.json` añade las colecciones `baseball-teams` y
`baseball-competitions`, con la misma forma `{id: {name, path}}` que fútbol.

Para actualizar:

1. Revisa nombres, alias, divisiones y equipos en el catálogo contra MLB.
   Conserva los ids publicados y añade los nombres anteriores como alias.
2. Revisa las URLs de los logos en `data/sources.json` antes de cambiarlas.
3. Ejecuta `python scripts/sync_mlb.py` para descargar los logos que falten.
   Usa `--force` para sustituir todos los existentes desde las URLs revisadas.
   El script normaliza imágenes, registra la fecha y regenera los índices.
4. Revisa visualmente los logos y ejecuta
   `python -m unittest discover -s tests` y `python scripts/validate_assets.py`.

Para cambios solo de metadatos, basta `python scripts/build_index.py`.
La validación detecta rutas incorrectas, archivos ausentes o huérfanos,
alias ambiguos dentro de la liga, ids duplicados y logos opacos o mayores de
1024 px. Los logos siguen siendo marcas de sus propietarios; su descarga
no concede una licencia de redistribución.

## NBA, NHL y NFL

Los tres deportes siguen la estructura de MLB, con PNG transparentes recortados,
sin ampliar y con lado mayor de 1024 px como máximo:

| Liga | Equipos actuales | Carpeta de imágenes | Carpeta de catálogos |
|---|---|---|---|
| NBA | 30 | `basketball/` | `data/basketball/` |
| NHL | 32 | `hockey/` | `data/hockey/` |
| NFL | 32 | `american-football/` | `data/american-football/` |

Cada carpeta de imágenes contiene `competitions/north-america/<liga>.png` y
`teams/<país>/<id>.png`. `american-football` distingue NFL del fútbol de
`football/`. El país indica la ubicación del equipo: `CA` para Toronto Raptors
y los siete equipos canadienses de NHL, `US` para los demás.

Los catálogos editables son `competitions.json` y `teams.json`, con `version: 1`
y listas `competitions` / `teams`, igual que MLB. Los equipos tienen `id`,
`name`, `aliases`, `abbreviation`, `espn_id`, `country`, `league`, `conference`,
`division` y `logo`. `espn_id` identifica al equipo en ESPN; no es un id oficial
de NBA, NHL o NFL. NBA y NHL usan `Eastern` / `Western`; NFL usa `AFC` / `NFC`.
`division` contiene el nombre de la división sin repetir la conferencia.

`build_index.py` genera `competitions-lookup.json` y `teams-lookup.json` dentro
de cada carpeta de datos. Usa la misma normalización que fútbol y MLB:
`teams_lookup["nba"]["gsw"]` → `golden-state-warriors`;
`teams_lookup["nhl"]["utah hockey club"]` → `utah-mammoth`.
Los alias antiguos resuelven al logo actual, no a una variante histórica.
El índice general añade `<deporte>-teams` y `<deporte>-competitions`, con
`{id: {name, path}}` igual que MLB.

Ejemplos de rutas para jsDelivr:

```text
https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@main/basketball/teams/us/los-angeles-lakers.png
https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@main/hockey/teams/us/utah-mammoth.png
https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@main/american-football/teams/us/kansas-city-chiefs.png
```

Para actualizar, revisa primero los nombres y las divisiones en los directorios
oficiales de [NBA](https://www.nba.com/teams),
[NHL](https://www.nhl.com/info/teams/) y [NFL](https://www.nfl.com/teams/).
Conserva los ids publicados y edita los alias explícitamente. Revisa las URLs
de las imágenes en `data/sources.json` antes de descargar:

```bash
python scripts/sync_league.py nba
python scripts/sync_league.py nhl
python scripts/sync_league.py nfl
```

El comando descarga los archivos ausentes y regenera los índices. `--force`
sustituye todos los logos de la liga seleccionada desde las URLs revisadas.
Para cambios solo de metadatos, usa `python scripts/build_index.py`.
Los logos iniciales proceden de ESPN a 500 px antes del recorte y las fuentes
incluyen la URL de verificación del directorio oficial. Los catálogos iniciales
se verificaron el 30 de octubre de 2026; NBA/NHL corresponden a 2026-27 y NFL a
2026. Las marcas pertenecen a sus propietarios, igual que los recursos de MLB.

Después de cualquier actualización, revisa las imágenes visualmente y ejecuta:

```bash
python -m unittest discover -s tests
python scripts/validate_assets.py
```

La validación detecta ids y alias duplicados, ligas o divisiones incorrectas,
rutas inválidas, archivos ausentes o huérfanos y PNG opacos, vacíos o mayores
de 1024 px. El comando rechaza catálogos inválidos antes de descargar.

## Descargar imágenes de peleadores UFC

El script `scripts/download_ufc_fighters.py` busca imágenes reutilizables en Wikimedia Commons, guarda la imagen en `ufc/fighters/`, registra autor, licencia y fuente en `data/sources.json`, y luego regenera los índices JSON.

Primero actualiza tu copia local:

```bash
git pull origin main
```

Prueba con cinco peleadores:

```bash
python scripts/download_ufc_fighters.py --limit 5
```

Descarga la lista inicial completa de 30 peleadores:

```bash
python scripts/download_ufc_fighters.py
```

Descarga uno específico:

```bash
python scripts/download_ufc_fighters.py --fighter "Ilia Topuria"
```

Comprueba qué archivo escogería sin descargar nada:

```bash
python scripts/download_ufc_fighters.py --fighter "Ilia Topuria" --dry-run
```

Reemplaza una imagen existente:

```bash
python scripts/download_ufc_fighters.py --fighter "Ilia Topuria" --force
```

Después revisa visualmente las imágenes elegidas. La búsqueda es automática y puede seleccionar una foto válida por licencia que no sea el retrato más conveniente para una plantilla gráfica.

## Generar índices JSON

```bash
python scripts/build_index.py
```

## Validar recursos

```bash
python scripts/validate_assets.py
```

Instala las dependencias y ejecuta los tests:

```bash
pip install -r requirements.txt
python -m unittest discover -s tests
```

La validación falla si un catálogo apunta a un archivo inexistente, si hay imágenes sin entrada, si un logo o escudo no es transparente, si dos competiciones (o dos clubes del mismo país) comparten un alias, o si un club apunta a una liga que no existe.

## Licencias

La licencia del código no concede derechos sobre logos, marcas, fotografías o retratos de terceros. El descargador de UFC usa Wikimedia Commons y guarda los metadatos de atribución disponibles en `data/sources.json`. Aun así, revisa la página de origen y las condiciones de cada recurso antes de redistribuirlo o usarlo comercialmente.
