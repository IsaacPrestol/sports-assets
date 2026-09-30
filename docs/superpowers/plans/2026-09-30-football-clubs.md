# Escudos de clubes de fútbol — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Catálogo y escudos de los ~697 clubes de las 25 ligas de luukhopman/football-logos (actuales + desde 2021/22), con imágenes de football-logos.cc, emparejamiento revisado visualmente y un script re-ejecutable cada temporada.

**Architecture:** Lógica pura en `scripts/football_clubs.py` (emparejamiento, ids, alias, fusión con el catálogo, lookup por país, validación), testeada sin red. `scripts/sync_clubs.py` es la capa fina de red/CLI (`plan`, `accept`, `apply`). `build_index.py` y `validate_assets.py` incorporan clubes. Las 18 ligas nuevas se añaden al catálogo de competiciones.

**Tech Stack:** Python 3.12, Pillow, `unittest`, `urllib`, `difflib`.

**Spec:** `docs/superpowers/specs/2026-09-30-football-clubs-design.md`

## Global Constraints

- Repositorio: `C:\Users\Isaac\Downloads\sports-assets`, rama `football-competitions-by-continent`. Comandos desde la raíz.
- Commits terminan con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Escudo: `football/clubs/<country en minúsculas>/<id>.png`, PNG con píxeles transparentes, lado mayor ≤ 1024 px, sin ampliar.
- `country`: `^[A-Z]{2}(?:-[A-Z]{3})?$` (`ES`, `GB-ENG`, `GB-SCT`).
- `league`: id de competición con `type: "league"`, o `null`.
- Normalización de nombres: la de `football_catalog.normalize_name`.
- JSON: `indent=2`, `ensure_ascii=False`, salto de línea final; `clubs-lookup.json` y `clubs-mapping.json` con claves ordenadas; `sources.json` con `sort_keys=True`.
- Fuentes de logos: primero repositorios (football-logos.cc), después Wikipedia/Wikimedia.
- User-Agent de red: `sports-assets-sync/1.0 (https://github.com/IsaacPrestol/sports-assets)` (sin email).
- Mensajes de scripts en inglés.

## Review Focus

1. Dos claves de luukhopman del mismo club con nombres distintos ("Banik Ostrava" / "FC Banik Ostrava") → mismo `id`, un solo club. Test en Task 3.
2. Dos clubes distintos de países distintos con el mismo slug → el segundo recibe sufijo de país; ninguno pierde su id existente. Test en Task 3.
3. Un club que baja de las 25 ligas → `league: null`, conserva escudo, nombre y alias manuales. Test en Task 4.
4. Alias automático que coincide con el nombre de otro club del mismo país → se descarta y se informa; el catálogo resultante valida. Test en Task 4.
5. Escudo de respaldo de luukhopman (139×181) → validación avisa (< 400 px) sin fallar. Test en Task 5.

## Estructura de archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `scripts/football_clubs.py` | Crear | Constantes de mapeo, emparejamiento, ids, alias, fusión, lookup, validación |
| `scripts/sync_clubs.py` | Crear | Red + CLI `plan` / `accept` / `apply` + hojas de revisión |
| `scripts/build_index.py` | Modificar | `clubs-lookup.json` y `clubs` en `all-assets.json` |
| `scripts/validate_assets.py` | Modificar | Recorrer `football/clubs/` y validar el catálogo de clubes |
| `tests/test_football_clubs.py` | Crear | Tests de `football_clubs` |
| `tests/test_football_catalog.py` | Modificar | Ampliar alias genéricos prohibidos |
| `data/football/competitions.json` | Modificar | 18 ligas nuevas |
| `data/football/clubs.json` | Crear | Catálogo de clubes |
| `data/football/clubs-mapping.json` | Crear | Emparejamientos confirmados |
| `data/football/clubs-lookup.json` | Generado | Alias por país |
| `football/clubs/**` | Crear | Escudos |
| `README.md` | Modificar | Documentación |

---

### Task 1: 18 ligas nuevas en el catálogo de competiciones

**Files:**
- Modify: `tests/test_football_catalog.py` (`RealCatalogTest.GENERIC_ALIASES`)
- Modify: `data/football/competitions.json`
- Create: `football/competitions/europe/<id>.png` × 18
- Modify: `data/sources.json`

- [ ] **Step 1: Ampliar la lista de alias genéricos**

En `RealCatalogTest.GENERIC_ALIASES` añadir `"superliga"`, `"super league"`, `"premier liga"`, `"pro league"`. Ejecutar `python -m unittest discover -s tests` → `OK` (guarda para las entradas nuevas).

- [ ] **Step 2: Añadir las 18 entradas**

Insertar tras `liga-portugal` (orden de la tabla del spec) con `type: "league"`, `scope: "club"`, `continent: "europe"`, `confederation: "UEFA"`, `logo: null`, `collage: null`:

```python
NEW = [
 ("austrian-bundesliga", "Austrian Football Bundesliga", ["Admiral Bundesliga", "Austrian Bundesliga"], "AT"),
 ("belgian-pro-league", "Belgian Pro League", ["Jupiler Pro League", "Belgian First Division A"], "BE"),
 ("bulgarian-first-league", "Bulgarian First League", ["efbet Liga", "First Professional Football League"], "BG"),
 ("croatian-football-league", "Croatian Football League", ["SuperSport HNL", "HNL", "Prva HNL"], "HR"),
 ("czech-first-league", "Czech First League", ["Chance Liga", "Fortuna Liga"], "CZ"),
 ("danish-superliga", "Danish Superliga", ["3F Superliga"], "DK"),
 ("greek-super-league", "Super League Greece", ["Super League 1", "Stoiximan Super League"], "GR"),
 ("israeli-premier-league", "Israeli Premier League", ["Ligat ha'Al"], "IL"),
 ("eliteserien", "Eliteserien", ["Norwegian Eliteserien"], "NO"),
 ("ekstraklasa", "Ekstraklasa", ["PKO BP Ekstraklasa", "Polish Ekstraklasa"], "PL"),
 ("romanian-liga-1", "Liga I", ["Romanian SuperLiga", "SuperLiga României"], "RO"),
 ("russian-premier-league", "Russian Premier League", ["RPL", "Mir Russian Premier League"], "RU"),
 ("scottish-premiership", "Scottish Premiership", ["SPFL Premiership", "William Hill Premiership"], "GB-SCT"),
 ("serbian-superliga", "Serbian SuperLiga", ["Super liga Srbije", "Mozzart Bet Super liga"], "RS"),
 ("allsvenskan", "Allsvenskan", ["Swedish Allsvenskan"], "SE"),
 ("swiss-super-league", "Swiss Super League", ["Brack Super League"], "CH"),
 ("super-lig", "Süper Lig", ["Turkish Super Lig", "Trendyol Süper Lig"], "TR"),
 ("ukrainian-premier-league", "Ukrainian Premier League", ["UPL", "Ukrainian Premier Liha"], "UA"),
]
```

Run: `python -m unittest discover -s tests && python scripts/validate_assets.py | tail -1`
Expected: `OK`, `Validation passed. 18 warning(s).`

- [ ] **Step 3: Logos**

Para cada liga, procedimiento de logos de la fase anterior (plan `2026-09-30-football-competitions.md`, sección "Procedimiento para obtener un logo"), buscando **primero** en la página de país de football-logos.cc (`https://football-logos.cc/<país>/`, imágenes `1500x1500`) y, si no está o trae patrocinador/fondo opaco, en Wikimedia. Revisar cada imagen visualmente, normalizar, poner `logo`, registrar en `sources.json`.

- [ ] **Step 4: Verificar y commit**

Run: `python -m unittest discover -s tests && python scripts/validate_assets.py | tail -1 && python scripts/build_index.py | tail -1`
Expected: `OK`, `Validation passed. 0 warning(s).`

```bash
git add -A tests data football
git commit -m "Add the 18 remaining European leagues to the competitions catalog

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Nombres, slugs, emparejamiento y alias

**Files:**
- Create: `scripts/football_clubs.py`
- Test: `tests/test_football_clubs.py`

**Interfaces:**
- Consumes: `football_catalog.normalize_name`, `ROOT`, `ID_RE`, `has_alpha`
- Produces: `strip_affixes(name) -> str`, `slugify(name) -> str`, `slug_name(slug) -> str`, `propose_slug(name, slugs, cutoff=0.8) -> tuple[str | None, str]` (`"exact"|"fuzzy"|"none"`), `auto_aliases(name, names, slug) -> list[str]`; constantes `CLUBS_FILE`, `CLUBS_LOOKUP_FILE`, `MAPPING_FILE`, `CLUBS_DIR`, `COUNTRY_RE`, `AFFIXES`

- [ ] **Step 1: Tests que fallan**

`tests/test_football_clubs.py`:

```python
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from football_clubs import auto_aliases, propose_slug, slug_name, slugify, strip_affixes


class NamesTest(unittest.TestCase):
    def test_strip_affixes(self):
        self.assertEqual(strip_affixes("Arsenal FC"), "arsenal")
        self.assertEqual(strip_affixes("FC Banik Ostrava"), "banik ostrava")
        self.assertEqual(strip_affixes("1. FC Köln"), "koln")

    def test_strip_affixes_keeps_name_made_only_of_affixes(self):
        self.assertEqual(strip_affixes("AC"), "ac")

    def test_slugify_and_slug_name(self):
        self.assertEqual(slugify("Atlético de Madrid"), "atletico-de-madrid")
        self.assertEqual(slug_name("real-madrid"), "Real Madrid")


class ProposeSlugTest(unittest.TestCase):
    SLUGS = ["arsenal", "aston-villa", "real-madrid", "salzburg"]

    def test_exact_after_stripping_affixes(self):
        self.assertEqual(propose_slug("Arsenal FC", self.SLUGS), ("arsenal", "exact"))

    def test_fuzzy(self):
        self.assertEqual(propose_slug("Aston Vila", self.SLUGS), ("aston-villa", "fuzzy"))

    def test_none(self):
        self.assertEqual(propose_slug("Kecskeméti TE", self.SLUGS), (None, "none"))


class AutoAliasesTest(unittest.TestCase):
    def test_collects_names_slug_and_stripped_forms(self):
        aliases = auto_aliases("Arsenal FC", ["Arsenal FC"], "arsenal")
        self.assertEqual(aliases, ["Arsenal"])

    def test_history_names_and_stripped_variants(self):
        aliases = auto_aliases(
            "FC Banik Ostrava", ["Banik Ostrava", "FC Banik Ostrava"], None,
        )
        self.assertEqual(aliases, ["Banik Ostrava"])

    def test_excludes_duplicates_of_name(self):
        self.assertEqual(auto_aliases("Real Madrid", ["Real Madrid"], "real-madrid"), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Ejecutar → falla**

Run: `python -m unittest discover -s tests -p "test_football_clubs.py"`
Expected: `ModuleNotFoundError: No module named 'football_clubs'`

- [ ] **Step 3: Implementación**

`scripts/football_clubs.py`:

```python
"""Football clubs catalog helpers and the luukhopman/football-logos sync logic."""

from pathlib import Path
import difflib
import json
import re

from PIL import Image

from football_catalog import ID_RE, ROOT, has_alpha, normalize_name

CLUBS_FILE = ROOT / "data" / "football" / "clubs.json"
CLUBS_LOOKUP_FILE = ROOT / "data" / "football" / "clubs-lookup.json"
MAPPING_FILE = ROOT / "data" / "football" / "clubs-mapping.json"
CLUBS_DIR = "football/clubs"
COUNTRY_RE = re.compile(r"^[A-Z]{2}(?:-[A-Z]{3})?$")
AFFIXES = {
    "1", "ac", "afc", "as", "bk", "ca", "cd", "cf", "fc", "fk", "fsv", "hnk", "if",
    "kaa", "krc", "kv", "nk", "rc", "rcd", "sc", "sd", "sk", "ss", "ssc", "sv", "tsg",
    "ud", "us", "vfb", "vfl",
}


def strip_affixes(name: str) -> str:
    words = normalize_name(name).split()
    kept = [word for word in words if word not in AFFIXES]
    return " ".join(kept or words)


def slugify(name: str) -> str:
    return normalize_name(name).replace(" ", "-")


def slug_name(slug: str) -> str:
    return " ".join(word.capitalize() for word in slug.split("-"))


def propose_slug(name: str, slugs: list[str], cutoff: float = 0.8) -> tuple[str | None, str]:
    candidates = {strip_affixes(slug.replace("-", " ")): slug for slug in sorted(slugs)}
    target = strip_affixes(name)
    if target in candidates:
        return candidates[target], "exact"
    close = difflib.get_close_matches(target, list(candidates), n=1, cutoff=cutoff)
    if close:
        return candidates[close[0]], "fuzzy"
    return None, "none"


def auto_aliases(name: str, names: list[str], slug: str | None) -> list[str]:
    raw = [*names, *([slug_name(slug)] if slug else [])]
    seen = {normalize_name(name)}
    aliases = []
    for candidate in [*raw, *(strip_affixes(n) for n in raw)]:
        key = normalize_name(candidate)
        if key and key not in seen:
            seen.add(key)
            aliases.append(candidate)
    return aliases
```

Nota del test `test_collects_names_slug_and_stripped_forms`: "Arsenal FC" (nombre) se excluye, `slug_name("arsenal")` = "Arsenal" se añade, `strip_affixes` produce "arsenal" (ya visto). En `test_history_names...`: "Banik Ostrava" se añade; "FC Banik Ostrava" es el nombre; las variantes sin afijos ya están vistas.

- [ ] **Step 4: Ejecutar → pasa**

Run: `python -m unittest discover -s tests`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/football_clubs.py tests/test_football_clubs.py
git commit -m "Add club name matching and alias helpers

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Índice de luukhopman y propuestas de emparejamiento

**Files:**
- Modify: `scripts/football_clubs.py`
- Test: `tests/test_football_clubs.py`

**Interfaces:**
- Produces:
  - `COUNTRY_CODES: dict[str, str]` (carpeta de país luukhopman → ISO), `LEAGUE_IDS: dict[str, str]` (carpeta de liga → id de competición), `FL_COUNTRIES: dict[str, str]` (carpeta de país → ruta de football-logos.cc), `CURRENT_SEASON = "~current"`
  - `luuk_index(paths: list[str]) -> dict[str, dict]`: clave `"<País>|<Club>"` → `{"country_folder", "name", "league_folder" (str|None), "latest_season", "latest_path"}`
  - `propose(luuk, mapping, fl_slugs: dict[str, list[str]], existing_ids: dict[str, str]) -> dict[str, dict]`: clave → `{"id", "source", "slug", "match"}`

- [ ] **Step 1: Tests que fallan**

Añadir a `tests/test_football_clubs.py` (import de `luuk_index, propose`):

```python
PATHS = [
    "README.md",
    "logos/Spain - LaLiga/Real Madrid.png",
    "history/2024-25/Spain - LaLiga/Real Madrid.png",
    "history/2023-24/Spain - LaLiga/UD Almería.png",
    "history/2024-25/Czech Republic - Chance Liga/Banik Ostrava.png",
    "history/2025-26/Czech Republic - Chance Liga/FC Banik Ostrava.png",
]


class LuukIndexTest(unittest.TestCase):
    def test_current_club(self):
        club = luuk_index(PATHS)["Spain|Real Madrid"]
        self.assertEqual(club["league_folder"], "Spain - LaLiga")
        self.assertEqual(club["latest_path"], "logos/Spain - LaLiga/Real Madrid.png")

    def test_history_only_club(self):
        club = luuk_index(PATHS)["Spain|UD Almería"]
        self.assertIsNone(club["league_folder"])
        self.assertEqual(club["latest_path"], "history/2023-24/Spain - LaLiga/UD Almería.png")

    def test_ignores_non_logo_paths(self):
        self.assertEqual(len(luuk_index(PATHS)), 4)


class ProposeTest(unittest.TestCase):
    def setUp(self):
        self.luuk = luuk_index(PATHS)
        self.fl = {"Spain": ["real-madrid", "almeria"], "Czech Republic": []}

    def test_matches_and_ids(self):
        proposals = propose(self.luuk, {}, self.fl, {})
        self.assertEqual(proposals["Spain|Real Madrid"],
                         {"id": "real-madrid", "source": "football-logos", "slug": "real-madrid", "match": "exact"})
        self.assertEqual(proposals["Spain|UD Almería"]["id"], "almeria")

    def test_name_variants_share_one_id(self):
        proposals = propose(self.luuk, {}, self.fl, {})
        self.assertEqual(proposals["Czech Republic|Banik Ostrava"]["id"], "banik-ostrava")
        self.assertEqual(proposals["Czech Republic|FC Banik Ostrava"]["id"], "banik-ostrava")
        self.assertEqual(proposals["Czech Republic|Banik Ostrava"]["source"], "luukhopman")

    def test_skips_mapped_keys(self):
        mapping = {"Spain|Real Madrid": {"id": "real-madrid", "source": "football-logos", "slug": "real-madrid"}}
        self.assertNotIn("Spain|Real Madrid", propose(self.luuk, mapping, self.fl, {}))

    def test_same_slug_in_other_country_gets_suffix(self):
        proposals = propose(self.luuk, {}, self.fl, {"real-madrid": "GB-ENG"})
        self.assertEqual(proposals["Spain|Real Madrid"]["id"], "real-madrid-es")

    def test_existing_id_in_same_country_is_reused(self):
        proposals = propose(self.luuk, {}, self.fl, {"real-madrid": "ES"})
        self.assertEqual(proposals["Spain|Real Madrid"]["id"], "real-madrid")
```

- [ ] **Step 2: Ejecutar → falla** (`ImportError: cannot import name 'luuk_index'`)

- [ ] **Step 3: Implementación** (añadir a `scripts/football_clubs.py`)

```python
CURRENT_SEASON = "~current"

COUNTRY_CODES = {
    "Austria": "AT", "Belgium": "BE", "Bulgaria": "BG", "Croatia": "HR",
    "Czech Republic": "CZ", "Denmark": "DK", "England": "GB-ENG", "France": "FR",
    "Germany": "DE", "Greece": "GR", "Hungary": "HU", "Israel": "IL", "Italy": "IT",
    "Netherlands": "NL", "Norway": "NO", "Poland": "PL", "Portugal": "PT",
    "Romania": "RO", "Russia": "RU", "Scotland": "GB-SCT", "Serbia": "RS",
    "Spain": "ES", "Sweden": "SE", "Switzerland": "CH", "Türkiye": "TR", "Ukraine": "UA",
}

FL_COUNTRIES = {
    folder: folder.lower().replace(" ", "-") for folder in COUNTRY_CODES
} | {"Türkiye": "turkey"}

LEAGUE_IDS = {
    "Austria - Bundesliga": "austrian-bundesliga",
    "Belgium - Jupiler Pro League": "belgian-pro-league",
    "Bulgaria - efbet Liga": "bulgarian-first-league",
    "Croatia - SuperSport HNL": "croatian-football-league",
    "Czech Republic - Chance Liga": "czech-first-league",
    "Denmark - Superliga": "danish-superliga",
    "England - Premier League": "premier-league",
    "France - Ligue 1": "ligue-1",
    "Germany - Bundesliga": "bundesliga",
    "Greece - Super League 1": "greek-super-league",
    "Israel - Ligat ha'Al": "israeli-premier-league",
    "Italy - Serie A": "serie-a",
    "Netherlands - Eredivisie": "eredivisie",
    "Norway - Eliteserien": "eliteserien",
    "Poland - PKO BP Ekstraklasa": "ekstraklasa",
    "Portugal - Liga Portugal": "liga-portugal",
    "Romania - SuperLiga": "romanian-liga-1",
    "Russia - Premier Liga": "russian-premier-league",
    "Scotland - Scottish Premiership": "scottish-premiership",
    "Serbia - Super liga Srbije": "serbian-superliga",
    "Spain - LaLiga": "laliga",
    "Sweden - Allsvenskan": "allsvenskan",
    "Switzerland - Super League": "swiss-super-league",
    "Türkiye - Süper Lig": "super-lig",
    "Ukraine - Premier Liga": "ukrainian-premier-league",
}


def luuk_index(paths: list[str]) -> dict[str, dict]:
    clubs: dict[str, dict] = {}
    for path in sorted(paths):
        parts = path.split("/")
        if not path.endswith(".png"):
            continue
        if parts[0] == "logos" and len(parts) == 3:
            season, league_folder, filename = CURRENT_SEASON, parts[1], parts[2]
        elif parts[0] == "history" and len(parts) == 4:
            season, league_folder, filename = parts[1], parts[2], parts[3]
        else:
            continue
        country_folder = league_folder.split(" - ")[0]
        name = filename[: -len(".png")]
        club = clubs.setdefault(f"{country_folder}|{name}", {
            "country_folder": country_folder,
            "name": name,
            "league_folder": None,
            "latest_season": "",
            "latest_path": "",
        })
        if season == CURRENT_SEASON:
            club["league_folder"] = league_folder
        if season > club["latest_season"]:
            club["latest_season"], club["latest_path"] = season, path
    return clubs


def propose(luuk: dict, mapping: dict, fl_slugs: dict[str, list[str]],
            existing_ids: dict[str, str]) -> dict[str, dict]:
    taken = dict(existing_ids)
    groups: dict[tuple[str, str], str] = {}
    proposals = {}
    for key in sorted(luuk):
        if key in mapping:
            continue
        club = luuk[key]
        country = COUNTRY_CODES[club["country_folder"]]
        slug, match = propose_slug(club["name"], fl_slugs.get(club["country_folder"], []))
        base = slug or slugify(strip_affixes(club["name"]))
        if (country, base) in groups:
            club_id = groups[(country, base)]
        elif base in taken and taken[base] != country:
            club_id = f"{base}-{country.lower()}"
        else:
            club_id = base
        groups[(country, base)] = club_id
        taken.setdefault(club_id, country)
        proposals[key] = {
            "id": club_id,
            "source": "football-logos" if slug else "luukhopman",
            "slug": slug,
            "match": match,
        }
    return proposals
```

- [ ] **Step 4: Ejecutar → pasa.** Run: `python -m unittest discover -s tests` → `OK`
- [ ] **Step 5: Commit** — `git add scripts/football_clubs.py tests/test_football_clubs.py` · mensaje `Index luukhopman clubs and propose logo matches`

---

### Task 4: Fusión con el catálogo, lookup por país y assets

**Files:**
- Modify: `scripts/football_clubs.py`
- Test: `tests/test_football_clubs.py`

**Interfaces:**
- Produces:
  - `merge_clubs(existing: list[dict], mapping: dict, luuk: dict, missing_logos: set[str] = frozenset()) -> tuple[list[dict], list[str]]` (clubes ordenados, alias descartados)
  - `build_club_lookup(clubs) -> tuple[dict[str, dict[str, str]], list[str]]`
  - `club_assets(clubs) -> dict[str, dict]`

- [ ] **Step 1: Tests que fallan**

```python
MAPPING = {
    "Spain|Real Madrid": {"id": "real-madrid", "source": "football-logos", "slug": "real-madrid"},
    "Spain|UD Almería": {"id": "ud-almeria", "source": "football-logos", "slug": "almeria"},
    "Czech Republic|Banik Ostrava": {"id": "banik-ostrava", "source": "luukhopman", "slug": None},
    "Czech Republic|FC Banik Ostrava": {"id": "banik-ostrava", "source": "luukhopman", "slug": None},
}


class MergeClubsTest(unittest.TestCase):
    def setUp(self):
        self.luuk = luuk_index(PATHS)

    def merged(self, existing=(), missing=frozenset()):
        clubs, skipped = merge_clubs(list(existing), MAPPING, self.luuk, missing)
        return {c["id"]: c for c in clubs}, skipped

    def test_new_current_club(self):
        clubs, _ = self.merged()
        self.assertEqual(clubs["real-madrid"], {
            "id": "real-madrid", "name": "Real Madrid", "aliases": [], "country": "ES",
            "league": "laliga", "logo": "football/clubs/es/real-madrid.png",
        })

    def test_history_only_club_has_no_league(self):
        clubs, _ = self.merged()
        self.assertIsNone(clubs["ud-almeria"]["league"])
        self.assertEqual(clubs["ud-almeria"]["aliases"], ["Almeria"])

    def test_name_variants_become_one_club_named_after_latest(self):
        clubs, _ = self.merged()
        self.assertEqual(clubs["banik-ostrava"]["name"], "FC Banik Ostrava")
        self.assertEqual(clubs["banik-ostrava"]["aliases"], ["Banik Ostrava"])
        self.assertEqual(len(clubs), 3)

    def test_existing_club_keeps_manual_fields_and_updates_league(self):
        existing = {"id": "real-madrid", "name": "Real Madrid CF", "aliases": ["Los Blancos"],
                    "country": "ES", "league": None, "logo": None}
        clubs, _ = self.merged([existing])
        self.assertEqual(clubs["real-madrid"]["name"], "Real Madrid CF")
        self.assertEqual(clubs["real-madrid"]["aliases"], ["Los Blancos"])
        self.assertEqual(clubs["real-madrid"]["league"], "laliga")
        self.assertEqual(clubs["real-madrid"]["logo"], "football/clubs/es/real-madrid.png")

    def test_relegated_existing_club_loses_league_only(self):
        existing = {"id": "ud-almeria", "name": "UD Almería", "aliases": ["Almeria"],
                    "country": "ES", "league": "laliga", "logo": "football/clubs/es/ud-almeria.png"}
        clubs, _ = self.merged([existing])
        self.assertIsNone(clubs["ud-almeria"]["league"])
        self.assertEqual(clubs["ud-almeria"]["aliases"], ["Almeria"])

    def test_missing_logo(self):
        clubs, _ = self.merged(missing={"ud-almeria"})
        self.assertIsNone(clubs["ud-almeria"]["logo"])

    def test_colliding_auto_alias_is_dropped_and_reported(self):
        existing = {"id": "other", "name": "Almeria", "aliases": [], "country": "ES",
                    "league": None, "logo": None}
        clubs, skipped = self.merged([existing])
        self.assertNotIn("Almeria", clubs["ud-almeria"]["aliases"])
        self.assertTrue(any("ud-almeria" in s and "other" in s for s in skipped))
        _, errors = build_club_lookup(list(clubs.values()))
        self.assertEqual(errors, [])

    def test_sorted_by_country_then_id(self):
        clubs, _ = merge_clubs([], MAPPING, self.luuk)
        self.assertEqual([c["id"] for c in clubs], ["banik-ostrava", "real-madrid", "ud-almeria"])


class ClubLookupTest(unittest.TestCase):
    def test_lookup_is_per_country(self):
        clubs = [
            {"id": "sporting-cp", "name": "Sporting CP", "aliases": ["Sporting"], "country": "PT", "league": None, "logo": None},
            {"id": "sporting-gijon", "name": "Sporting Gijón", "aliases": ["Sporting"], "country": "ES", "league": None, "logo": None},
        ]
        lookup, errors = build_club_lookup(clubs)
        self.assertEqual(errors, [])
        self.assertEqual(lookup["PT"]["sporting"], "sporting-cp")
        self.assertEqual(lookup["ES"]["sporting"], "sporting-gijon")
        self.assertEqual(list(lookup), ["ES", "PT"])

    def test_collision_within_country(self):
        clubs = [
            {"id": "a", "name": "Dinamo", "aliases": [], "country": "RO", "league": None, "logo": None},
            {"id": "b", "name": "Other", "aliases": ["Dinamo"], "country": "RO", "league": None, "logo": None},
        ]
        _, errors = build_club_lookup(clubs)
        self.assertEqual(len(errors), 1)

    def test_club_assets(self):
        clubs = [
            {"id": "a", "name": "A", "aliases": [], "country": "ES", "league": None, "logo": "football/clubs/es/a.png"},
            {"id": "b", "name": "B", "aliases": [], "country": "ES", "league": None, "logo": None},
        ]
        self.assertEqual(club_assets(clubs), {"a": {"name": "A", "path": "football/clubs/es/a.png"}})
```

Nota: el id de Almería es `ud-almeria` para que el alias automático "Almeria" choque solo con el club `other` (nombre "Almeria") y no con un id, que sería un error de validación y no un alias descartable.

- [ ] **Step 2: Ejecutar → falla** (`ImportError`)

- [ ] **Step 3: Implementación**

```python
def _drop_colliding_aliases(by_id: dict[str, dict], new_ids: set[str]) -> list[str]:
    owners: dict[tuple[str, str], str] = {}
    for club in by_id.values():
        names = [club["id"], club["name"]]
        if club["id"] not in new_ids:
            names += club["aliases"]
        for name in names:
            owners.setdefault((club["country"], normalize_name(name)), club["id"])
    skipped = []
    for club_id in sorted(new_ids):
        club = by_id[club_id]
        kept = []
        for alias in club["aliases"]:
            key = (club["country"], normalize_name(alias))
            owner = owners.setdefault(key, club_id)
            if owner == club_id:
                kept.append(alias)
            else:
                skipped.append(f"{club_id}: alias '{alias}' collides with '{owner}'")
        club["aliases"] = kept
    return skipped


def merge_clubs(existing: list[dict], mapping: dict, luuk: dict,
                missing_logos: set[str] = frozenset()) -> tuple[list[dict], list[str]]:
    by_id = {club["id"]: dict(club) for club in existing}
    keys_by_id: dict[str, list[str]] = {}
    for key in sorted(mapping):
        keys_by_id.setdefault(mapping[key]["id"], []).append(key)

    new_ids = set()
    for club_id, keys in keys_by_id.items():
        entries = [luuk[key] for key in keys if key in luuk]
        if not entries:
            continue
        country = COUNTRY_CODES[entries[0]["country_folder"]]
        current = [entry for entry in entries if entry["league_folder"]]
        league = LEAGUE_IDS[current[0]["league_folder"]] if current else None
        logo = None if club_id in missing_logos else f"{CLUBS_DIR}/{country.lower()}/{club_id}.png"
        if club_id in by_id:
            by_id[club_id].update(league=league, logo=logo)
            continue
        latest = max(entries, key=lambda entry: entry["latest_season"])
        slug = next((mapping[key]["slug"] for key in keys if mapping[key].get("slug")), None)
        by_id[club_id] = {
            "id": club_id,
            "name": latest["name"],
            "aliases": auto_aliases(latest["name"], [entry["name"] for entry in entries], slug),
            "country": country,
            "league": league,
            "logo": logo,
        }
        new_ids.add(club_id)

    skipped = _drop_colliding_aliases(by_id, new_ids)
    clubs = sorted(by_id.values(), key=lambda club: (club["country"], club["id"]))
    return clubs, skipped


def build_club_lookup(clubs: list[dict]) -> tuple[dict[str, dict[str, str]], list[str]]:
    lookup: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    for club in clubs:
        table = lookup.setdefault(club["country"], {})
        for raw in [club["id"], club["name"], *club["aliases"]]:
            key = normalize_name(raw)
            if not key:
                errors.append(f"Name '{raw}' of '{club['id']}' normalizes to an empty string")
                continue
            owner = table.setdefault(key, club["id"])
            if owner != club["id"]:
                errors.append(
                    f"Name '{raw}' of '{club['id']}' collides with '{owner}' "
                    f"in {club['country']} (key '{key}')"
                )
    sorted_lookup = {country: dict(sorted(table.items())) for country, table in sorted(lookup.items())}
    return sorted_lookup, errors


def club_assets(clubs: list[dict]) -> dict[str, dict]:
    return {club["id"]: {"name": club["name"], "path": club["logo"]} for club in clubs if club["logo"]}
```

- [ ] **Step 4: Ejecutar → pasa.** `python -m unittest discover -s tests` → `OK`
- [ ] **Step 5: Commit** — mensaje `Merge synced clubs into the catalog and build per-country lookup`

---

### Task 5: Validación del catálogo de clubes

**Files:**
- Modify: `scripts/football_clubs.py`
- Test: `tests/test_football_clubs.py`

**Interfaces:**
- Produces: `validate_clubs(root: Path, catalog, competitions: list[dict], mapping: dict) -> tuple[list[str], list[str]]`, `load_json(path: Path, default)`

- [ ] **Step 1: Tests que fallan**

```python
import tempfile
from PIL import Image

LEAGUES = [{"id": "laliga", "type": "league"}, {"id": "copa-del-rey", "type": "cup"}]


def club(**overrides):
    entry = {"id": "real-madrid", "name": "Real Madrid", "aliases": [], "country": "ES",
             "league": "laliga", "logo": None}
    entry.update(overrides)
    return entry


class ValidateClubsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def png(self, rel, size=(500, 500), alpha=0):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", size, (255, 0, 0, alpha)).save(path)
        return rel

    def validate(self, *clubs, mapping=None):
        return validate_clubs(self.root, {"version": 1, "clubs": list(clubs)}, LEAGUES, mapping or {})

    def test_valid(self):
        logo = self.png("football/clubs/es/real-madrid.png")
        self.assertEqual(self.validate(club(logo=logo)), ([], []))

    def test_missing_logo_is_warning(self):
        errors, warnings = self.validate(club())
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)

    def test_low_resolution_is_warning(self):
        logo = self.png("football/clubs/es/real-madrid.png", size=(139, 181))
        errors, warnings = self.validate(club(logo=logo))
        self.assertEqual(errors, [])
        self.assertTrue(any("low resolution" in w for w in warnings))

    def test_bad_structure(self):
        self.assertEqual(len(self.validate(club(country="Spain"))[0]), 1)
        self.assertEqual(len(self.validate(club(id="Real Madrid"))[0]), 1)
        entry = club(); del entry["league"]
        self.assertEqual(len(self.validate(entry)[0]), 1)
        self.assertEqual(len(validate_clubs(self.root, {}, LEAGUES, {})[0]), 1)

    def test_league_must_be_a_league(self):
        errors, _ = self.validate(club(league="copa-del-rey"))
        self.assertTrue(any("league" in e for e in errors))

    def test_duplicate_id(self):
        errors, _ = self.validate(club(), club(name="Other"))
        self.assertTrue(any("Duplicate id" in e for e in errors))

    def test_logo_path_and_existence(self):
        errors, _ = self.validate(club(logo="football/clubs/gb-eng/real-madrid.png"))
        self.assertTrue(any("must be" in e for e in errors))
        errors, _ = self.validate(club(logo="football/clubs/es/real-madrid.png"))
        self.assertTrue(any("not found" in e for e in errors))

    def test_opaque_logo(self):
        logo = self.png("football/clubs/es/real-madrid.png", alpha=255)
        errors, _ = self.validate(club(logo=logo))
        self.assertTrue(any("transparent" in e for e in errors))

    def test_orphan_image(self):
        self.png("football/clubs/es/other.png")
        errors, _ = self.validate(club())
        self.assertTrue(any("not referenced" in e for e in errors))

    def test_alias_collision_in_country(self):
        errors, _ = self.validate(club(), club(id="other", name="Other", aliases=["Real Madrid"]))
        self.assertTrue(any("collides" in e for e in errors))

    def test_mapping_id_must_exist(self):
        mapping = {"Spain|Ghost": {"id": "ghost", "source": "luukhopman", "slug": None}}
        errors, _ = self.validate(club(), mapping=mapping)
        self.assertTrue(any("ghost" in e for e in errors))
```

- [ ] **Step 2: Ejecutar → falla** (`ImportError: validate_clubs`)

- [ ] **Step 3: Implementación**

```python
LOW_RES_SIDE = 400
REQUIRED_FIELDS = ("id", "name", "aliases", "country", "league", "logo")


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _club_errors(entry) -> list[str]:
    if not isinstance(entry, dict):
        return [f"Club entry is not an object: {entry!r}"]
    label = entry.get("id", "<no id>")
    missing = [field for field in REQUIRED_FIELDS if field not in entry]
    if missing:
        return [f"Club '{label}' is missing field(s): {', '.join(missing)}"]
    errors = []
    if not isinstance(entry["id"], str) or not ID_RE.match(entry["id"]):
        errors.append(f"Invalid club id: {entry['id']!r}")
    if not isinstance(entry["name"], str) or not entry["name"].strip():
        errors.append(f"Club '{label}' has an empty name")
    if not isinstance(entry["aliases"], list) or not all(isinstance(a, str) for a in entry["aliases"]):
        errors.append(f"Club '{label}' aliases must be a list of strings")
    if not isinstance(entry["country"], str) or not COUNTRY_RE.match(entry["country"]):
        errors.append(f"Club '{label}' has invalid country: {entry['country']!r}")
    for field in ("league", "logo"):
        if entry[field] is not None and not isinstance(entry[field], str):
            errors.append(f"Club '{label}' {field} must be a string or null")
    return errors


def validate_clubs(root: Path, catalog, competitions: list[dict], mapping: dict) -> tuple[list[str], list[str]]:
    clubs = catalog.get("clubs") if isinstance(catalog, dict) else None
    if not isinstance(clubs, list):
        return ["Clubs catalog must be an object with a 'clubs' list"], []
    errors = [error for entry in clubs for error in _club_errors(entry)]
    if errors:
        return errors, []

    warnings = []
    ids = [c["id"] for c in clubs]
    errors.extend(f"Duplicate id: '{i}'" for i in sorted({i for i in ids if ids.count(i) > 1}))
    leagues = {c["id"] for c in competitions if c.get("type") == "league"}
    referenced = set()
    for entry in clubs:
        club_id = entry["id"]
        if entry["league"] is not None and entry["league"] not in leagues:
            errors.append(f"Club '{club_id}' has unknown league: {entry['league']!r}")
        logo = entry["logo"]
        if logo is None:
            warnings.append(f"Club '{club_id}' has no logo yet")
            continue
        referenced.add(logo)
        expected = f"{CLUBS_DIR}/{entry['country'].lower()}/{club_id}.png"
        if logo != expected:
            errors.append(f"Club '{club_id}' logo must be '{expected}', got '{logo}'")
        elif not (root / logo).is_file():
            errors.append(f"Club '{club_id}' logo not found: {logo}")
        elif not has_alpha(root / logo):
            errors.append(f"Club '{club_id}' logo has no transparent pixels: {logo}")
        else:
            with Image.open(root / logo) as image:
                if max(image.size) < LOW_RES_SIDE:
                    warnings.append(f"Club '{club_id}' logo is low resolution {image.size}: {logo}")

    clubs_dir = root / CLUBS_DIR
    if clubs_dir.exists():
        for path in sorted(clubs_dir.rglob("*")):
            if path.is_file() and not path.name.startswith("."):
                relative = path.relative_to(root).as_posix()
                if relative not in referenced:
                    errors.append(f"Image not referenced by the clubs catalog: {relative}")

    errors.extend(build_club_lookup(clubs)[1])
    known = set(ids)
    for key in sorted(mapping):
        if mapping[key]["id"] not in known:
            errors.append(f"Mapping '{key}' points to unknown club '{mapping[key]['id']}'")
    return errors, warnings
```

- [ ] **Step 4: Ejecutar → pasa.** `python -m unittest discover -s tests` → `OK`
- [ ] **Step 5: Commit** — mensaje `Validate the football clubs catalog`

---

### Task 6: Conectar clubes a `build_index.py` y `validate_assets.py`

**Files:**
- Create: `data/football/clubs.json` (`{"version": 1, "clubs": []}`), `data/football/clubs-mapping.json` (`{}`)
- Modify: `scripts/build_index.py`, `scripts/validate_assets.py`

- [ ] **Step 1: Datos vacíos**

```bash
printf '{\n  "version": 1,\n  "clubs": []\n}\n' > data/football/clubs.json
printf '{}\n' > data/football/clubs-mapping.json
```

- [ ] **Step 2: `build_index.py`** — import `from football_clubs import CLUBS_FILE, CLUBS_LOOKUP_FILE, build_club_lookup, club_assets, load_json`; en `main()` tras el lookup de competiciones:

```python
    clubs = load_json(CLUBS_FILE, {"clubs": []})["clubs"]
    club_lookup, club_errors = build_club_lookup(clubs)
    if club_errors:
        for error in club_errors:
            print("ERROR:", error)
        sys.exit(1)
    write_json(CLUBS_LOOKUP_FILE, club_lookup)
```

y en `all_assets`, tras `"competitions"`: `"clubs": club_assets(clubs),`; al final `print(f"  club lookup: {sum(len(t) for t in club_lookup.values())} name(s)")`.

- [ ] **Step 3: `validate_assets.py`** — añadir `ROOT / "football" / "clubs"` a `ASSET_DIRS`; import `from football_clubs import CLUBS_FILE, MAPPING_FILE, load_json, validate_clubs`; nueva función llamada desde `main()` tras `check_catalog`:

```python
def check_clubs(errors: list, warnings: list) -> None:
    try:
        clubs = load_json(CLUBS_FILE, None)
        mapping = load_json(MAPPING_FILE, {})
        competitions = load_catalog()["competitions"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"Cannot read clubs data: {exc}")
        return
    if clubs is None:
        errors.append(f"Missing {CLUBS_FILE.relative_to(ROOT).as_posix()}")
        return
    club_errors, club_warnings = validate_clubs(ROOT, clubs, competitions, mapping)
    errors.extend(club_errors)
    warnings.extend(club_warnings)
```

- [ ] **Step 4: Verificar**

Run: `python -m unittest discover -s tests && python scripts/validate_assets.py | tail -1 && python scripts/build_index.py && git status --short data`
Expected: `OK`, `Validation passed. 0 warning(s).`, `club lookup: 0 name(s)`, nuevos `clubs-lookup.json` (`{}`) y `all-assets.json` con `"clubs": {}`.

- [ ] **Step 5: Commit** — `git add -A scripts data` · mensaje `Index and validate football clubs`

---

### Task 7: `scripts/sync_clubs.py` y primera ejecución de `plan`

**Files:**
- Create: `scripts/sync_clubs.py`

- [ ] **Step 1: Escribir el script**

```python
"""Sync football club crests.

Roster from github.com/luukhopman/football-logos, images from football-logos.cc
(github.com/Leo4815162342/football-logos), luukhopman's 139x181 PNG as fallback.

  python scripts/sync_clubs.py plan               propose matches for unmapped clubs and render review sheets
  python scripts/sync_clubs.py accept [COUNTRY]   copy proposals into data/football/clubs-mapping.json
  python scripts/sync_clubs.py apply              download crests, update data/football/clubs.json, rebuild indexes
"""

from datetime import date
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw

from football_catalog import ROOT
from football_clubs import (
    CLUBS_DIR, CLUBS_FILE, COUNTRY_CODES, FL_COUNTRIES, MAPPING_FILE,
    load_json, luuk_index, merge_clubs, propose,
)
from normalize_logo import normalize_logo

CACHE = ROOT / ".cache" / "clubs"
PROPOSALS_FILE = CACHE / "proposals.json"
SOURCES_FILE = ROOT / "data" / "sources.json"
BUILD_INDEX = ROOT / "scripts" / "build_index.py"
LUUK_TREE = "https://api.github.com/repos/luukhopman/football-logos/git/trees/master?recursive=1"
LUUK_RAW = "https://raw.githubusercontent.com/luukhopman/football-logos/master/"
FL_PAGE = "https://football-logos.cc/{}/"
HEADERS = {"User-Agent": "sports-assets-sync/1.0 (https://github.com/IsaacPrestol/sports-assets)"}
THUMB = 150


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def cached(url: str, path: Path) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(fetch(url))
    return path


def write_json(path: Path, data, sort_keys: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=sort_keys) + "\n", encoding="utf-8")


def luuk_url(path: str) -> str:
    return LUUK_RAW + urllib.parse.quote(path)


def load_luuk() -> dict:
    tree = json.loads(fetch(LUUK_TREE))
    return luuk_index([entry["path"] for entry in tree["tree"] if entry["type"] == "blob"])


def load_fl() -> dict[str, dict[str, str]]:
    """Country folder -> {slug: 1500px image URL}."""
    result = {}
    for folder, fl_country in FL_COUNTRIES.items():
        html = fetch(FL_PAGE.format(fl_country)).decode("utf-8", errors="ignore")
        pattern = rf"assets\.football-logos\.cc/logos/{fl_country}/1500x1500/([a-z0-9-]+)\.[0-9a-f]{{8}}\.png"
        result[folder] = {
            match.group(1): "https://" + match.group(0)
            for match in re.finditer(pattern, html)
        }
    return result


def existing_ids(clubs: list[dict], mapping: dict) -> dict[str, str]:
    ids = {club["id"]: club["country"] for club in clubs}
    for key, entry in mapping.items():
        ids.setdefault(entry["id"], COUNTRY_CODES[key.split("|")[0]])
    return ids


def thumbnail(path: Path | None) -> Image.Image:
    canvas = Image.new("RGBA", (THUMB, THUMB), (200, 200, 200, 255))
    if path is not None:
        with Image.open(path) as image:
            logo = image.convert("RGBA")
        logo.thumbnail((THUMB - 10, THUMB - 10))
        canvas.alpha_composite(logo, ((THUMB - logo.width) // 2, (THUMB - logo.height) // 2))
    return canvas


def render_sheet(rows: list[tuple[str, Path, Path | None]], out: Path) -> None:
    columns, cell_w, cell_h = 3, THUMB * 2 + 30, THUMB + 40
    lines = (len(rows) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_w, max(lines, 1) * cell_h), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (label, luuk_path, fl_path) in enumerate(rows):
        x, y = (index % columns) * cell_w, (index // columns) * cell_h
        sheet.paste(thumbnail(luuk_path).convert("RGB"), (x + 5, y + 5))
        sheet.paste(thumbnail(fl_path).convert("RGB"), (x + THUMB + 15, y + 5))
        draw.text((x + 5, y + THUMB + 10), label, fill="black")
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=85)


def plan() -> None:
    luuk, fl = load_luuk(), load_fl()
    mapping = load_json(MAPPING_FILE, {})
    clubs = load_json(CLUBS_FILE, {"clubs": []})["clubs"]
    fl_slugs = {folder: sorted(slugs) for folder, slugs in fl.items()}
    proposals = propose(luuk, mapping, fl_slugs, existing_ids(clubs, mapping))
    write_json(PROPOSALS_FILE, proposals, sort_keys=True)

    by_country: dict[str, list] = {}
    for key, proposal in sorted(proposals.items()):
        folder = key.split("|")[0]
        luuk_path = cached(luuk_url(luuk[key]["latest_path"]), CACHE / "luuk" / luuk[key]["latest_path"])
        fl_path = None
        if proposal["slug"]:
            fl_path = cached(fl[folder][proposal["slug"]], CACHE / "fl" / FL_COUNTRIES[folder] / f"{proposal['slug']}.png")
        label = f"{luuk[key]['name'][:28]} -> {proposal['id'][:24]} [{proposal['match']}]"
        by_country.setdefault(folder, []).append((label, luuk_path, fl_path))
    for folder, rows in by_country.items():
        render_sheet(rows, CACHE / f"review-{FL_COUNTRIES[folder]}.jpg")

    counts = {kind: sum(p["match"] == kind for p in proposals.values()) for kind in ("exact", "fuzzy", "none")}
    print(f"{len(proposals)} unmapped club(s): {counts}")
    print(f"Proposals: {PROPOSALS_FILE.relative_to(ROOT).as_posix()}; review sheets in {CACHE.relative_to(ROOT).as_posix()}/")


def accept(country: str | None) -> None:
    proposals = load_json(PROPOSALS_FILE, {})
    mapping = load_json(MAPPING_FILE, {})
    added = 0
    for key, proposal in proposals.items():
        if country and key.split("|")[0] != country:
            continue
        if key not in mapping:
            mapping[key] = {"id": proposal["id"], "source": proposal["source"], "slug": proposal["slug"]}
            added += 1
    write_json(MAPPING_FILE, mapping, sort_keys=True)
    print(f"Accepted {added} proposal(s)")


def apply() -> None:
    luuk, fl = load_luuk(), load_fl()
    mapping = load_json(MAPPING_FILE, {})
    unmapped = sorted(key for key in luuk if key not in mapping)
    if unmapped:
        for key in unmapped:
            print("UNMAPPED:", key)
        sys.exit(f"{len(unmapped)} club(s) are not in {MAPPING_FILE.name}; run plan and accept first")

    catalog = load_json(CLUBS_FILE, {"version": 1, "clubs": []})
    sources = load_json(SOURCES_FILE, {})
    keys_by_id: dict[str, list[str]] = {}
    for key in sorted(mapping):
        if key in luuk:
            keys_by_id.setdefault(mapping[key]["id"], []).append(key)

    missing = set()
    for club_id, keys in sorted(keys_by_id.items()):
        folder = keys[0].split("|")[0]
        relative = f"{CLUBS_DIR}/{COUNTRY_CODES[folder].lower()}/{club_id}.png"
        destination = ROOT / relative
        if destination.exists():
            continue
        slug = next((mapping[k]["slug"] for k in keys if mapping[k]["source"] == "football-logos"), None)
        try:
            if slug:
                url = fl[folder][slug]
                notes = "Via github.com/Leo4815162342/football-logos (football-logos.cc)"
                raw = cached(url, CACHE / "fl" / FL_COUNTRIES[folder] / f"{slug}.png")
            else:
                latest = max((luuk[k] for k in keys), key=lambda entry: entry["latest_season"])
                url = luuk_url(latest["latest_path"])
                notes = "github.com/luukhopman/football-logos (139x181 fallback)"
                raw = cached(url, CACHE / "luuk" / latest["latest_path"])
            normalize_logo(raw, destination)
        except (KeyError, OSError, ValueError) as exc:
            print(f"WARNING: {club_id}: {exc}")
            missing.add(club_id)
            continue
        sources[relative] = {"url": url, "retrieved": date.today().isoformat(), "license": None, "notes": notes}

    clubs, skipped = merge_clubs(catalog["clubs"], mapping, luuk, missing)
    for message in skipped:
        print("SKIPPED ALIAS:", message)
    write_json(CLUBS_FILE, {"version": 1, "clubs": clubs})
    write_json(SOURCES_FILE, sources, sort_keys=True)
    print(f"{len(clubs)} club(s) in catalog, {len(missing)} without logo")
    subprocess.run([sys.executable, str(BUILD_INDEX)], check=True, cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    accept_parser = sub.add_parser("accept")
    accept_parser.add_argument("country", nargs="?", help="luukhopman country folder, e.g. Spain")
    sub.add_parser("apply")
    args = parser.parse_args()
    if args.command == "plan":
        plan()
    elif args.command == "accept":
        accept(args.country)
    else:
        apply()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Ejecutar `plan`**

Run: `python scripts/sync_clubs.py plan`
Expected: `~697 unmapped club(s): {'exact': …, 'fuzzy': …, 'none': …}` y 26 archivos `.cache/clubs/review-*.jpg`.

- [ ] **Step 3: Commit** — `git add scripts/sync_clubs.py` · mensaje `Add club crest sync script`

---

### Task 8: Revisión y correspondencias — 7 ligas principales

**Países:** England, Spain, Italy, Germany, France, Netherlands, Portugal.

- [ ] **Step 1:** Para cada país, abrir `.cache/clubs/review-<país>.jpg` con Read. Cada celda: escudo de luukhopman (izquierda) y propuesto de football-logos.cc (derecha), etiqueta `nombre -> id [match]`.
- [ ] **Step 2:** `python scripts/sync_clubs.py accept <País>`.
- [ ] **Step 3:** Corregir en `data/football/clubs-mapping.json` cada emparejamiento incorrecto:
  - escudo distinto → buscar el slug correcto en `.cache` / página de país y ponerlo, o `"source": "luukhopman", "slug": null`;
  - `[none]` cuyo club sí existe en football-logos.cc con otro nombre → poner su slug y `"source": "football-logos"`;
  - nombres del mismo club con ids distintos → unificar al mismo `id`.
  - Mantener ids en kebab-case con la regla del spec (slug de football-logos.cc o nombre sin afijos; sufijo de país si choca).
- [ ] **Step 4:** Re-ejecutar `python scripts/sync_clubs.py plan` no debe proponer ninguna clave de estos países.
- [ ] **Step 5: Commit** — `git add data/football/clubs-mapping.json` · mensaje `Map clubs of the top 7 leagues`

---

### Task 9: Revisión y correspondencias — resto de países

**Países:** Austria, Belgium, Bulgaria, Croatia, Czech Republic, Denmark, Greece, Hungary, Israel, Norway, Poland, Romania, Russia, Scotland, Serbia, Sweden, Switzerland, Türkiye, Ukraine.

- [ ] **Steps 1–4:** Igual que Task 8 para cada país.
- [ ] **Step 5:** `python scripts/sync_clubs.py plan` → `0 unmapped club(s)`.
- [ ] **Step 6: Commit** — mensaje `Map clubs of the remaining leagues`

---

### Task 10: `apply` y verificación

- [ ] **Step 1:** `python scripts/sync_clubs.py apply` → sin `UNMAPPED`; anotar `WARNING` y `SKIPPED ALIAS`.
- [ ] **Step 2:** `python -m unittest discover -s tests && python scripts/validate_assets.py | tail -3` → `OK`, `Validation passed.` (avisos solo de baja resolución / sin logo).
- [ ] **Step 3:** Revisión visual por muestreo: hoja de 30 escudos finales al azar (`python .cache/sheet.py` sobre rutas de `football/clubs/**`), comprobar que ninguno está mal recortado ni es de otro club.
- [ ] **Step 4:** Comprobar lookup:
  ```bash
  python -c "import json; l=json.load(open('data/football/clubs-lookup.json',encoding='utf-8')); print(l['ES']['real madrid'], l['GB-ENG']['arsenal'], l['PT'].get('sporting cp'), l['DE'].get('bayern munich') or l['DE'].get('bayern munchen'))"
  ```
- [ ] **Step 5:** Re-ejecutar `apply` → no descarga nada nuevo y `git status` sin cambios (idempotencia).
- [ ] **Step 6: Commit** — `git add -A football data` · mensaje `Add crests for clubs of the 25 leagues`

---

### Task 11: README

- [ ] **Step 1:** En "Estructura", añadir `football/clubs/<país>/`, `data/football/clubs.json`, `clubs-mapping.json`, `clubs-lookup.json` y `scripts/football_clubs.py`, `scripts/sync_clubs.py`.
- [ ] **Step 2:** Nueva sección `## Clubes de fútbol`: esquema del catálogo (tabla de campos del spec), uso desde la app (normalizar nombre → `clubs-lookup.json[país][nombre]` → `clubs.json` → URL jsDelivr), y actualización por temporada:
  ```bash
  python scripts/sync_clubs.py plan
  # revisar .cache/clubs/review-*.jpg
  python scripts/sync_clubs.py accept
  # corregir data/football/clubs-mapping.json si hace falta
  python scripts/sync_clubs.py apply
  ```
- [ ] **Step 3:** `python -m unittest discover -s tests && python scripts/validate_assets.py | tail -1` → `OK`, `Validation passed.`
- [ ] **Step 4: Commit** — mensaje `Document football clubs catalog and sync`
