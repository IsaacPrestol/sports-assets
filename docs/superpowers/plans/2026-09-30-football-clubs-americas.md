# Escudos de clubes de América — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir los clubes de primera división de 16 ligas de CONMEBOL y CONCACAF (temporada actual y desde 2022) al catálogo de clubes, con escudos transparentes y el mismo flujo `plan/accept/apply`.

**Architecture:** Un archivo de plantillas mantenido a mano (`data/football/rosters.json`) se convierte con `roster_index` en entradas con la misma forma que las de luukhopman; `sync_clubs.py` combina los dos índices, de modo que propuesta, revisión visual, fusión y validación no cambian. Las correspondencias admiten `"source": "url"` para escudos que no están en football-logos.cc.

**Tech Stack:** Python 3.12, Pillow, `unittest` (stdlib), `urllib`.

**Spec:** `docs/superpowers/specs/2026-09-30-football-clubs-americas-design.md`

## Global Constraints

- Tests: `python -m unittest discover -s tests -v` (sin pytest). Los tests importan desde `scripts/` vía `sys.path`.
- Logos: PNG con píxeles transparentes, recortado, lado mayor ≤ 1024 px, nunca ampliado (`scripts/normalize_logo.py`).
- País de un club = `country` de su liga en `competitions.json`. Los clubes canadienses de la MLS llevan `US`.
- Temporadas: `AAAA` (año natural) o `AAAA-AA` (cruzan dos años), una sola forma por liga. Desde 2022 / 2022-23 hasta la actual.
- Ligas con temporada `AAAA-AA`: `liga-mx`, `costa-rican-primera-division`, `guatemalan-liga-nacional`. El resto, `AAAA`.
- Nombres de club en `rosters.json`: tal como aparecen en la Wikipedia en inglés.
- Ningún alias de competición puede ser uno de `RealCatalogTest.GENERIC_ALIASES`.
- JSON escrito con `ensure_ascii=False, indent=2` y salto de línea final (como `write_json` de `sync_clubs.py`).
- Commits con identidad local del repo; mensajes terminados en `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- No hacer push ni merge.
- `football/clubs/tr/fenerbahce.png` tiene un cambio local del usuario: no hacer `git add` de ese archivo ni `git add -A`.

## Review Focus

1. Un club que cambia de nombre entre temporadas (p. ej. "York United" → "Inter Toronto FC") aparece como dos claves; ambas deben ir al mismo id y el nombre antiguo quedar como alias. Test: `RosterIndexTest.test_renamed_club_is_one_club`.
2. Una correspondencia aceptada con `"source": "url"` pero sin URL rellenada no debe llegar a CI en silencio: `validate_clubs` la rechaza. Test: `ValidateClubsTest.test_url_source_needs_https_url`.
3. Temporadas con formatos mezclados en una liga harían que la "actual" fuera la equivocada. Test: `RosterErrorsTest.test_season_format`.
4. Un nombre repetido en una temporada con otra grafía ("Club Nacional" / "club nacional") produciría dos claves del mismo club. Test: `RosterErrorsTest.test_club_names`.
5. Volver a ejecutar `apply` sin cambios no debe modificar nada (`git status` limpio). Paso explícito en la Task 7.

---

### Task 1: Doce ligas nuevas en el catálogo de competiciones

**Files:**
- Modify: `data/football/competitions.json`, `data/sources.json`, `data/football/competitions-lookup.json` (regenerado), `data/all-assets.json` (regenerado)
- Create: 12 PNG en `football/competitions/south-america/` y `football/competitions/north-america/`
- Test: `tests/test_football_catalog.py`

**Interfaces:**
- Produces: competiciones de tipo `league` con estos ids y países, usadas por `rosters.json` (Task 5):

| id | name | aliases | continent / confederation | country | slug en football-logos.cc |
|---|---|---|---|---|---|
| `uruguayan-primera-division` | Liga AUF Uruguaya | Uruguayan Primera División, Campeonato Uruguayo | south-america / CONMEBOL | UY | `uruguay/liga-auf-uruguaya` |
| `colombian-primera-a` | Categoría Primera A | Liga BetPlay, Liga BetPlay Dimayor, Colombian Primera A | south-america / CONMEBOL | CO | `colombia/categoria-primera-a` |
| `chilean-primera-division` | Liga de Primera | Chilean Primera División, Campeonato Nacional de Chile | south-america / CONMEBOL | CL | `chile/liga-de-primera` |
| `paraguayan-primera-division` | Paraguayan Primera División | División de Honor, Copa de Primera | south-america / CONMEBOL | PY | `paraguay/copa-de-primera` |
| `peruvian-liga-1` | Peruvian Liga 1 | Liga 1 Perú, Peruvian Primera División | south-america / CONMEBOL | PE | `peru/peruvian-primera-division` |
| `ecuadorian-serie-a` | LigaPro Serie A | Ecuadorian Serie A, LigaPro | south-america / CONMEBOL | EC | `ecuador/liga-pro-serie-a` |
| `bolivian-primera-division` | Bolivian Primera División | División Profesional de Bolivia | south-america / CONMEBOL | BO | `bolivia/primera-division-de-bolivia` |
| `venezuelan-primera-division` | Liga FUTVE | Venezuelan Primera División | south-america / CONMEBOL | VE | `venezuela/primera-division-de-venezuela` |
| `canadian-premier-league` | Canadian Premier League | CPL | north-america / CONCACAF | CA | `canada/canadian-premier-league` |
| `costa-rican-primera-division` | Liga FPD | Costa Rican Primera División, Primera División de Costa Rica | north-america / CONCACAF | CR | `costa-rica/primera-division` |
| `guatemalan-liga-nacional` | Liga Nacional de Guatemala | Liga Guate | north-america / CONCACAF | GT | `guatemala/liga-nacional-de-futbol-de-guatemala` |
| `panamanian-football-league` | Liga Panameña de Fútbol | Panamanian Football League, LPF Panamá | north-america / CONCACAF | PA | `panama/panamanian-football-league` |

Todas con `"type": "league"`, `"scope": "club"`, `"collage": null`, `"logo": "football/competitions/<continent>/<id>.png"`.

- [ ] **Step 1: Write the failing test**

Añadir a `RealCatalogTest` en `tests/test_football_catalog.py`:

```python
    AMERICAN_LEAGUES = {
        "brasileirao-serie-a": "BR", "liga-profesional-argentina": "AR",
        "uruguayan-primera-division": "UY", "colombian-primera-a": "CO",
        "chilean-primera-division": "CL", "paraguayan-primera-division": "PY",
        "peruvian-liga-1": "PE", "ecuadorian-serie-a": "EC",
        "bolivian-primera-division": "BO", "venezuelan-primera-division": "VE",
        "liga-mx": "MX", "mls": "US", "canadian-premier-league": "CA",
        "costa-rican-primera-division": "CR", "guatemalan-liga-nacional": "GT",
        "panamanian-football-league": "PA",
    }

    def test_american_leagues_have_country_and_logo(self):
        by_id = {c["id"]: c for c in load_catalog()["competitions"]}
        for league_id, country in self.AMERICAN_LEAGUES.items():
            competition = by_id.get(league_id)
            self.assertIsNotNone(competition, league_id)
            self.assertEqual((competition["type"], competition["country"]), ("league", country), league_id)
            self.assertIsNotNone(competition["logo"], league_id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_football_catalog.RealCatalogTest -v`
Expected: FAIL en `test_american_leagues_have_country_and_logo` con `uruguayan-primera-division` (`None` is not not None).

- [ ] **Step 3: Download and normalize the 12 logos**

Para cada fila de la tabla, obtener la URL de 1500 px de la página del país y normalizarla. Script de un solo uso (en `.cache/`, no se commitea):

```python
# .cache/americas_logos.py
import re, subprocess, sys, urllib.request
ROWS = [
    ("uruguayan-primera-division", "south-america", "uruguay", "liga-auf-uruguaya"),
    ("colombian-primera-a", "south-america", "colombia", "categoria-primera-a"),
    ("chilean-primera-division", "south-america", "chile", "liga-de-primera"),
    ("paraguayan-primera-division", "south-america", "paraguay", "copa-de-primera"),
    ("peruvian-liga-1", "south-america", "peru", "peruvian-primera-division"),
    ("ecuadorian-serie-a", "south-america", "ecuador", "liga-pro-serie-a"),
    ("bolivian-primera-division", "south-america", "bolivia", "primera-division-de-bolivia"),
    ("venezuelan-primera-division", "south-america", "venezuela", "primera-division-de-venezuela"),
    ("canadian-premier-league", "north-america", "canada", "canadian-premier-league"),
    ("costa-rican-primera-division", "north-america", "costa-rica", "primera-division"),
    ("guatemalan-liga-nacional", "north-america", "guatemala", "liga-nacional-de-futbol-de-guatemala"),
    ("panamanian-football-league", "north-america", "panama", "panamanian-football-league"),
]
UA = {"User-Agent": "sports-assets-sync/1.0 (https://github.com/IsaacPrestol/sports-assets)"}
for league_id, continent, country, slug in ROWS:
    html = urllib.request.urlopen(urllib.request.Request(f"https://football-logos.cc/{country}/", headers=UA)).read().decode()
    url = "https://" + re.search(rf"assets\.football-logos\.cc/logos/{country}/1500x1500/{slug}\.[0-9a-f]{{8}}\.png", html).group(0)
    raw = f".cache/logos/{league_id}.png"
    open(raw, "wb").write(urllib.request.urlopen(urllib.request.Request(url, headers=UA)).read())
    subprocess.run([sys.executable, "scripts/normalize_logo.py", raw, f"football/competitions/{continent}/{league_id}.png"], check=True)
    print(league_id, url)
```

Run: `python .cache/americas_logos.py`
Expected: 12 líneas `<id> https://assets.football-logos.cc/...png`, sin excepciones.

Revisar visualmente los 12 PNG (hoja de contacto sobre fondo gris). Si alguno es opaco, lleva marca de agua o no es el logo de la liga, sustituirlo por el PNG de Wikimedia (URL `thumb` de 3840 px de la API `imageinfo`) y anotar la decisión como Ruling.

- [ ] **Step 4: Add catalog entries and sources**

Añadir las 12 entradas de la tabla a `data/football/competitions.json` (después de las demás de su continente) y una entrada por logo en `data/sources.json`:

```json
"football/competitions/south-america/uruguayan-primera-division.png": {
  "license": null,
  "notes": "Via github.com/Leo4815162342/football-logos (football-logos.cc)",
  "retrieved": "2026-09-30",
  "url": "<URL impresa en el Step 3>"
}
```

Luego: `python scripts/build_index.py`
Expected: termina sin errores. Si informa de una colisión de alias (p. ej. `LPF Panamá` o `Liga 1 Perú` con otra competición), quitar ese alias de la liga nueva y anotarlo como Ruling.

- [ ] **Step 5: Run tests and validation**

Run: `python -m unittest discover -s tests` y `python scripts/validate_assets.py`
Expected: `OK`; `Validation passed.`

- [ ] **Step 6: Commit**

```bash
git add tests/test_football_catalog.py data/football/competitions.json data/football/competitions-lookup.json data/sources.json data/all-assets.json football/competitions/south-america football/competitions/north-america
git commit -m "Add the 12 remaining American leagues to the competitions catalog"
```

---

### Task 2: Índice de plantillas y liga en las entradas del índice

**Files:**
- Modify: `scripts/football_clubs.py`
- Test: `tests/test_football_clubs.py`

**Interfaces:**
- Consumes: ids de liga de la Task 1 (solo como datos de ejemplo en los tests).
- Produces:
  - `ROSTERS_FILE = ROOT / "data" / "football" / "rosters.json"`
  - `COUNTRY_CODES` con 16 países nuevos; `FL_COUNTRIES` los incluye (derivado), con `"United States": "usa"`.
  - Entradas de índice (de `luuk_index` y `roster_index`) con las claves `country_folder`, `name`, `league_folder`, `league`, `latest_season`, `latest_path`. `league` es un id de competición o `None`.
  - `roster_index(rosters: dict, competitions: list[dict]) -> dict[str, dict]`, clave `"<country_folder>|<name>"`, `league_folder` siempre `None`, `latest_path` siempre `None`.
  - `propose(...)` devuelve `"source": "url"` cuando no hay slug y la entrada no tiene `latest_path`.
  - `merge_clubs` toma la liga actual del campo `league` de las entradas.

- [ ] **Step 1: Write the failing tests**

En `tests/test_football_clubs.py`, añadir `roster_index` a la importación de `football_clubs`, añadir este test a `LuukIndexTest`:

```python
    def test_entries_carry_league_id(self):
        index = luuk_index(PATHS)
        self.assertEqual(index["Spain|Real Madrid"]["league"], "laliga")
        self.assertIsNone(index["Spain|UD Almería"]["league"])
```

y esta clase después de `SyncSafetyTest`:

```python
ROSTERS = {
    "brasileirao-serie-a": {
        "2025": ["Flamengo", "Sport Recife"],
        "2026": ["Flamengo", "Coritiba"],
    },
    "canadian-premier-league": {
        "2025": ["York United"],
        "2026": ["Inter Toronto FC"],
    },
    "mls": {"2026": ["Toronto FC"]},
}
COMPETITIONS = [
    {"id": "brasileirao-serie-a", "type": "league", "country": "BR"},
    {"id": "canadian-premier-league", "type": "league", "country": "CA"},
    {"id": "mls", "type": "league", "country": "US"},
    {"id": "copa-libertadores", "type": "international", "country": None},
]


class RosterIndexTest(unittest.TestCase):
    def setUp(self):
        self.index = roster_index(ROSTERS, COMPETITIONS)

    def test_current_club(self):
        self.assertEqual(self.index["Brazil|Flamengo"], {
            "country_folder": "Brazil", "name": "Flamengo", "league_folder": None,
            "league": "brasileirao-serie-a", "latest_season": "2026", "latest_path": None,
        })

    def test_relegated_club_has_no_league(self):
        club = self.index["Brazil|Sport Recife"]
        self.assertIsNone(club["league"])
        self.assertEqual(club["latest_season"], "2025")

    def test_country_comes_from_the_league(self):
        self.assertEqual(self.index["United States|Toronto FC"]["country_folder"], "United States")
        self.assertEqual(len(self.index), 6)

    def test_merge_uses_roster_league_and_country(self):
        mapping = {
            "Brazil|Flamengo": {"id": "flamengo", "source": "football-logos", "slug": "flamengo"},
            "Brazil|Sport Recife": {"id": "sport-recife", "source": "url", "slug": None,
                                    "url": "https://example.org/sport.png"},
        }
        clubs, _ = merge_clubs([], mapping, self.index)
        by_id = {c["id"]: c for c in clubs}
        self.assertEqual(by_id["flamengo"]["league"], "brasileirao-serie-a")
        self.assertEqual(by_id["flamengo"]["country"], "BR")
        self.assertEqual(by_id["flamengo"]["logo"], "football/clubs/br/flamengo.png")
        self.assertIsNone(by_id["sport-recife"]["league"])

    def test_renamed_club_is_one_club(self):
        mapping = {
            "Canada|York United": {"id": "inter-toronto", "source": "football-logos", "slug": "inter-toronto-fc"},
            "Canada|Inter Toronto FC": {"id": "inter-toronto", "source": "football-logos", "slug": "inter-toronto-fc"},
        }
        clubs, _ = merge_clubs([], mapping, self.index)
        self.assertEqual(len(clubs), 1)
        self.assertEqual(clubs[0]["name"], "Inter Toronto FC")
        self.assertIn("York United", clubs[0]["aliases"])
        self.assertEqual(clubs[0]["league"], "canadian-premier-league")

    def test_propose_without_slug_asks_for_url(self):
        proposals = propose(self.index, {}, {"Brazil": ["flamengo"], "Canada": [], "United States": []}, {})
        self.assertEqual(proposals["Brazil|Flamengo"]["source"], "football-logos")
        self.assertEqual(proposals["United States|Toronto FC"],
                         {"id": "toronto", "source": "url", "slug": None, "match": "none"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_football_clubs -v`
Expected: ERROR al importar: `ImportError: cannot import name 'roster_index'`.

- [ ] **Step 3: Implement**

En `scripts/football_clubs.py`:

1. Debajo de `MAPPING_FILE`:

```python
ROSTERS_FILE = ROOT / "data" / "football" / "rosters.json"
```

2. En `COUNTRY_CODES`, añadir (manteniendo el orden alfabético):

```python
    "Argentina": "AR", "Bolivia": "BO", "Brazil": "BR", "Canada": "CA", "Chile": "CL",
    "Colombia": "CO", "Costa Rica": "CR", "Ecuador": "EC", "Guatemala": "GT",
    "Mexico": "MX", "Panama": "PA", "Paraguay": "PY", "Peru": "PE",
    "United States": "US", "Uruguay": "UY", "Venezuela": "VE",
```

y en `FL_COUNTRIES`: `} | {"Türkiye": "turkey", "United States": "usa"}`.

3. En `luuk_index`, añadir `"league": None,` al diccionario creado con `setdefault` (después de `"league_folder": None,`) y sustituir

```python
        if season == CURRENT_SEASON:
            club["league_folder"] = league_folder
```

por

```python
        if season == CURRENT_SEASON:
            club["league_folder"] = league_folder
            club["league"] = LEAGUE_IDS.get(league_folder)
```

4. Después de `luuk_index`:

```python
def roster_index(rosters: dict, competitions: list[dict]) -> dict[str, dict]:
    """Index data/football/rosters.json like luuk_index; the country of every club is its league's."""
    folders = {code: folder for folder, code in COUNTRY_CODES.items()}
    countries = {competition["id"]: competition["country"] for competition in competitions}
    clubs: dict[str, dict] = {}
    for league in sorted(rosters):
        folder = folders[countries[league]]
        seasons = rosters[league]
        current = max(seasons)
        for season in sorted(seasons):
            for name in seasons[season]:
                club = clubs.setdefault(f"{folder}|{name}", {
                    "country_folder": folder,
                    "name": name,
                    "league_folder": None,
                    "league": None,
                    "latest_season": "",
                    "latest_path": None,
                })
                if season == current:
                    club["league"] = league
                if season > club["latest_season"]:
                    club["latest_season"] = season
    return clubs
```

5. En `propose`, sustituir `"source": "football-logos" if slug else "luukhopman",` por `"source": source,` y antes del `proposals[key] = {` añadir:

```python
        if slug:
            source = "football-logos"
        elif club["latest_path"]:
            source = "luukhopman"
        else:
            source = "url"
```

6. En `merge_clubs`, sustituir

```python
        current = [entry for entry in entries if entry["league_folder"]]
        league = LEAGUE_IDS[current[0]["league_folder"]] if current else None
```

por

```python
        current = [entry for entry in entries if entry["league"]]
        league = current[0]["league"] if current else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest discover -s tests`
Expected: `OK` (94 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/football_clubs.py tests/test_football_clubs.py
git commit -m "Index hand-maintained club rosters like luukhopman"
```

---

### Task 3: Validación de plantillas y de correspondencias por URL

**Files:**
- Modify: `scripts/football_clubs.py`, `scripts/validate_assets.py`
- Test: `tests/test_football_clubs.py`

**Interfaces:**
- Consumes: `ROSTERS_FILE`, `COUNTRY_CODES` (Task 2); fixtures `ROSTERS`, `COMPETITIONS` (Task 2).
- Produces:
  - `SEASON_RE = re.compile(r"^\d{4}(?:-\d{2})?$")`
  - `roster_errors(rosters, competitions: list[dict]) -> list[str]`: lista vacía si es válido.
  - `validate_clubs` rechaza correspondencias con `"source": "url"` sin una `url` que empiece por `https://`.
  - `validate_assets.check_rosters(errors, warnings)`.

- [ ] **Step 1: Write the failing tests**

Añadir `roster_errors` a la importación y estas pruebas:

```python
class RosterErrorsTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(roster_errors(ROSTERS, COMPETITIONS), [])

    def test_not_an_object(self):
        self.assertEqual(len(roster_errors([], COMPETITIONS)), 1)

    def test_unknown_non_league_or_countryless_league(self):
        competitions = COMPETITIONS + [{"id": "j-league", "type": "league", "country": "JP"}]
        rosters = {"nope": {"2026": ["A"]}, "copa-libertadores": {"2026": ["A"]}, "j-league": {"2026": ["A"]}}
        self.assertEqual(len(roster_errors(rosters, competitions)), 3)

    def test_season_format(self):
        errors = roster_errors({"mls": {"2025-26": ["A"], "2026": ["B"]}}, COMPETITIONS)
        self.assertTrue(any("same format" in e for e in errors))
        errors = roster_errors({"mls": {"26": ["A"]}}, COMPETITIONS)
        self.assertTrue(any("YYYY" in e for e in errors))

    def test_empty_season(self):
        self.assertEqual(len(roster_errors({"mls": {"2026": []}}, COMPETITIONS)), 1)
        self.assertEqual(len(roster_errors({"mls": {}}, COMPETITIONS)), 1)

    def test_club_names(self):
        errors = roster_errors({"mls": {"2026": ["Club Nacional", " B", "", "club nacional"]}}, COMPETITIONS)
        self.assertEqual(len(errors), 3)
        self.assertTrue(any("repeated" in e for e in errors))
        self.assertTrue(any("spaces" in e for e in errors))
        self.assertTrue(any("empty" in e for e in errors))
```

y en `ValidateClubsTest`:

```python
    def test_url_source_needs_https_url(self):
        for entry in ({"id": "real-madrid", "source": "url", "slug": None},
                      {"id": "real-madrid", "source": "url", "slug": None, "url": None},
                      {"id": "real-madrid", "source": "url", "slug": None, "url": "http://x/y.png"}):
            errors, _ = self.validate(club(), mapping={"Spain|Real Madrid": entry})
            self.assertTrue(any("https" in e for e in errors), entry)
        ok = {"id": "real-madrid", "source": "url", "slug": None, "url": "https://upload.wikimedia.org/x.png"}
        self.assertEqual(self.validate(club(), mapping={"Spain|Real Madrid": ok})[0], [])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_football_clubs -v`
Expected: `ImportError: cannot import name 'roster_errors'`.

- [ ] **Step 3: Implement**

En `scripts/football_clubs.py`, junto a las constantes:

```python
SEASON_RE = re.compile(r"^\d{4}(?:-\d{2})?$")
```

y después de `roster_index`:

```python
def roster_errors(rosters, competitions: list[dict]) -> list[str]:
    if not isinstance(rosters, dict):
        return ["Rosters must be an object keyed by league id"]
    leagues = {c["id"]: c for c in competitions if c.get("type") == "league"}
    codes = set(COUNTRY_CODES.values())
    errors = []
    for league in sorted(rosters):
        seasons = rosters[league]
        if league not in leagues or leagues[league].get("country") not in codes:
            errors.append(f"Roster '{league}' is not a league whose country is in COUNTRY_CODES")
            continue
        if not isinstance(seasons, dict) or not seasons:
            errors.append(f"Roster '{league}' must map seasons to club lists")
            continue
        if len({len(season) for season in seasons}) > 1:
            errors.append(f"Roster '{league}' seasons must all use the same format")
        for season in sorted(seasons):
            label = f"Roster '{league}' {season}"
            if not SEASON_RE.match(season):
                errors.append(f"{label}: season must be YYYY or YYYY-YY")
            names = seasons[season]
            if not isinstance(names, list) or not names:
                errors.append(f"{label}: must be a non-empty list of club names")
                continue
            seen = set()
            for name in names:
                if not isinstance(name, str) or not name.strip():
                    errors.append(f"{label}: empty club name")
                    continue
                if name != name.strip():
                    errors.append(f"{label}: '{name}' has surrounding spaces")
                key = normalize_name(name)
                if key in seen:
                    errors.append(f"{label}: '{name}' is repeated")
                seen.add(key)
    return errors
```

En `validate_clubs`, sustituir el bucle final de correspondencias por:

```python
    for key in sorted(mapping):
        entry = mapping[key]
        if entry["id"] not in known:
            errors.append(f"Mapping '{key}' points to unknown club '{entry['id']}'")
        url = entry.get("url")
        if entry.get("source") == "url" and not (isinstance(url, str) and url.startswith("https://")):
            errors.append(f"Mapping '{key}' uses source 'url' without an https url")
```

En `scripts/validate_assets.py`, ampliar la importación a
`from football_clubs import CLUBS_FILE, MAPPING_FILE, ROSTERS_FILE, load_json, roster_errors, validate_clubs`, añadir:

```python
def check_rosters(errors: list, warnings: list) -> None:
    try:
        rosters = load_json(ROSTERS_FILE, {})
        competitions = load_catalog()["competitions"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"Cannot read rosters: {exc}")
        return
    errors.extend(roster_errors(rosters, competitions))
```

y llamar a `check_rosters(errors, warnings)` en `main()` después de `check_clubs`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest discover -s tests` y `python scripts/validate_assets.py`
Expected: `OK` (101 tests); `Validation passed.`

- [ ] **Step 5: Commit**

```bash
git add scripts/football_clubs.py scripts/validate_assets.py tests/test_football_clubs.py
git commit -m "Validate club rosters and manual crest URLs"
```

---

### Task 4: `sync_clubs.py` procesa las plantillas

**Files:**
- Modify: `scripts/sync_clubs.py`

**Interfaces:**
- Consumes: `ROSTERS_FILE`, `roster_index`, `roster_errors` (Tasks 2–3); `load_catalog` de `football_catalog`.
- Produces: `load_index() -> dict` (luukhopman + plantillas); `apply` descarga `mapping[key]["url"]` para `"source": "url"`.

- [ ] **Step 1: Wire the combined index**

1. Docstring: primera línea de fuentes → `Rosters from github.com/luukhopman/football-logos (Europe) and data/football/rosters.json (Americas),` y la de respaldo → `images from football-logos.cc (github.com/Leo4815162342/football-logos); luukhopman's 139x181 PNG or a manual url as fallback.`
2. Importaciones: `from football_catalog import ROOT, load_catalog` y añadir `ROSTERS_FILE, roster_errors, roster_index` a la importación de `football_clubs`.
3. Después de `check_folders`:

```python
def load_index() -> dict:
    competitions = load_catalog()["competitions"]
    rosters = load_json(ROSTERS_FILE, {})
    problems = roster_errors(rosters, competitions)
    if problems:
        for problem in problems:
            print("ERROR:", problem)
        sys.exit(f"Fix {ROSTERS_FILE.relative_to(ROOT).as_posix()} first")
    luuk = load_luuk()
    check_folders(luuk)
    return luuk | roster_index(rosters, competitions)
```

4. En `plan()` y en `apply()`, sustituir las dos líneas `luuk = load_luuk()` / `check_folders(luuk)` por `luuk = load_index()`.
5. En `plan()`, sustituir la línea de `luuk_path` por:

```python
        latest_path = luuk[key]["latest_path"]
        luuk_path = cached(luuk_url(latest_path), CACHE / "luuk" / latest_path) if latest_path else None
```

6. En `apply()`, sustituir el bloque desde `slug = next(...)` hasta `normalize_logo(raw, destination)` por:

```python
        slug = next((mapping[k]["slug"] for k in keys if mapping[k]["source"] == "football-logos"), None)
        manual = next((mapping[k].get("url") for k in keys if mapping[k]["source"] == "url"), None)
        try:
            if slug:
                url = fl[folder][slug]
                notes = "Via github.com/Leo4815162342/football-logos (football-logos.cc)"
                raw = cached(url, CACHE / "fl" / FL_COUNTRIES[folder] / f"{slug}.png")
            elif manual:
                url = manual
                notes = "Via Wikimedia Commons" if "wikimedia.org" in url else "Manual url in clubs-mapping.json"
                raw = cached(url, CACHE / "url" / f"{club_id}.png")
            else:
                latest = max((luuk[k] for k in keys), key=lambda entry: entry["latest_season"])
                if not latest["latest_path"]:
                    raise ValueError("no football-logos slug or url in clubs-mapping.json")
                url = luuk_url(latest["latest_path"])
                notes = "github.com/luukhopman/football-logos (139x181 fallback)"
                raw = cached(url, CACHE / "luuk" / latest["latest_path"])
            normalize_logo(raw, destination)
```

7. Ayuda de `accept`: `help="country folder, e.g. Spain or Brazil"`.

- [ ] **Step 2: Verify no regression on Europe**

Run: `python scripts/sync_clubs.py plan`
Expected: `0 unmapped club(s): {'exact': 0, 'partial': 0, 'fuzzy': 0, 'none': 0}` (aún no existe `rosters.json`).

Run: `python scripts/sync_clubs.py apply` y `git status --short`
Expected: `572 club(s) in catalog, 0 without logo`; `git status` solo muestra `football/clubs/tr/fenerbahce.png` (cambio del usuario) y `scripts/sync_clubs.py`.

- [ ] **Step 3: Run tests**

Run: `python -m unittest discover -s tests`
Expected: `OK` (101 tests).

- [ ] **Step 4: Commit**

```bash
git add scripts/sync_clubs.py
git commit -m "Sync clubs from hand-maintained rosters and manual crest urls"
```

---

### Task 5: `rosters.json` con las 16 ligas

**Files:**
- Create: `data/football/rosters.json`
- Test: `tests/test_football_clubs.py`

**Interfaces:**
- Consumes: ids de la Task 1; `roster_errors`, `ROSTERS_FILE` (Tasks 2–3).
- Produces: plantillas de todas las ligas de `continent` `south-america` o `north-america` con `type: league`.

- [ ] **Step 1: Write the failing test**

Añadir `ROSTERS_FILE` a la importación, `from football_catalog import load_catalog` junto a la importación de `normalize_name`, y:

```python
class RealRostersTest(unittest.TestCase):
    def test_every_american_league_has_a_valid_roster_up_to_2026(self):
        competitions = load_catalog()["competitions"]
        rosters = load_json(ROSTERS_FILE, {})
        self.assertEqual(roster_errors(rosters, competitions), [])
        american = {c["id"] for c in competitions
                    if c["type"] == "league" and c["continent"] in ("south-america", "north-america")}
        self.assertEqual(set(rosters), american)
        for league, seasons in rosters.items():
            self.assertGreaterEqual(max(seasons), "2026", league)
            self.assertLessEqual(min(seasons), "2022-23" if len(min(seasons)) == 7 else "2022", league)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_football_clubs.RealRostersTest -v`
Expected: FAIL: `Items in the second set but not the first` con los 16 ids.

- [ ] **Step 3: Collect the rosters from Wikipedia**

Para cada liga y temporada, abrir el artículo de la temporada en en.wikipedia.org (p. ej. "2026 Campeonato Brasileiro Série A", "2026–27 Liga MX season", "2026 Major League Soccer season") y copiar los equipos de la sección "Teams" (tabla de estadios/ubicaciones o "Stadia and locations"). Si no existe el artículo en inglés, usar el de es.wikipedia (o pt.wikipedia para Brasil) y escribir el nombre como lo escribe en.wikipedia en el artículo del club.

Temporadas:

| Ligas | Temporadas |
|---|---|
| brasileirao-serie-a, liga-profesional-argentina, uruguayan-primera-division, colombian-primera-a, chilean-primera-division, paraguayan-primera-division, peruvian-liga-1, ecuadorian-serie-a, bolivian-primera-division, venezuelan-primera-division, mls, canadian-premier-league, panamanian-football-league | 2022, 2023, 2024, 2025, 2026 |
| liga-mx, costa-rican-primera-division, guatemalan-liga-nacional | 2022-23, 2023-24, 2024-25, 2025-26, 2026-27 |

Reglas:
- Nombre de un club = título de su artículo en en.wikipedia sin el paréntesis de desambiguación ("Club Nacional de Football", "Liverpool F.C. (Montevideo)" → "Liverpool F.C."). El mismo club se escribe igual en todas las temporadas salvo que cambiara de nombre oficialmente (esos cambios los une la Task 6).
- Apertura + Clausura: unión de los equipos de ambos torneos.
- El número de clubes de cada temporada coincide con el que indica el artículo (p. ej. Brasileirão 20, Liga MX 18, MLS 2026 30). Anotar cualquier discrepancia como Ruling.
- Orden de las listas: alfabético.

Formato:

```json
{
  "bolivian-primera-division": {
    "2022": ["Always Ready", "..."],
    "2026": ["..."]
  },
  "...": {}
}
```

Claves de primer nivel en orden alfabético; escribir con `json.dumps(data, ensure_ascii=False, indent=2) + "\n"`.

- [ ] **Step 4: Run tests and validation**

Run: `python -m unittest discover -s tests` y `python scripts/validate_assets.py`
Expected: `OK` (102 tests); `Validation passed.`

- [ ] **Step 5: Commit**

```bash
git add data/football/rosters.json tests/test_football_clubs.py
git commit -m "Add club rosters of 16 American leagues since 2022"
```

---

### Task 6: Emparejar clubes y revisar escudos

**Files:**
- Modify: `data/football/clubs-mapping.json`

**Interfaces:**
- Consumes: `sync_clubs.py plan|accept` (Task 4), `rosters.json` (Task 5).
- Produces: una correspondencia por clave de `rosters.json`, con `source` `football-logos` (slug verificado) o `url` (URL https de PNG de Wikimedia).

- [ ] **Step 1: Propose**

Run: `python scripts/sync_clubs.py plan`
Expected: `<N> unmapped club(s): {...}` con N igual al número de claves de `roster_index` (entre 400 y 600); hojas `.cache/clubs/review-<país>.jpg` para los 16 países.

- [ ] **Step 2: Review each country and accept**

Para cada país: abrir su hoja, anotar las propuestas erróneas (escudo de otro club, `none`, slug de otra categoría o del equipo femenino), ejecutar `python scripts/sync_clubs.py accept <País>` y corregir en `clubs-mapping.json` las anotadas:

- Slug erróneo: buscar el correcto en `https://football-logos.cc/<país>/` y cambiar `slug` (y `id` si el id derivado era el del club equivocado).
- Sin escudo en football-logos.cc o escudo opaco: `"source": "url"`, `"slug": null`, `"url": "<URL thumb PNG de 3840 px de la API imageinfo de Wikimedia Commons, o el PNG original si es más pequeño>"`. Nunca una URL `.svg` sin thumb (Pillow no la abre).
- Mismo club con dos nombres (renombrado, o grafías distintas entre temporadas): mismo `id` en ambas claves.
- Id con errata heredada del slug (p. ej. `argeninos-juniors`): corregir el `id` (`argentinos-juniors`), manteniendo el `slug`.

- [ ] **Step 3: Verify the mapping**

Generar una hoja de verificación por país a partir de `clubs-mapping.json` (nombre de la plantilla → id, junto al escudo que se descargará: slug de football-logos.cc o `url`) con un script de un solo uso en `.cache/`, y revisarla. Repetir el Step 2 hasta que todas las filas sean correctas.

Run: `python scripts/sync_clubs.py plan`
Expected: `0 unmapped club(s)`.

- [ ] **Step 4: Commit**

```bash
git add data/football/clubs-mapping.json
git commit -m "Map clubs of the American leagues"
```

---

### Task 7: Descargar escudos, tests del catálogo real y documentación

**Files:**
- Modify: `data/football/clubs.json`, `data/football/clubs-lookup.json`, `data/sources.json`, `data/all-assets.json`, `README.md`
- Create: `football/clubs/<br|ar|uy|co|cl|py|pe|ec|bo|ve|mx|us|ca|cr|gt|pa>/*.png`
- Test: `tests/test_football_clubs.py`

**Interfaces:**
- Consumes: todo lo anterior.

- [ ] **Step 1: Write the failing test**

Añadir a `RealClubsCatalogTest`:

```python
    def test_american_clubs_resolve(self):
        self.assertEqual(self.find("BR", "Flamengo"), "flamengo")
        self.assertEqual(self.find("AR", "Boca Juniors"), "boca-juniors")
        self.assertEqual(self.find("US", "Toronto FC"), "toronto-fc")
        self.assertEqual(self.find("MX", "Club América"), "america")
        self.assertIsNone(self.find("CA", "Toronto FC"))
```

Si los ids de la Task 6 difieren (p. ej. `club-america`), ajustar los valores esperados a esos ids antes de ejecutar.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_football_clubs.RealClubsCatalogTest -v`
Expected: FAIL en `test_american_clubs_resolve` (`None != 'flamengo'`).

- [ ] **Step 3: Apply**

Run: `python scripts/sync_clubs.py apply`
Expected: `<572+N'> club(s) in catalog, 0 without logo`. Si hay `WARNING: <id>: ...`, corregir su correspondencia (Task 6, Step 2), borrar el PNG si se creó y repetir.

Revisar la hoja de contacto de los escudos descargados de cada país (fondo gris) para detectar fondos opacos residuales o recortes incorrectos.

- [ ] **Step 4: Verify idempotence, tests and validation**

Run: `python scripts/sync_clubs.py apply` y `git status --short data football`
Expected: mismo recuento y ningún cambio nuevo respecto al Step 3.

Run: `python -m unittest discover -s tests` y `python scripts/validate_assets.py`
Expected: `OK` (103 tests); `Validation passed.` (los avisos solo de baja resolución).

- [ ] **Step 5: Document**

En `README.md`, sección "Clubes de fútbol":
- Fuentes: las 25 ligas europeas vienen de luukhopman; las 16 de América de `data/football/rosters.json`, mantenido a mano desde Wikipedia.
- Los clubes de la MLS con sede en Canadá tienen país `US`.
- "Actualizar cada temporada": para América, añadir la temporada nueva de cada liga a `rosters.json` (nombres de la Wikipedia en inglés, `AAAA` o `AAAA-AA` según la liga) y ejecutar `plan` → revisar hojas → `accept` → `apply`; los escudos sin versión en football-logos.cc se indican con `"source": "url"` en `clubs-mapping.json`.

- [ ] **Step 6: Commit**

```bash
git add tests/test_football_clubs.py README.md data/football/clubs.json data/football/clubs-lookup.json data/sources.json data/all-assets.json football/clubs/br football/clubs/ar football/clubs/uy football/clubs/co football/clubs/cl football/clubs/py football/clubs/pe football/clubs/ec football/clubs/bo football/clubs/ve football/clubs/mx football/clubs/us football/clubs/ca football/clubs/cr football/clubs/gt football/clubs/pa
git commit -m "Add crests for clubs of the American leagues"
```
