# Sports Assets CDN

Repositorio de recursos visuales deportivos preparado para usarse directamente desde GitHub o jsDelivr.

## Estructura

```text
sports-assets/
├── football/
│   └── competitions/
├── ufc/
│   ├── fighters/
│   └── logos/
├── data/
│   ├── competitions.json
│   ├── fighters.json
│   ├── ufc-logos.json
│   ├── ufc-fighters-seed.json
│   ├── all-assets.json
│   └── sources.json
└── scripts/
    ├── build_index.py
    ├── download_ufc_fighters.py
    └── validate_assets.py
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

```text
https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@main/football/competitions/uefa-champions-league.png
```

Para producción, es recomendable usar un tag en vez de `main`, por ejemplo `@v1.0.0`.

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

## Licencias

La licencia del código no concede derechos sobre logos, marcas, fotografías o retratos de terceros. El descargador de UFC usa Wikimedia Commons y guarda los metadatos de atribución disponibles en `data/sources.json`. Aun así, revisa la página de origen y las condiciones de cada recurso antes de redistribuirlo o usarlo comercialmente.
