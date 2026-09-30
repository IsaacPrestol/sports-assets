# Competiciones de fútbol por continente — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganizar los logos de competiciones por continente, conservar los collages aparte y publicar un catálogo JSON + índice de alias que una app externa pueda usar sin confundir logos.

**Architecture:** `data/football/competitions.json` es la fuente de verdad, mantenida a mano. Un módulo compartido `scripts/football_catalog.py` normaliza nombres, construye el índice de alias y valida el catálogo contra los archivos. `build_index.py` y `validate_assets.py` (y la CI) lo usan. `normalize_logo.py` prepara cada logo descargado.

**Tech Stack:** Python 3.12, Pillow, `unittest` de la librería estándar (pytest no está instalado), GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-30-football-competitions-design.md`

## Global Constraints

- Repositorio de trabajo: `C:\Users\Isaac\Downloads\sports-assets` (clon con git), rama `football-competitions-by-continent`. Todos los comandos se ejecutan desde esa raíz.
- Los commits terminan con la línea `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Logos: PNG con canal alfa, recortados al contenido, lado mayor ≤ 1024 px, sin ampliar, nombre `<id>.png`, sin marca de agua.
- Ruta del logo: `football/competitions/<continent>/<id>.png`. Ruta del collage: `football/collages/<id>.png`.
- `type` ∈ {`league`, `cup`, `super-cup`, `international`}; `scope` ∈ {`club`, `national-team`}; `continent` ∈ {`europe`, `south-america`, `north-america`, `asia`, `africa`, `oceania`, `world`}; `confederation` ∈ {`UEFA`, `CONMEBOL`, `CONCACAF`, `AFC`, `CAF`, `OFC`, `FIFA`}.
- Normalización de nombres: NFKD + quitar diacríticos → minúsculas → todo lo que no sea `a-z0-9` pasa a espacio → colapsar espacios y recortar.
- JSON generado: `indent=2`, `ensure_ascii=False`, salto de línea final, claves del lookup ordenadas.
- `data/sources.json` se indexa por ruta del asset y se escribe con `sort_keys=True`, como hace `download_ufc_fighters.py`.
- No se tocan los assets ni el descargador de UFC.
- Los mensajes de los scripts van en inglés, como los existentes.

## Review Focus

1. Un alias que al normalizarse queda vacío (p. ej. `"—"`) → la validación falla nombrando la competición. Test en Task 1.
2. Un alias genérico compartido por dos competiciones tras normalizar (p. ej. `"Supercopa"`) → la validación falla nombrando ambos ids. Test en Task 1.
3. Un logo PNG en modo `LA` o paleta con transparencia → se acepta; un PNG `RGB` con fondo blanco → se rechaza. Tests en Task 2.
4. Una imagen presente en `football/competitions/…` o `football/collages/` sin entrada en el catálogo (p. ej. con `logo: null`) → error, no se ignora en silencio. Test en Task 2.
5. Pasar a `normalize_logo.py` una imagen sin transparencia o totalmente transparente → error claro y no se escribe ningún archivo de salida. Tests en Task 4.

## Estructura de archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `scripts/football_catalog.py` | Crear | Constantes, carga, normalización, lookup, validación del catálogo |
| `scripts/normalize_logo.py` | Crear | Recortar y redimensionar un logo descargado |
| `scripts/build_index.py` | Modificar | Generar el lookup y `all-assets.json` desde el catálogo |
| `scripts/validate_assets.py` | Modificar | Recorrer subcarpetas y ejecutar la validación del catálogo |
| `tests/test_football_catalog.py` | Crear | Tests de normalización, lookup y validación |
| `tests/test_normalize_logo.py` | Crear | Tests del normalizador |
| `requirements.txt` | Crear | `Pillow>=10.0` |
| `data/football/competitions.json` | Crear | Catálogo (fuente de verdad) |
| `data/football/competitions-lookup.json` | Generado | Alias normalizado → id |
| `data/competitions.json` | Eliminar | Sustituido por el catálogo |
| `.github/workflows/validate.yml` | Modificar | Instalar dependencias y ejecutar tests |
| `README.md` | Modificar | Nueva estructura y uso desde la app |

## Procedimiento para obtener un logo

Las Tasks 6–10 aplican estos pasos a cada competición de su lote.

1. Buscar con WebSearch, p. ej. `"<name> logo png transparent"` y `"<name> logo svg"`. Orden de preferencia: web oficial o press kit → página `File:` de Wikimedia Commons o Wikipedia → repositorios de logos que sirvan el archivo sin marca de agua. Comprobar que el logo es el **actual** (p. ej. LaLiga usa desde 2023 el logo rojo "LALIGA"; Ligue 1 cambió de logo en 2024; la Concacaf Champions Cup, en 2024).
2. Descargar a `.cache/logos/` (ya está en `.gitignore`):
   ```bash
   mkdir -p .cache/logos
   curl -L -A "sports-assets-logo-fetch/1.0 (https://github.com/IsaacPrestol/sports-assets)" -o .cache/logos/<id>.<ext> "<url>"
   ```
   Si la fuente es un SVG de Wikimedia, descargar el PNG renderizado: `https://upload.wikimedia.org/wikipedia/commons/thumb/<x>/<xy>/<Archivo>.svg/2048px-<Archivo>.svg.png` (misma ruta `<x>/<xy>` que el SVG; para archivos de `wikipedia/en`, sustituir `commons` por `en`). Si solo existe un SVG fuera de Wikimedia, renderizarlo con Edge en modo headless y fondo transparente:
   ```bash
   printf '<html><body style="margin:0"><img src="%s" style="width:2048px"></body></html>' "file:///C:/Users/Isaac/Downloads/sports-assets/.cache/logos/<id>.svg" > .cache/logos/<id>.html
   "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless --disable-gpu --hide-scrollbars --default-background-color=00000000 --window-size=2048,2048 --screenshot="C:/Users/Isaac/Downloads/sports-assets/.cache/logos/<id>.png" "file:///C:/Users/Isaac/Downloads/sports-assets/.cache/logos/<id>.html"
   ```
3. Revisar visualmente la descarga con la herramienta Read. Descartarla si tiene marca de agua, fondo opaco, es un logo antiguo o está pixelada (lado mayor < 400 px).
4. Normalizar:
   ```bash
   python scripts/normalize_logo.py .cache/logos/<id>.png football/competitions/<continent>/<id>.png
   ```
5. Revisar visualmente el resultado con Read.
6. En `data/football/competitions.json`, poner en la entrada `"logo": "football/competitions/<continent>/<id>.png"`.
7. Registrar el origen:
   ```bash
   python - <<'EOF'
   import json, pathlib
   p = pathlib.Path("data/sources.json")
   s = json.loads(p.read_text(encoding="utf-8"))
   s["football/competitions/<continent>/<id>.png"] = {
       "url": "<url de la página o archivo de origen>",
       "retrieved": "<YYYY-MM-DD>",
       "license": None,  # p. ej. "Public domain (PD-textlogo)" si la fuente lo indica
       "notes": None,    # p. ej. "Rendered from SVG at 2048px"
   }
   p.write_text(json.dumps(s, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
   EOF
   ```
8. Ejecutar `python scripts/validate_assets.py && python scripts/build_index.py`. Debe terminar con `Validation passed.`
9. Si no aparece un logo aceptable tras buscar en las tres fuentes, dejar `logo: null` y anotarlo para el informe final.

---

### Task 1: Módulo del catálogo — normalización y lookup

**Files:**
- Create: `scripts/football_catalog.py`
- Create: `requirements.txt`
- Test: `tests/test_football_catalog.py`

**Interfaces:**
- Produces:
  - `normalize_name(value: str) -> str`
  - `build_lookup(competitions: list[dict]) -> tuple[dict[str, str], list[str]]`: devuelve (lookup ordenado, errores)
  - `competition_assets(competitions: list[dict]) -> dict[str, dict]`: `{id: {"name", "path"}}` solo para entradas con `logo`
  - `load_catalog(path: Path = CATALOG_FILE) -> dict`
  - Constantes `ROOT`, `CATALOG_FILE`, `LOOKUP_FILE`, `COMPETITIONS_DIR`, `COLLAGES_DIR`, `TYPES`, `SCOPES`, `CONTINENTS`, `CONFEDERATIONS`, `REQUIRED_FIELDS`, `ID_RE`

- [ ] **Step 1: Crear `requirements.txt`**

```text
Pillow>=10.0
```

- [ ] **Step 2: Escribir los tests que fallan**

`tests/test_football_catalog.py`:

```python
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from football_catalog import build_lookup, competition_assets, normalize_name


def make_entry(**overrides):
    entry = {
        "id": "laliga",
        "name": "LaLiga",
        "aliases": ["La Liga"],
        "type": "league",
        "scope": "club",
        "continent": "europe",
        "confederation": "UEFA",
        "country": "ES",
        "logo": None,
        "collage": None,
    }
    entry.update(overrides)
    return entry


class NormalizeNameTest(unittest.TestCase):
    def test_lowercases_and_keeps_words(self):
        self.assertEqual(normalize_name("LaLiga EA Sports"), "laliga ea sports")

    def test_strips_accents(self):
        self.assertEqual(normalize_name("Primera División"), "primera division")

    def test_punctuation_and_spacing_become_single_spaces(self):
        self.assertEqual(normalize_name("  Trophée   des-Champions "), "trophee des champions")
        self.assertEqual(normalize_name("DFB-Pokal"), "dfb pokal")

    def test_only_symbols_normalizes_to_empty(self):
        self.assertEqual(normalize_name("—!!"), "")


class BuildLookupTest(unittest.TestCase):
    def test_includes_id_name_and_aliases(self):
        lookup, errors = build_lookup([make_entry(aliases=["La Liga", "Primera División"])])
        self.assertEqual(errors, [])
        self.assertEqual(
            lookup,
            {"la liga": "laliga", "laliga": "laliga", "primera division": "laliga"},
        )

    def test_keys_are_sorted(self):
        lookup, _ = build_lookup([
            make_entry(),
            make_entry(id="serie-a", name="Serie A", aliases=["Italian Serie A"], country="IT"),
        ])
        self.assertEqual(list(lookup), sorted(lookup))

    def test_repeated_name_within_same_competition_is_fine(self):
        _, errors = build_lookup([make_entry(aliases=["LaLiga", "laliga"])])
        self.assertEqual(errors, [])

    def test_collision_between_competitions_is_an_error(self):
        _, errors = build_lookup([
            make_entry(id="supercopa-de-espana", name="Supercopa de España", aliases=["Supercopa"]),
            make_entry(id="uefa-super-cup", name="UEFA Super Cup", aliases=["Supercopa"]),
        ])
        self.assertEqual(len(errors), 1)
        self.assertIn("supercopa-de-espana", errors[0])
        self.assertIn("uefa-super-cup", errors[0])

    def test_alias_that_normalizes_to_empty_is_an_error(self):
        _, errors = build_lookup([make_entry(aliases=["—"])])
        self.assertEqual(len(errors), 1)
        self.assertIn("laliga", errors[0])


class CompetitionAssetsTest(unittest.TestCase):
    def test_only_entries_with_logo(self):
        assets = competition_assets([
            make_entry(logo="football/competitions/europe/laliga.png"),
            make_entry(id="serie-a", name="Serie A", aliases=[], logo=None),
        ])
        self.assertEqual(
            assets,
            {"laliga": {"name": "LaLiga", "path": "football/competitions/europe/laliga.png"}},
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Ejecutar y comprobar que fallan**

Run: `python -m unittest discover -s tests -v`
Expected: ERROR `ModuleNotFoundError: No module named 'football_catalog'`

- [ ] **Step 4: Implementación mínima**

`scripts/football_catalog.py`:

```python
"""Shared helpers for the football competitions catalog."""

from pathlib import Path
import json
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
CATALOG_FILE = ROOT / "data" / "football" / "competitions.json"
LOOKUP_FILE = ROOT / "data" / "football" / "competitions-lookup.json"
COMPETITIONS_DIR = "football/competitions"
COLLAGES_DIR = "football/collages"

TYPES = {"league", "cup", "super-cup", "international"}
SCOPES = {"club", "national-team"}
CONTINENTS = {"europe", "south-america", "north-america", "asia", "africa", "oceania", "world"}
CONFEDERATIONS = {"UEFA", "CONMEBOL", "CONCACAF", "AFC", "CAF", "OFC", "FIFA"}
REQUIRED_FIELDS = (
    "id", "name", "aliases", "type", "scope",
    "continent", "confederation", "country", "logo", "collage",
)
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def load_catalog(path: Path = CATALOG_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", without_marks.lower()).split())


def build_lookup(competitions: list[dict]) -> tuple[dict[str, str], list[str]]:
    lookup: dict[str, str] = {}
    errors: list[str] = []
    for competition in competitions:
        competition_id = competition["id"]
        for raw in [competition_id, competition["name"], *competition["aliases"]]:
            key = normalize_name(raw)
            if not key:
                errors.append(f"Name '{raw}' of '{competition_id}' normalizes to an empty string")
                continue
            owner = lookup.setdefault(key, competition_id)
            if owner != competition_id:
                errors.append(
                    f"Name '{raw}' of '{competition_id}' collides with '{owner}' (key '{key}')"
                )
    return dict(sorted(lookup.items())), errors


def competition_assets(competitions: list[dict]) -> dict[str, dict]:
    return {
        competition["id"]: {"name": competition["name"], "path": competition["logo"]}
        for competition in competitions
        if competition["logo"]
    }
```

- [ ] **Step 5: Ejecutar y comprobar que pasan**

Run: `python -m unittest discover -s tests -v`
Expected: 10 tests, `OK`

- [ ] **Step 6: Commit**

```bash
git add requirements.txt scripts/football_catalog.py tests/test_football_catalog.py
git commit -m "Add football catalog name normalization and alias lookup

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Validación del catálogo contra los archivos

**Files:**
- Modify: `scripts/football_catalog.py` (añadir al final; import de Pillow arriba)
- Test: `tests/test_football_catalog.py` (añadir clases)

**Interfaces:**
- Consumes: `build_lookup`, constantes de Task 1
- Produces:
  - `has_alpha(path: Path) -> bool`
  - `validate_catalog(root: Path, catalog: object) -> tuple[list[str], list[str]]`: devuelve (errores, avisos)

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a los imports de `tests/test_football_catalog.py`:

```python
import tempfile

from PIL import Image

from football_catalog import has_alpha, validate_catalog
```

Añadir antes de `if __name__ == "__main__":`:

```python
def save_png(root: Path, relative: str, mode: str = "RGBA", **save_args) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new(mode, (8, 8)).save(path, **save_args)
    return path


LOGO = "football/competitions/europe/laliga.png"
COLLAGE = "football/collages/laliga.png"


class HasAlphaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_rgba_and_la_have_alpha(self):
        self.assertTrue(has_alpha(save_png(self.root, "a.png", "RGBA")))
        self.assertTrue(has_alpha(save_png(self.root, "b.png", "LA")))

    def test_palette_with_transparency_has_alpha(self):
        self.assertTrue(has_alpha(save_png(self.root, "c.png", "P", transparency=0)))

    def test_rgb_has_no_alpha(self):
        self.assertFalse(has_alpha(save_png(self.root, "d.png", "RGB")))

    def test_non_image_has_no_alpha(self):
        path = self.root / "e.png"
        path.write_text("not an image")
        self.assertFalse(has_alpha(path))


class ValidateCatalogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def validate(self, *entries):
        return validate_catalog(self.root, {"version": 1, "competitions": list(entries)})

    def test_valid_entry_with_logo_and_collage(self):
        save_png(self.root, LOGO)
        save_png(self.root, COLLAGE, "RGB")
        errors, warnings = self.validate(make_entry(logo=LOGO, collage=COLLAGE))
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_missing_logo_is_only_a_warning(self):
        errors, warnings = self.validate(make_entry())
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("laliga", warnings[0])

    def test_catalog_without_competitions_list(self):
        errors, _ = validate_catalog(self.root, {"version": 1})
        self.assertEqual(len(errors), 1)
        errors, _ = validate_catalog(self.root, [])
        self.assertEqual(len(errors), 1)

    def test_missing_field(self):
        entry = make_entry()
        del entry["confederation"]
        errors, _ = self.validate(entry)
        self.assertEqual(len(errors), 1)
        self.assertIn("confederation", errors[0])

    def test_invalid_enum_values(self):
        errors, _ = self.validate(make_entry(continent="europa", type=["league"]))
        self.assertEqual(len(errors), 2)

    def test_invalid_id(self):
        errors, _ = self.validate(make_entry(id="La Liga"))
        self.assertTrue(any("Invalid id" in e for e in errors))

    def test_duplicate_id(self):
        errors, _ = self.validate(make_entry(), make_entry(name="La Liga 2", aliases=[]))
        self.assertTrue(any("Duplicate id: 'laliga'" in e for e in errors))

    def test_logo_in_wrong_continent_folder(self):
        wrong = "football/competitions/world/laliga.png"
        save_png(self.root, wrong)
        errors, _ = self.validate(make_entry(logo=wrong))
        self.assertTrue(any("must be" in e for e in errors))

    def test_logo_file_missing(self):
        errors, _ = self.validate(make_entry(logo=LOGO))
        self.assertTrue(any("not found" in e for e in errors))

    def test_logo_without_alpha(self):
        save_png(self.root, LOGO, "RGB")
        errors, _ = self.validate(make_entry(logo=LOGO))
        self.assertTrue(any("alpha" in e for e in errors))

    def test_la_logo_is_accepted(self):
        save_png(self.root, LOGO, "LA")
        errors, _ = self.validate(make_entry(logo=LOGO))
        self.assertEqual(errors, [])

    def test_collage_file_missing(self):
        errors, _ = self.validate(make_entry(collage=COLLAGE))
        self.assertTrue(any("not found" in e for e in errors))

    def test_unreferenced_image_is_an_error(self):
        save_png(self.root, COLLAGE, "RGB")
        errors, _ = self.validate(make_entry(collage=None))
        self.assertTrue(any("not referenced" in e and COLLAGE in e for e in errors))

    def test_image_outside_continent_folder_is_an_error(self):
        save_png(self.root, "football/competitions/laliga.png")
        errors, _ = self.validate(make_entry())
        self.assertTrue(any("outside a continent folder" in e for e in errors))

    def test_hidden_files_are_ignored(self):
        (self.root / "football/competitions").mkdir(parents=True)
        (self.root / "football/competitions/.gitkeep").write_text("")
        errors, _ = self.validate(make_entry())
        self.assertEqual(errors, [])

    def test_alias_collision_is_reported(self):
        errors, _ = self.validate(
            make_entry(aliases=["Supercopa"]),
            make_entry(id="uefa-super-cup", name="UEFA Super Cup", aliases=["Supercopa"],
                       type="super-cup", country=None),
        )
        self.assertTrue(any("collides" in e for e in errors))
```

- [ ] **Step 2: Ejecutar y comprobar que fallan**

Run: `python -m unittest discover -s tests -v`
Expected: ERROR `ImportError: cannot import name 'has_alpha'`

- [ ] **Step 3: Implementación**

En `scripts/football_catalog.py`, añadir tras `import unicodedata`:

```python

from PIL import Image
```

Y al final del archivo:

```python
def has_alpha(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            return "A" in image.getbands() or "transparency" in image.info
    except OSError:
        return False


def _enum_error(label: str, field: str, value, allowed: set) -> str | None:
    if not isinstance(value, str) or value not in allowed:
        return f"'{label}' has invalid {field}: {value!r}"
    return None


def _entry_errors(entry) -> list[str]:
    if not isinstance(entry, dict):
        return [f"Catalog entry is not an object: {entry!r}"]
    label = entry.get("id", "<no id>")
    missing = [field for field in REQUIRED_FIELDS if field not in entry]
    if missing:
        return [f"'{label}' is missing field(s): {', '.join(missing)}"]

    errors = []
    if not isinstance(entry["id"], str) or not ID_RE.match(entry["id"]):
        errors.append(f"Invalid id: {entry['id']!r}")
    if not isinstance(entry["name"], str) or not entry["name"].strip():
        errors.append(f"'{label}' has an empty name")
    if not isinstance(entry["aliases"], list) or not all(isinstance(a, str) for a in entry["aliases"]):
        errors.append(f"'{label}' aliases must be a list of strings")
    for field, allowed in (
        ("type", TYPES),
        ("scope", SCOPES),
        ("continent", CONTINENTS),
        ("confederation", CONFEDERATIONS),
    ):
        error = _enum_error(label, field, entry[field], allowed)
        if error:
            errors.append(error)
    for field in ("country", "logo", "collage"):
        if entry[field] is not None and not isinstance(entry[field], str):
            errors.append(f"'{label}' {field} must be a string or null")
    return errors


def _file_errors(root: Path, competitions: list[dict]) -> tuple[list[str], list[str], set[str]]:
    errors, warnings, referenced = [], [], set()
    for competition in competitions:
        competition_id = competition["id"]

        logo = competition["logo"]
        if logo is None:
            warnings.append(f"'{competition_id}' has no logo yet")
        else:
            referenced.add(logo)
            expected = f"{COMPETITIONS_DIR}/{competition['continent']}/{competition_id}.png"
            if logo != expected:
                errors.append(f"'{competition_id}' logo must be '{expected}', got '{logo}'")
            elif not (root / logo).is_file():
                errors.append(f"'{competition_id}' logo not found: {logo}")
            elif not has_alpha(root / logo):
                errors.append(f"'{competition_id}' logo has no alpha channel: {logo}")

        collage = competition["collage"]
        if collage is not None:
            referenced.add(collage)
            expected = f"{COLLAGES_DIR}/{competition_id}.png"
            if collage != expected:
                errors.append(f"'{competition_id}' collage must be '{expected}', got '{collage}'")
            elif not (root / collage).is_file():
                errors.append(f"'{competition_id}' collage not found: {collage}")
    return errors, warnings, referenced


def _orphan_errors(root: Path, referenced: set[str]) -> list[str]:
    errors = []
    competitions_dir = root / COMPETITIONS_DIR
    for folder in (competitions_dir, root / COLLAGES_DIR):
        if not folder.exists():
            continue
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            relative = path.relative_to(root).as_posix()
            if path.parent == competitions_dir:
                errors.append(f"Competition logo outside a continent folder: {relative}")
            elif relative not in referenced:
                errors.append(f"Image not referenced by the catalog: {relative}")
    return errors


def validate_catalog(root: Path, catalog) -> tuple[list[str], list[str]]:
    competitions = catalog.get("competitions") if isinstance(catalog, dict) else None
    if not isinstance(competitions, list):
        return ["Catalog must be an object with a 'competitions' list"], []

    errors = [error for entry in competitions for error in _entry_errors(entry)]
    if errors:
        return errors, []

    ids = [competition["id"] for competition in competitions]
    errors.extend(f"Duplicate id: '{i}'" for i in sorted({i for i in ids if ids.count(i) > 1}))

    file_errors, warnings, referenced = _file_errors(root, competitions)
    errors.extend(file_errors)
    errors.extend(_orphan_errors(root, referenced))
    errors.extend(build_lookup(competitions)[1])
    return errors, warnings
```

- [ ] **Step 4: Ejecutar y comprobar que pasan**

Run: `python -m unittest discover -s tests -v`
Expected: 30 tests, `OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/football_catalog.py tests/test_football_catalog.py
git commit -m "Validate football catalog against image files

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Reorganizar archivos y escribir el catálogo

**Files:**
- Move: 11 collages → `football/collages/`; 6 logos → carpetas de continente
- Delete: `football/competitions/.gitkeep`
- Create: `data/football/competitions.json`

**Interfaces:**
- Consumes: `load_catalog`, `validate_catalog`, `ROOT` (Task 1–2)
- Produces: el catálogo con 36 entradas que usan las Tasks 4 y 6–10

- [ ] **Step 1: Mover los collages**

```bash
mkdir -p football/collages
for id in brasileirao-serie-a bundesliga eredivisie laliga liga-mx liga-portugal \
          liga-profesional-argentina ligue-1 mls premier-league serie-a; do
  git mv "football/competitions/$id.png" "football/collages/$id.png"
done
```

- [ ] **Step 2: Mover los logos sueltos a su continente**

```bash
mkdir -p football/competitions/europe football/competitions/south-america football/competitions/world
for id in uefa-champions-league uefa-europa-league uefa-conference-league copa-del-rey; do
  git mv "football/competitions/$id.png" "football/competitions/europe/$id.png"
done
git mv football/competitions/copa-libertadores.png football/competitions/south-america/copa-libertadores.png
git mv football/competitions/fifa-club-world-cup.png football/competitions/world/fifa-club-world-cup.png
git rm -q football/competitions/.gitkeep
ls football/competitions
```

Expected: `europe  south-america  world` (ningún `.png` suelto).

- [ ] **Step 3: Escribir `data/football/competitions.json`**

```json
{
  "version": 1,
  "competitions": [
    {
      "id": "uefa-champions-league",
      "name": "UEFA Champions League",
      "aliases": ["Champions League", "UCL", "Liga de Campeones", "Liga de Campeones de la UEFA"],
      "type": "international",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": null,
      "logo": "football/competitions/europe/uefa-champions-league.png",
      "collage": null
    },
    {
      "id": "uefa-europa-league",
      "name": "UEFA Europa League",
      "aliases": ["Europa League", "UEL", "Liga Europa"],
      "type": "international",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": null,
      "logo": "football/competitions/europe/uefa-europa-league.png",
      "collage": null
    },
    {
      "id": "uefa-conference-league",
      "name": "UEFA Conference League",
      "aliases": ["Conference League", "UECL", "UEFA Europa Conference League", "Liga Conferencia"],
      "type": "international",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": null,
      "logo": "football/competitions/europe/uefa-conference-league.png",
      "collage": null
    },
    {
      "id": "uefa-super-cup",
      "name": "UEFA Super Cup",
      "aliases": ["Supercopa de Europa", "European Super Cup"],
      "type": "super-cup",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": null,
      "logo": null,
      "collage": null
    },
    {
      "id": "premier-league",
      "name": "Premier League",
      "aliases": ["English Premier League", "EPL", "Barclays Premier League"],
      "type": "league",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "GB-ENG",
      "logo": null,
      "collage": "football/collages/premier-league.png"
    },
    {
      "id": "laliga",
      "name": "LaLiga",
      "aliases": ["La Liga", "LaLiga EA Sports", "Primera División", "Spanish La Liga"],
      "type": "league",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "ES",
      "logo": null,
      "collage": "football/collages/laliga.png"
    },
    {
      "id": "serie-a",
      "name": "Serie A",
      "aliases": ["Italian Serie A", "Serie A Enilive", "Serie A TIM"],
      "type": "league",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "IT",
      "logo": null,
      "collage": "football/collages/serie-a.png"
    },
    {
      "id": "bundesliga",
      "name": "Bundesliga",
      "aliases": ["German Bundesliga", "1. Bundesliga"],
      "type": "league",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "DE",
      "logo": null,
      "collage": "football/collages/bundesliga.png"
    },
    {
      "id": "ligue-1",
      "name": "Ligue 1",
      "aliases": ["French Ligue 1", "Ligue 1 McDonald's"],
      "type": "league",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "FR",
      "logo": null,
      "collage": "football/collages/ligue-1.png"
    },
    {
      "id": "eredivisie",
      "name": "Eredivisie",
      "aliases": ["Dutch Eredivisie", "VriendenLoterij Eredivisie"],
      "type": "league",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "NL",
      "logo": null,
      "collage": "football/collages/eredivisie.png"
    },
    {
      "id": "liga-portugal",
      "name": "Liga Portugal",
      "aliases": ["Liga Portugal Betclic", "Primeira Liga", "Portuguese Primeira Liga"],
      "type": "league",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "PT",
      "logo": null,
      "collage": "football/collages/liga-portugal.png"
    },
    {
      "id": "fa-cup",
      "name": "FA Cup",
      "aliases": ["Emirates FA Cup", "The FA Cup"],
      "type": "cup",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "GB-ENG",
      "logo": null,
      "collage": null
    },
    {
      "id": "efl-cup",
      "name": "EFL Cup",
      "aliases": ["Carabao Cup", "League Cup", "English League Cup"],
      "type": "cup",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "GB-ENG",
      "logo": null,
      "collage": null
    },
    {
      "id": "community-shield",
      "name": "FA Community Shield",
      "aliases": ["Community Shield"],
      "type": "super-cup",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "GB-ENG",
      "logo": null,
      "collage": null
    },
    {
      "id": "copa-del-rey",
      "name": "Copa del Rey",
      "aliases": ["Spanish Cup", "King's Cup"],
      "type": "cup",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "ES",
      "logo": "football/competitions/europe/copa-del-rey.png",
      "collage": null
    },
    {
      "id": "supercopa-de-espana",
      "name": "Supercopa de España",
      "aliases": ["Spanish Super Cup", "Supercopa de Espana"],
      "type": "super-cup",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "ES",
      "logo": null,
      "collage": null
    },
    {
      "id": "coppa-italia",
      "name": "Coppa Italia",
      "aliases": ["Italian Cup", "Coppa Italia Frecciarossa"],
      "type": "cup",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "IT",
      "logo": null,
      "collage": null
    },
    {
      "id": "supercoppa-italiana",
      "name": "Supercoppa Italiana",
      "aliases": ["Italian Super Cup", "Supercopa de Italia"],
      "type": "super-cup",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "IT",
      "logo": null,
      "collage": null
    },
    {
      "id": "dfb-pokal",
      "name": "DFB-Pokal",
      "aliases": ["DFB Cup", "German Cup", "Copa de Alemania"],
      "type": "cup",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "DE",
      "logo": null,
      "collage": null
    },
    {
      "id": "dfl-supercup",
      "name": "DFL-Supercup",
      "aliases": ["German Super Cup", "Franz Beckenbauer Supercup", "Supercopa de Alemania"],
      "type": "super-cup",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "DE",
      "logo": null,
      "collage": null
    },
    {
      "id": "coupe-de-france",
      "name": "Coupe de France",
      "aliases": ["French Cup", "Copa de Francia"],
      "type": "cup",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "FR",
      "logo": null,
      "collage": null
    },
    {
      "id": "trophee-des-champions",
      "name": "Trophée des Champions",
      "aliases": ["French Super Cup", "Supercopa de Francia"],
      "type": "super-cup",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "FR",
      "logo": null,
      "collage": null
    },
    {
      "id": "uefa-euro",
      "name": "UEFA European Championship",
      "aliases": ["UEFA Euro", "Euro", "Eurocopa", "European Championship"],
      "type": "international",
      "scope": "national-team",
      "continent": "europe",
      "confederation": "UEFA",
      "country": null,
      "logo": null,
      "collage": null
    },
    {
      "id": "uefa-nations-league",
      "name": "UEFA Nations League",
      "aliases": ["Nations League", "Liga de Naciones", "Liga de Naciones de la UEFA"],
      "type": "international",
      "scope": "national-team",
      "continent": "europe",
      "confederation": "UEFA",
      "country": null,
      "logo": null,
      "collage": null
    },
    {
      "id": "copa-libertadores",
      "name": "CONMEBOL Libertadores",
      "aliases": ["Copa Libertadores", "Libertadores", "Copa CONMEBOL Libertadores"],
      "type": "international",
      "scope": "club",
      "continent": "south-america",
      "confederation": "CONMEBOL",
      "country": null,
      "logo": "football/competitions/south-america/copa-libertadores.png",
      "collage": null
    },
    {
      "id": "copa-sudamericana",
      "name": "CONMEBOL Sudamericana",
      "aliases": ["Copa Sudamericana", "Sudamericana", "Copa CONMEBOL Sudamericana"],
      "type": "international",
      "scope": "club",
      "continent": "south-america",
      "confederation": "CONMEBOL",
      "country": null,
      "logo": null,
      "collage": null
    },
    {
      "id": "brasileirao-serie-a",
      "name": "Campeonato Brasileiro Série A",
      "aliases": ["Brasileirão", "Brasileirão Série A", "Brazilian Serie A", "Série A Brasil"],
      "type": "league",
      "scope": "club",
      "continent": "south-america",
      "confederation": "CONMEBOL",
      "country": "BR",
      "logo": null,
      "collage": "football/collages/brasileirao-serie-a.png"
    },
    {
      "id": "liga-profesional-argentina",
      "name": "Liga Profesional de Fútbol",
      "aliases": ["Liga Profesional Argentina", "Liga Profesional", "Primera División Argentina", "Argentine Primera División"],
      "type": "league",
      "scope": "club",
      "continent": "south-america",
      "confederation": "CONMEBOL",
      "country": "AR",
      "logo": null,
      "collage": "football/collages/liga-profesional-argentina.png"
    },
    {
      "id": "copa-america",
      "name": "Copa América",
      "aliases": ["CONMEBOL Copa América", "Copa America"],
      "type": "international",
      "scope": "national-team",
      "continent": "south-america",
      "confederation": "CONMEBOL",
      "country": null,
      "logo": null,
      "collage": null
    },
    {
      "id": "liga-mx",
      "name": "Liga MX",
      "aliases": ["Liga BBVA MX", "Mexican Liga MX", "Primera División de México"],
      "type": "league",
      "scope": "club",
      "continent": "north-america",
      "confederation": "CONCACAF",
      "country": "MX",
      "logo": null,
      "collage": "football/collages/liga-mx.png"
    },
    {
      "id": "mls",
      "name": "Major League Soccer",
      "aliases": ["MLS"],
      "type": "league",
      "scope": "club",
      "continent": "north-america",
      "confederation": "CONCACAF",
      "country": "US",
      "logo": null,
      "collage": "football/collages/mls.png"
    },
    {
      "id": "concacaf-champions-cup",
      "name": "Concacaf Champions Cup",
      "aliases": ["CONCACAF Champions League", "Concacaf Champions League", "Copa de Campeones de la Concacaf"],
      "type": "international",
      "scope": "club",
      "continent": "north-america",
      "confederation": "CONCACAF",
      "country": null,
      "logo": null,
      "collage": null
    },
    {
      "id": "concacaf-gold-cup",
      "name": "Concacaf Gold Cup",
      "aliases": ["Gold Cup", "Copa Oro", "Copa Oro de la Concacaf"],
      "type": "international",
      "scope": "national-team",
      "continent": "north-america",
      "confederation": "CONCACAF",
      "country": null,
      "logo": null,
      "collage": null
    },
    {
      "id": "saudi-pro-league",
      "name": "Saudi Pro League",
      "aliases": ["Roshn Saudi League", "Saudi Professional League", "Liga Profesional Saudí"],
      "type": "league",
      "scope": "club",
      "continent": "asia",
      "confederation": "AFC",
      "country": "SA",
      "logo": null,
      "collage": null
    },
    {
      "id": "fifa-world-cup",
      "name": "FIFA World Cup",
      "aliases": ["World Cup", "Copa Mundial", "Mundial", "Copa del Mundo"],
      "type": "international",
      "scope": "national-team",
      "continent": "world",
      "confederation": "FIFA",
      "country": null,
      "logo": null,
      "collage": null
    },
    {
      "id": "fifa-club-world-cup",
      "name": "FIFA Club World Cup",
      "aliases": ["Club World Cup", "Mundial de Clubes", "Copa Mundial de Clubes"],
      "type": "international",
      "scope": "club",
      "continent": "world",
      "confederation": "FIFA",
      "country": null,
      "logo": "football/competitions/world/fifa-club-world-cup.png",
      "collage": null
    }
  ]
}
```

- [ ] **Step 4: Validar el catálogo**

Run:
```bash
python -c "import sys; sys.path.insert(0, 'scripts'); from football_catalog import *; c = load_catalog(); e, w = validate_catalog(ROOT, c); print(len(c['competitions']), 'entries'); print('\n'.join(e) or 'no errors'); print(len(w), 'warnings')"
```
Expected: `36 entries`, `no errors`, `30 warnings`.

- [ ] **Step 5: Commit**

```bash
git add -A football data/football/competitions.json
git commit -m "Move competition logos into continent folders and add catalog

Collages from FootyLogos move to football/collages unchanged.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Conectar el catálogo a `build_index.py`, `validate_assets.py` y la CI

**Files:**
- Modify: `scripts/build_index.py` (archivo completo)
- Modify: `scripts/validate_assets.py` (archivo completo)
- Modify: `.github/workflows/validate.yml`
- Delete: `data/competitions.json`
- Generated: `data/football/competitions-lookup.json`, `data/all-assets.json`

**Interfaces:**
- Consumes: `load_catalog`, `build_lookup`, `competition_assets`, `validate_catalog`, `CATALOG_FILE`, `LOOKUP_FILE`

- [ ] **Step 1: Sustituir `scripts/build_index.py`**

```python
from pathlib import Path
import json
import sys

from football_catalog import LOOKUP_FILE, build_lookup, competition_assets, load_catalog

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

COLLECTIONS = {
    "fighters": ROOT / "ufc" / "fighters",
    "ufc-logos": ROOT / "ufc" / "logos",
}

ALLOWED = {".png", ".webp", ".jpg", ".jpeg", ".svg"}


def pretty_name(slug: str) -> str:
    special = {
        "ufc": "UFC",
        "uefa": "UEFA",
        "fifa": "FIFA",
        "afc": "AFC",
        "caf": "CAF",
        "concacaf": "CONCACAF",
        "conmebol": "CONMEBOL",
        "mls": "MLS",
    }
    return " ".join(special.get(word, word.capitalize()) for word in slug.split("-"))


def build_collection(folder: Path):
    result = {}
    if not folder.exists():
        return result

    for file in sorted(folder.iterdir()):
        if not file.is_file() or file.name.startswith("."):
            continue
        if file.suffix.lower() not in ALLOWED:
            continue

        slug = file.stem
        result[slug] = {
            "name": pretty_name(slug),
            "path": file.relative_to(ROOT).as_posix(),
        }
    return result


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    competitions = load_catalog()["competitions"]
    lookup, errors = build_lookup(competitions)
    if errors:
        for error in errors:
            print("ERROR:", error)
        sys.exit(1)
    write_json(LOOKUP_FILE, lookup)

    all_assets = {
        "fighters": build_collection(COLLECTIONS["fighters"]),
        "competitions": competition_assets(competitions),
        "ufc-logos": build_collection(COLLECTIONS["ufc-logos"]),
    }
    for collection in COLLECTIONS:
        write_json(DATA / f"{collection}.json", all_assets[collection])
    write_json(DATA / "all-assets.json", all_assets)

    print("Indexes generated:")
    for collection, items in all_assets.items():
        print(f"  {collection}: {len(items)} asset(s)")
    print(f"  competition lookup: {len(lookup)} name(s)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Sustituir `scripts/validate_assets.py`**

```python
from pathlib import Path
import re
import struct
import sys

from football_catalog import CATALOG_FILE, load_catalog, validate_catalog

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIRS = [
    ROOT / "football" / "competitions",
    ROOT / "football" / "collages",
    ROOT / "ufc" / "fighters",
    ROOT / "ufc" / "logos",
]
ALLOWED = {".png", ".webp", ".jpg", ".jpeg", ".svg"}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.(?:png|webp|jpg|jpeg|svg)$")
MAX_BYTES = 5 * 1024 * 1024


def png_dimensions(path: Path):
    try:
        with path.open("rb") as f:
            header = f.read(24)
        if header[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        return struct.unpack(">II", header[16:24])
    except OSError:
        return None


def check_files(errors: list, warnings: list) -> None:
    for folder in ASSET_DIRS:
        if not folder.exists():
            continue

        seen = {}
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue

            if path.suffix.lower() not in ALLOWED:
                errors.append(f"Unsupported extension: {path.relative_to(ROOT)}")
                continue

            if not NAME_RE.match(path.name):
                errors.append(f"Invalid filename: {path.relative_to(ROOT)}")

            slug = path.stem
            if slug in seen:
                warnings.append(
                    f"Repeated slug '{slug}': {seen[slug].relative_to(ROOT)} and {path.relative_to(ROOT)}"
                )
            else:
                seen[slug] = path

            if path.stat().st_size > MAX_BYTES:
                warnings.append(f"Large asset (>5 MB): {path.relative_to(ROOT)}")

            if path.suffix.lower() == ".png":
                dims = png_dimensions(path)
                if dims:
                    w, h = dims
                    if w > 3000 or h > 3000:
                        warnings.append(
                            f"Very large dimensions ({w}x{h}): {path.relative_to(ROOT)}"
                        )


def check_catalog(errors: list, warnings: list) -> None:
    try:
        catalog = load_catalog()
    except (OSError, ValueError) as exc:
        errors.append(f"Cannot read {CATALOG_FILE.relative_to(ROOT).as_posix()}: {exc}")
        return
    catalog_errors, catalog_warnings = validate_catalog(ROOT, catalog)
    errors.extend(catalog_errors)
    warnings.extend(catalog_warnings)


def main():
    errors = []
    warnings = []
    check_files(errors, warnings)
    check_catalog(errors, warnings)

    for warning in warnings:
        print("WARNING:", warning)
    for error in errors:
        print("ERROR:", error)

    if errors:
        print(f"\nValidation failed with {len(errors)} error(s).")
        sys.exit(1)

    print(f"\nValidation passed. {len(warnings)} warning(s).")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Actualizar `.github/workflows/validate.yml`**

Sustituir los pasos a partir de `Set up Python` por:

```yaml
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: python -m unittest discover -s tests -v

      - name: Validate assets
        run: python scripts/validate_assets.py

      - name: Rebuild indexes
        run: python scripts/build_index.py

      - name: Check generated indexes
        run: git diff --exit-code data/
```

- [ ] **Step 4: Borrar el índice antiguo y regenerar**

```bash
git rm -q data/competitions.json
python scripts/validate_assets.py | tail -1
python scripts/build_index.py
```
Expected: `Validation passed. 30 warning(s).` y después `competitions: 6 asset(s)` y `competition lookup: <N> name(s)`, con N > 100.

- [ ] **Step 5: Comprobar que el lookup resuelve los casos del spec**

```bash
python -c "import json; l = json.load(open('data/football/competitions-lookup.json', encoding='utf-8')); print(l['laliga ea sports'], l['primera division'], l['laliga'], l['champions league'], l['brasileirao'])"
```
Expected: `laliga laliga laliga uefa-champions-league brasileirao-serie-a`

- [ ] **Step 6: Comprobar que la validación falla ante un collage huérfano**

```bash
cp football/collages/laliga.png football/collages/test-orphan.png
python scripts/validate_assets.py; echo "exit=$?"
rm football/collages/test-orphan.png
```
Expected: `ERROR: Image not referenced by the catalog: football/collages/test-orphan.png` y `exit=1`.

- [ ] **Step 7: Ejecutar los tests y hacer commit**

```bash
python -m unittest discover -s tests
git add -A scripts .github data
git commit -m "Build and validate indexes from the football catalog

Replaces data/competitions.json with data/football/competitions.json
and a generated alias lookup. CI now installs Pillow and runs tests.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Normalizador de logos

**Files:**
- Create: `scripts/normalize_logo.py`
- Test: `tests/test_normalize_logo.py`

**Interfaces:**
- Produces: `normalize_logo(src: Path, dst: Path, max_side: int = 1024) -> tuple[int, int]` (tamaño final); CLI `python scripts/normalize_logo.py <src> <dst>`

- [ ] **Step 1: Escribir los tests que fallan**

`tests/test_normalize_logo.py`:

```python
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from normalize_logo import normalize_logo


class NormalizeLogoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.src = self.dir / "in.png"
        self.dst = self.dir / "out" / "logo.png"

    def tearDown(self):
        self.tmp.cleanup()

    def test_trims_transparent_margins(self):
        image = Image.new("RGBA", (100, 80), (0, 0, 0, 0))
        image.paste((255, 0, 0, 255), (10, 20, 60, 50))
        image.save(self.src)
        self.assertEqual(normalize_logo(self.src, self.dst), (50, 30))
        with Image.open(self.dst) as out:
            self.assertEqual(out.mode, "RGBA")
            self.assertEqual(out.size, (50, 30))

    def test_caps_longest_side(self):
        image = Image.new("RGBA", (2048, 1024), (255, 0, 0, 255))
        image.putpixel((0, 0), (0, 0, 0, 0))
        image.save(self.src)
        self.assertEqual(normalize_logo(self.src, self.dst), (1024, 512))

    def test_does_not_upscale(self):
        image = Image.new("RGBA", (40, 20), (0, 0, 0, 0))
        image.paste((0, 0, 255, 255), (5, 5, 35, 15))
        image.save(self.src)
        self.assertEqual(normalize_logo(self.src, self.dst), (30, 10))

    def test_rejects_image_without_transparency(self):
        Image.new("RGB", (50, 50), (255, 255, 255)).save(self.src)
        with self.assertRaises(ValueError):
            normalize_logo(self.src, self.dst)
        self.assertFalse(self.dst.exists())

    def test_rejects_fully_transparent_image(self):
        Image.new("RGBA", (50, 50), (0, 0, 0, 0)).save(self.src)
        with self.assertRaises(ValueError):
            normalize_logo(self.src, self.dst)
        self.assertFalse(self.dst.exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Ejecutar y comprobar que fallan**

Run: `python -m unittest discover -s tests -p "test_normalize_logo.py" -v`
Expected: ERROR `ModuleNotFoundError: No module named 'normalize_logo'`

- [ ] **Step 3: Implementación**

`scripts/normalize_logo.py`:

```python
"""Trim transparent margins from a logo and cap its longest side."""

from pathlib import Path
import argparse
import sys

from PIL import Image

MAX_SIDE = 1024


def normalize_logo(src: Path, dst: Path, max_side: int = MAX_SIDE) -> tuple[int, int]:
    with Image.open(src) as image:
        rgba = image.convert("RGBA")

    alpha = rgba.getchannel("A")
    if alpha.getextrema()[0] == 255:
        raise ValueError(f"{src} has no transparent pixels; use a logo with a transparent background")
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError(f"{src} is fully transparent")

    logo = rgba.crop(bbox)
    logo.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    logo.save(dst, "PNG", optimize=True)
    return logo.size


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src", type=Path, help="Downloaded logo")
    parser.add_argument("dst", type=Path, help="Destination, e.g. football/competitions/europe/laliga.png")
    args = parser.parse_args()

    try:
        width, height = normalize_logo(args.src, args.dst)
    except (OSError, ValueError) as exc:
        print("ERROR:", exc)
        sys.exit(1)
    print(f"OK -> {args.dst} ({width}x{height})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Ejecutar y comprobar que pasan**

Run: `python -m unittest discover -s tests -v`
Expected: 35 tests, `OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/normalize_logo.py tests/test_normalize_logo.py
git commit -m "Add logo normalizer for competition assets

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Revisar los 6 logos existentes

**Files:**
- Possibly modify: `football/competitions/europe/{uefa-champions-league,uefa-europa-league,uefa-conference-league,copa-del-rey}.png`, `football/competitions/south-america/copa-libertadores.png`, `football/competitions/world/fifa-club-world-cup.png`
- Modify: `data/sources.json`

- [ ] **Step 1: Inspeccionar cada uno**

Abrir cada PNG con Read y comprobar: sin marca de agua, fondo transparente, logo vigente (UCL con el "starball"; UEL y UECL con la identidad de 2021 en adelante; Libertadores con el logo de CONMEBOL Libertadores; Mundial de Clubes con el logo del formato de 2025).

- [ ] **Step 2: Sustituir los que no cumplan**

Para cada uno que falle, aplicar el "Procedimiento para obtener un logo" (pasos 1–8).

- [ ] **Step 3: Normalizar los que se conservan**

Para cada logo conservado, recortarlo y limitarlo a 1024 px sin cambiar su contenido:
```bash
python scripts/normalize_logo.py football/competitions/europe/uefa-champions-league.png football/competitions/europe/uefa-champions-league.png
```
(repetir con cada ruta conservada). Registrar en `data/sources.json` con `"url": null` y `"notes": "Pre-existing asset; original source unknown"` (paso 7 del procedimiento).

- [ ] **Step 4: Validar y hacer commit**

```bash
python scripts/validate_assets.py | tail -1 && python scripts/build_index.py
git add -A football data
git commit -m "Review and normalize existing competition logos

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Logos de ligas europeas (7)

**Competiciones:** `premier-league`, `laliga`, `serie-a`, `bundesliga`, `ligue-1`, `eredivisie`, `liga-portugal` → `football/competitions/europe/`

- [ ] **Step 1:** Aplicar el "Procedimiento para obtener un logo" a cada una. El collage de la liga sirve como referencia visual del logo actual (esquina superior izquierda), no como fuente.
- [ ] **Step 2:** `python scripts/validate_assets.py | tail -1 && python scripts/build_index.py`. Expected: `Validation passed.` con 7 avisos menos que antes.
- [ ] **Step 3: Commit**

```bash
git add -A football data
git commit -m "Add clean logos for European leagues

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Logos de copas y supercopas europeas (10)

**Competiciones:** `fa-cup`, `efl-cup`, `community-shield`, `supercopa-de-espana`, `coppa-italia`, `supercoppa-italiana`, `dfb-pokal`, `dfl-supercup`, `coupe-de-france`, `trophee-des-champions` → `football/competitions/europe/`

- [ ] **Step 1:** Aplicar el "Procedimiento para obtener un logo" a cada una. Para copas con patrocinador (EFL Cup/Carabao Cup), preferir el logo de la competición sin patrocinador si existe; si solo existe con patrocinador, usar el actual y anotarlo en `notes`.
- [ ] **Step 2:** `python scripts/validate_assets.py | tail -1 && python scripts/build_index.py`. Expected: `Validation passed.`
- [ ] **Step 3: Commit**

```bash
git add -A football data
git commit -m "Add clean logos for European domestic cups and super cups

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Logos de UEFA y FIFA restantes (4)

**Competiciones:** `uefa-super-cup`, `uefa-euro`, `uefa-nations-league` → `football/competitions/europe/`; `fifa-world-cup` → `football/competitions/world/`

- [ ] **Step 1:** Aplicar el "Procedimiento para obtener un logo" a cada una. Para `uefa-euro` y `fifa-world-cup`, usar el logo genérico de la marca del torneo (sin sede ni año) si existe; si no, usar el de la edición más reciente o la próxima y anotarlo en `notes`.
- [ ] **Step 2:** `python scripts/validate_assets.py | tail -1 && python scripts/build_index.py`. Expected: `Validation passed.`
- [ ] **Step 3: Commit**

```bash
git add -A football data
git commit -m "Add clean logos for UEFA and FIFA tournaments

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Logos de América y Asia (9)

**Competiciones:** `copa-sudamericana`, `brasileirao-serie-a`, `liga-profesional-argentina`, `copa-america` → `football/competitions/south-america/`; `liga-mx`, `mls`, `concacaf-champions-cup`, `concacaf-gold-cup` → `football/competitions/north-america/`; `saudi-pro-league` → `football/competitions/asia/`

- [ ] **Step 1:** Aplicar el "Procedimiento para obtener un logo" a cada una.
- [ ] **Step 2:** `python scripts/validate_assets.py | tail -1 && python scripts/build_index.py`. Expected: `Validation passed.` Los únicos avisos que quedan son los de logos no encontrados en las Tasks 6–10.
- [ ] **Step 3: Commit**

```bash
git add -A football data
git commit -m "Add clean logos for American and Asian competitions

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Actualizar la sección "Estructura"**

Sustituir el árbol por:

````markdown
```text
sports-assets/
├── football/
│   ├── competitions/
│   │   ├── europe/
│   │   ├── south-america/
│   │   ├── north-america/
│   │   ├── asia/
│   │   └── world/
│   └── collages/
├── ufc/
│   ├── fighters/
│   └── logos/
├── data/
│   ├── football/
│   │   ├── competitions.json          # catálogo (fuente de verdad, se edita a mano)
│   │   └── competitions-lookup.json   # generado: nombre normalizado → id
│   ├── fighters.json
│   ├── ufc-logos.json
│   ├── ufc-fighters-seed.json
│   ├── all-assets.json
│   └── sources.json
├── scripts/
│   ├── build_index.py
│   ├── football_catalog.py
│   ├── normalize_logo.py
│   ├── download_ufc_fighters.py
│   └── validate_assets.py
└── tests/
```
````

- [ ] **Step 2: Sustituir la sección "### Competiciones" por una sección "## Competiciones de fútbol"**

````markdown
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

1. Normaliza el nombre que recibes: quita tildes, pasa a minúsculas, cambia todo lo que no sea letra o número por un espacio y colapsa los espacios (`"LaLiga EA Sports"` → `"laliga ea sports"`).
2. Búscalo en `data/football/competitions-lookup.json` para obtener el `id`.
3. Busca ese `id` en `data/football/competitions.json` para obtener `logo`.
4. Construye la URL:

```text
https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@main/football/competitions/europe/laliga.png
```

### Añadir o sustituir un logo

```bash
python scripts/normalize_logo.py descarga.png football/competitions/europe/laliga.png
```

Después actualiza `logo` en el catálogo, registra el origen en `data/sources.json` y ejecuta `python scripts/build_index.py`.
````

- [ ] **Step 3: Añadir a "## Validar recursos"**

````markdown
Instala las dependencias y ejecuta los tests:

```bash
pip install -r requirements.txt
python -m unittest discover -s tests
```

La validación falla si el catálogo apunta a un archivo inexistente, si hay imágenes sin entrada, si un logo no es transparente o si dos competiciones comparten un alias.
````

- [ ] **Step 4: Verificación final y commit**

```bash
python -m unittest discover -s tests && python scripts/validate_assets.py | tail -1 && python scripts/build_index.py && git status --short data
```
Expected: tests `OK`, `Validation passed.`, sin cambios pendientes en `data/`.

```bash
git add README.md
git commit -m "Document football competitions catalog

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
