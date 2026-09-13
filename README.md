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
│   ├── all-assets.json
│   └── sources.json
└── scripts/
    ├── build_index.py
    └── validate_assets.py
```

## Convención de nombres

Usa minúsculas, guiones y extensiones web comunes.

```text
uefa-champions-league.png
laliga.png
ilia-topuria.png
islam-makhachev.png
alex-pereira.png
```

Evita espacios, tildes y caracteres especiales.

## Uso mediante jsDelivr

### Peleadores UFC

```text
https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@main/ufc/fighters/ilia-topuria.png
```

### Competiciones

```text
https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@main/football/competitions/uefa-champions-league.png
```

Para producción, es recomendable usar un tag en vez de `main`, por ejemplo `@v1.0.0`.

## Generar índices JSON

```bash
python scripts/build_index.py
```

## Validar recursos

```bash
python scripts/validate_assets.py
```

## Licencias

La licencia del código no concede derechos sobre logos, marcas, fotografías o retratos de terceros. Antes de redistribuir cualquier recurso, verifica que tengas permiso o una licencia compatible.
