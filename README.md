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
├── data/
│   ├── football/
│   │   ├── competitions.json          # catálogo (fuente de verdad, se edita a mano)
│   │   ├── competitions-lookup.json   # generado: nombre normalizado → id
│   │   ├── clubs.json                 # catálogo de clubes (lo actualiza sync_clubs.py)
│   │   ├── clubs-mapping.json         # emparejamientos luukhopman → escudo, revisados
│   │   └── clubs-lookup.json          # generado: país → nombre normalizado → id
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

Escudos de los clubes de las 25 ligas europeas de [luukhopman/football-logos](https://github.com/luukhopman/football-logos): los de la temporada actual y los que han jugado en ellas desde 2021/22. Las imágenes vienen de [football-logos.cc](https://github.com/Leo4815162342/football-logos) (1024 px); si un club no está allí, se usa el PNG de luukhopman (139×181, la validación lo avisa como baja resolución).

Los escudos están en `football/clubs/<país>/<id>.png`. La carpeta no cambia cuando un club sube o baja de categoría.

`data/football/clubs.json`:

| Campo | Descripción |
|---|---|
| `id` | identificador estable; coincide con el nombre del archivo |
| `name` | nombre del club |
| `aliases` | otros nombres habituales |
| `country` | código ISO (`ES`, `GB-ENG`, `GB-SCT`…) |
| `league` | id de su liga en `competitions.json` esta temporada, o `null` si no juega en ninguna de las 25 |
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
