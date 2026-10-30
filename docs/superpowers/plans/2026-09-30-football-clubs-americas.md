# Americas club crests — Implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the top-division clubs of 16 CONMEBOL and CONCACAF leagues (current season and since 2022) to the club catalog, with transparent crests and the same `plan/accept/apply` flow.

**Architecture:** A hand-maintained roster file (`data/football/rosters.json`) is turned by `roster_index` into entries with the same shape as luukhopman's; `sync_clubs.py` combines both indexes, so proposal, visual review, merging and validation don't change. Mappings accept `"source": "url"` for crests that aren't on football-logos.cc.

**Tech Stack:** Python 3.12, Pillow, `unittest` (stdlib), `urllib`.

**Spec:** `docs/superpowers/specs/2026-09-30-football-clubs-americas-design.md`

## Global Constraints

- Tests: `python -m unittest discover -s tests -v` (no pytest). Tests import from `scripts/` via `sys.path`.
- Logos: PNG with transparent pixels, trimmed, longest side ≤ 1024 px, never upscaled (`scripts/normalize_logo.py`).
- A club's country = its league's `country` in `competitions.json`. Canadian MLS clubs get `US`.
- Seasons: `YYYY` (calendar year) or `YYYY-YY` (spanning two years), a single form per league. From 2022 / 2022-23 up to the current one.
- Leagues with `YYYY-YY` seasons: `liga-mx`, `costa-rican-primera-division`, `guatemalan-liga-nacional`. The rest use `YYYY`.
- Club names in `rosters.json`: as they appear on English Wikipedia.
- No competition alias may be one of `RealCatalogTest.GENERIC_ALIASES`.
- JSON written with `ensure_ascii=False, indent=2` and a trailing newline (like `write_json` in `sync_clubs.py`).
- Commits with the repo's local identity; messages ending in `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Don't push or merge.
- `football/clubs/tr/fenerbahce.png` has a local change by the user: don't `git add` that file, and don't `git add -A`.

## Review Focus

1. A club that changes name between seasons (e.g. "York United" → "Inter Toronto FC") appears as two keys; both must map to the same id, with the old name kept as an alias. Test: `RosterIndexTest.test_renamed_club_is_one_club`.
2. An accepted mapping with `"source": "url"` but no URL filled in must not reach CI silently: `validate_clubs` rejects it. Test: `ValidateClubsTest.test_url_source_needs_https_url`.
3. Mixed season formats in one league would make the wrong season the "current" one. Test: `RosterErrorsTest.test_season_format`.
4. A name repeated in a season with a different spelling ("Club Nacional" / "club nacional") would produce two keys for the same club. Test: `RosterErrorsTest.test_club_names`.
5. Running `apply` again with no changes must not modify anything (clean `git status`). Explicit step in Task 7.

---

### Task 1: Twelve new leagues in the competition catalog

**Files:**
- Modify: `data/football/competitions.json`, `data/sources.json`, `data/football/competitions-lookup.json` (regenerado), `data/all-assets.json` (regenerado)
- Create: 12 PNGs in `football/competitions/south-america/` and `football/competitions/north-america/`
- Test: `tests/test_football_catalog.py`

**Interfaces:**
- Produces: `league` competitions with these ids and countries, used by `rosters.json` (Task 5):

| id | name | aliases | continent / confederation | country | football-logos.cc slug |
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

All with `"type": "league"`, `"scope": "club"`, `"collage": null`, `"logo": "football/competitions/<continent>/<id>.png"`.

- [ ] **Step 1: Write the failing test**

Add to `RealCatalogTest` in `tests/test_football_catalog.py`:

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
Expected: FAIL in `test_american_leagues_have_country_and_logo` with `uruguayan-primera-division` (`None` is not not None).

- [ ] **Step 3: Download and normalize the 12 logos**

For each row of the table, get the 1500 px URL from the country page and normalize it. One-off script (in `.cache/`, not committed):

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
Expected: 12 lines `<id> https://assets.football-logos.cc/...png`, no exceptions.

Review the 12 PNGs visually (contact sheet on a grey background). If any is opaque, has a watermark or isn't the league's logo, replace it with the Wikimedia PNG (3840 px `thumb` URL from the `imageinfo` API) and record the decision as a Ruling.

- [ ] **Step 4: Add catalog entries and sources**

Add the 12 table entries to `data/football/competitions.json` (after the others of their continent) and one entry per logo to `data/sources.json`:

```json
"football/competitions/south-america/uruguayan-primera-division.png": {
  "license": null,
  "notes": "Via github.com/Leo4815162342/football-logos (football-logos.cc)",
  "retrieved": "2026-09-30",
  "url": "<URL impresa en el Step 3>"
}
```

Then: `python scripts/build_index.py`
Expected: finishes without errors. If it reports an alias collision (e.g. `LPF Panamá` or `Liga 1 Perú` with another competition), remove that alias from the new league and record it as a Ruling.

- [ ] **Step 5: Run tests and validation**

Run: `python -m unittest discover -s tests` and `python scripts/validate_assets.py`
Expected: `OK`; `Validation passed.`

- [ ] **Step 6: Commit**

```bash
git add tests/test_football_catalog.py data/football/competitions.json data/football/competitions-lookup.json data/sources.json data/all-assets.json football/competitions/south-america football/competitions/north-america
git commit -m "Add the 12 remaining American leagues to the competitions catalog"
```

---

### Task 2: Roster index and league in index entries

**Files:**
- Modify: `scripts/football_clubs.py`
- Test: `tests/test_football_clubs.py`

**Interfaces:**
- Consumes: league ids from Task 1 (only as sample data in the tests).
- Produces:
  - `ROSTERS_FILE = ROOT / "data" / "football" / "rosters.json"`
  - `COUNTRY_CODES` with 16 new countries; `FL_COUNTRIES` includes them (derived), with `"United States": "usa"`.
  - Index entries (from `luuk_index` and `roster_index`) with the keys `country_folder`, `name`, `league_folder`, `league`, `latest_season`, `latest_path`. `league` is a competition id or `None`.
  - `roster_index(rosters: dict, competitions: list[dict]) -> dict[str, dict]`, key `"<country_folder>|<name>"`, `league_folder` always `None`, `latest_path` always `None`.
  - `propose(...)` returns `"source": "url"` when there's no slug and the entry has no `latest_path`.
  - `merge_clubs` takes the current league from the entries' `league` field.

- [ ] **Step 1: Write the failing tests**

In `tests/test_football_clubs.py`, add `roster_index` to the `football_clubs` import, and add this test to `LuukIndexTest`:

```python
    def test_entries_carry_league_id(self):
        index = luuk_index(PATHS)
        self.assertEqual(index["Spain|Real Madrid"]["league"], "laliga")
        self.assertIsNone(index["Spain|UD Almería"]["league"])
```

and this class after `SyncSafetyTest`:

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
Expected: ERROR on import: `ImportError: cannot import name 'roster_index'`.

- [ ] **Step 3: Implement**

In `scripts/football_clubs.py`:

1. Below `MAPPING_FILE`:

```python
ROSTERS_FILE = ROOT / "data" / "football" / "rosters.json"
```

2. In `COUNTRY_CODES`, add (keeping alphabetical order):

```python
    "Argentina": "AR", "Bolivia": "BO", "Brazil": "BR", "Canada": "CA", "Chile": "CL",
    "Colombia": "CO", "Costa Rica": "CR", "Ecuador": "EC", "Guatemala": "GT",
    "Mexico": "MX", "Panama": "PA", "Paraguay": "PY", "Peru": "PE",
    "United States": "US", "Uruguay": "UY", "Venezuela": "VE",
```

and in `FL_COUNTRIES`: `} | {"Türkiye": "turkey", "United States": "usa"}`.

3. In `luuk_index`, add `"league": None,` to the dictionary created with `setdefault` (after `"league_folder": None,`) and replace

```python
        if season == CURRENT_SEASON:
            club["league_folder"] = league_folder
```

with

```python
        if season == CURRENT_SEASON:
            club["league_folder"] = league_folder
            club["league"] = LEAGUE_IDS.get(league_folder)
```

4. After `luuk_index`:

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

5. In `propose`, replace `"source": "football-logos" if slug else "luukhopman",` with `"source": source,` and before `proposals[key] = {` add:

```python
        if slug:
            source = "football-logos"
        elif club["latest_path"]:
            source = "luukhopman"
        else:
            source = "url"
```

6. In `merge_clubs`, replace

```python
        current = [entry for entry in entries if entry["league_folder"]]
        league = LEAGUE_IDS[current[0]["league_folder"]] if current else None
```

with

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

### Task 3: Roster validation and URL mappings

**Files:**
- Modify: `scripts/football_clubs.py`, `scripts/validate_assets.py`
- Test: `tests/test_football_clubs.py`

**Interfaces:**
- Consumes: `ROSTERS_FILE`, `COUNTRY_CODES` (Task 2); fixtures `ROSTERS`, `COMPETITIONS` (Task 2).
- Produces:
  - `SEASON_RE = re.compile(r"^\d{4}(?:-\d{2})?$")`
  - `roster_errors(rosters, competitions: list[dict]) -> list[str]`: empty list if valid.
  - `validate_clubs` rejects mappings with `"source": "url"` without a `url` starting with `https://`.
  - `validate_assets.check_rosters(errors, warnings)`.

- [ ] **Step 1: Write the failing tests**

Add `roster_errors` to the import and these tests:

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

and in `ValidateClubsTest`:

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

In `scripts/football_clubs.py`, next to the constants:

```python
SEASON_RE = re.compile(r"^\d{4}(?:-\d{2})?$")
```

and after `roster_index`:

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

In `validate_clubs`, replace the final mappings loop with:

```python
    for key in sorted(mapping):
        entry = mapping[key]
        if entry["id"] not in known:
            errors.append(f"Mapping '{key}' points to unknown club '{entry['id']}'")
        url = entry.get("url")
        if entry.get("source") == "url" and not (isinstance(url, str) and url.startswith("https://")):
            errors.append(f"Mapping '{key}' uses source 'url' without an https url")
```

In `scripts/validate_assets.py`, extend the import to
`from football_clubs import CLUBS_FILE, MAPPING_FILE, ROSTERS_FILE, load_json, roster_errors, validate_clubs`, add:

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

and call `check_rosters(errors, warnings)` in `main()` after `check_clubs`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest discover -s tests` and `python scripts/validate_assets.py`
Expected: `OK` (101 tests); `Validation passed.`

- [ ] **Step 5: Commit**

```bash
git add scripts/football_clubs.py scripts/validate_assets.py tests/test_football_clubs.py
git commit -m "Validate club rosters and manual crest URLs"
```

---

### Task 4: `sync_clubs.py` processes the rosters

**Files:**
- Modify: `scripts/sync_clubs.py`

**Interfaces:**
- Consumes: `ROSTERS_FILE`, `roster_index`, `roster_errors` (Tasks 2–3); `load_catalog` from `football_catalog`.
- Produces: `load_index() -> dict` (luukhopman + rosters); `apply` downloads `mapping[key]["url"]` for `"source": "url"`.

- [ ] **Step 1: Wire the combined index**

1. Docstring: first sources line → `Rosters from github.com/luukhopman/football-logos (Europe) and data/football/rosters.json (Americas),` and the fallback line → `images from football-logos.cc (github.com/Leo4815162342/football-logos); luukhopman's 139x181 PNG or a manual url as fallback.`
2. Imports: `from football_catalog import ROOT, load_catalog` and add `ROSTERS_FILE, roster_errors, roster_index` to the `football_clubs` import.
3. After `check_folders`:

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

4. In `plan()` and in `apply()`, replace the two lines `luuk = load_luuk()` / `check_folders(luuk)` with `luuk = load_index()`.
5. In `plan()`, replace the `luuk_path` line with:

```python
        latest_path = luuk[key]["latest_path"]
        luuk_path = cached(luuk_url(latest_path), CACHE / "luuk" / latest_path) if latest_path else None
```

6. In `apply()`, replace the block from `slug = next(...)` to `normalize_logo(raw, destination)` with:

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

7. `accept` help: `help="country folder, e.g. Spain or Brazil"`.

- [ ] **Step 2: Verify no regression on Europe**

Run: `python scripts/sync_clubs.py plan`
Expected: `0 unmapped club(s): {'exact': 0, 'partial': 0, 'fuzzy': 0, 'none': 0}` (`rosters.json` doesn't exist yet).

Run: `python scripts/sync_clubs.py apply` and `git status --short`
Expected: `572 club(s) in catalog, 0 without logo`; `git status` only shows `football/clubs/tr/fenerbahce.png` (the user's change) and `scripts/sync_clubs.py`.

- [ ] **Step 3: Run tests**

Run: `python -m unittest discover -s tests`
Expected: `OK` (101 tests).

- [ ] **Step 4: Commit**

```bash
git add scripts/sync_clubs.py
git commit -m "Sync clubs from hand-maintained rosters and manual crest urls"
```

---

### Task 5: `rosters.json` with the 16 leagues

**Files:**
- Create: `data/football/rosters.json`
- Test: `tests/test_football_clubs.py`

**Interfaces:**
- Consumes: ids from Task 1; `roster_errors`, `ROSTERS_FILE` (Tasks 2–3).
- Produces: rosters for every `south-america` or `north-america` `continent` league with `type: league`.

- [ ] **Step 1: Write the failing test**

Add `ROSTERS_FILE` to the import, `from football_catalog import load_catalog` next to the `normalize_name` import, and:

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
Expected: FAIL: `Items in the second set but not the first` with the 16 ids.

- [ ] **Step 3: Collect the rosters from Wikipedia**

For each league and season, open the season article on en.wikipedia.org (e.g. "2026 Campeonato Brasileiro Série A", "2026–27 Liga MX season", "2026 Major League Soccer season") and copy the teams from the "Teams" section (stadiums/locations table or "Stadia and locations"). If there's no English article, use the es.wikipedia one (or pt.wikipedia for Brazil) and write the name as en.wikipedia writes it in the club's article.

Seasons:

| Leagues | Seasons |
|---|---|
| brasileirao-serie-a, liga-profesional-argentina, uruguayan-primera-division, colombian-primera-a, chilean-primera-division, paraguayan-primera-division, peruvian-liga-1, ecuadorian-serie-a, bolivian-primera-division, venezuelan-primera-division, mls, canadian-premier-league, panamanian-football-league | 2022, 2023, 2024, 2025, 2026 |
| liga-mx, costa-rican-primera-division, guatemalan-liga-nacional | 2022-23, 2023-24, 2024-25, 2025-26, 2026-27 |

Rules:
- A club's name = the title of its en.wikipedia article without the disambiguation parenthesis ("Club Nacional de Football", "Liverpool F.C. (Montevideo)" → "Liverpool F.C."). The same club is spelled the same way in every season unless it officially changed its name (Task 6 joins those changes).
- Apertura + Clausura: union of the teams of both tournaments.
- The number of clubs in each season matches the article (e.g. Brasileirão 20, Liga MX 18, MLS 2026 30). Record any discrepancy as a Ruling.
- List order: alphabetical.

Format:

```json
{
  "bolivian-primera-division": {
    "2022": ["Always Ready", "..."],
    "2026": ["..."]
  },
  "...": {}
}
```

Top-level keys in alphabetical order; write with `json.dumps(data, ensure_ascii=False, indent=2) + "\n"`.

- [ ] **Step 4: Run tests and validation**

Run: `python -m unittest discover -s tests` and `python scripts/validate_assets.py`
Expected: `OK` (102 tests); `Validation passed.`

- [ ] **Step 5: Commit**

```bash
git add data/football/rosters.json tests/test_football_clubs.py
git commit -m "Add club rosters of 16 American leagues since 2022"
```

---

### Task 6: Match clubs and review crests

**Files:**
- Modify: `data/football/clubs-mapping.json`

**Interfaces:**
- Consumes: `sync_clubs.py plan|accept` (Task 4), `rosters.json` (Task 5).
- Produces: one mapping per `rosters.json` key, with `source` `football-logos` (verified slug) or `url` (https URL of a Wikimedia PNG).

- [ ] **Step 1: Propose**

Run: `python scripts/sync_clubs.py plan`
Expected: `<N> unmapped club(s): {...}` with N equal to the number of `roster_index` keys (between 400 and 600); sheets `.cache/clubs/review-<country>.jpg` for the 16 countries.

- [ ] **Step 2: Review each country and accept**

For each country: open its sheet, note the wrong proposals (another club's crest, `none`, a slug from another division or of the women's team), run `python scripts/sync_clubs.py accept <Country>` and fix the noted ones in `clubs-mapping.json`:

- Wrong slug: find the right one at `https://football-logos.cc/<country>/` and change `slug` (and `id` if the derived id was the wrong club's).
- No crest on football-logos.cc, or an opaque crest: `"source": "url"`, `"slug": null`, `"url": "<3840 px PNG thumb URL from the Wikimedia Commons imageinfo API, or the original PNG if smaller>"`. Never an `.svg` URL without a thumb (Pillow can't open it).
- Same club under two names (renamed, or spelled differently between seasons): the same `id` on both keys.
- Id with a typo inherited from the slug (e.g. `argeninos-juniors`): fix the `id` (`argentinos-juniors`), keeping the `slug`.

- [ ] **Step 3: Verify the mapping**

Generate a verification sheet per country from `clubs-mapping.json` (roster name → id, next to the crest that will be downloaded: football-logos.cc slug or `url`) with a one-off script in `.cache/`, and review it. Repeat Step 2 until every row is correct.

Run: `python scripts/sync_clubs.py plan`
Expected: `0 unmapped club(s)`.

- [ ] **Step 4: Commit**

```bash
git add data/football/clubs-mapping.json
git commit -m "Map clubs of the American leagues"
```

---

### Task 7: Download crests, real-catalog tests and documentation

**Files:**
- Modify: `data/football/clubs.json`, `data/football/clubs-lookup.json`, `data/sources.json`, `data/all-assets.json`, `README.md`
- Create: `football/clubs/<br|ar|uy|co|cl|py|pe|ec|bo|ve|mx|us|ca|cr|gt|pa>/*.png`
- Test: `tests/test_football_clubs.py`

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Write the failing test**

Add to `RealClubsCatalogTest`:

```python
    def test_american_clubs_resolve(self):
        self.assertEqual(self.find("BR", "Flamengo"), "flamengo")
        self.assertEqual(self.find("AR", "Boca Juniors"), "boca-juniors")
        self.assertEqual(self.find("US", "Toronto FC"), "toronto-fc")
        self.assertEqual(self.find("MX", "Club América"), "america")
        self.assertIsNone(self.find("CA", "Toronto FC"))
```

If the ids from Task 6 differ (e.g. `club-america`), adjust the expected values to those ids before running.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_football_clubs.RealClubsCatalogTest -v`
Expected: FAIL in `test_american_clubs_resolve` (`None != 'flamengo'`).

- [ ] **Step 3: Apply**

Run: `python scripts/sync_clubs.py apply`
Expected: `<572+N'> club(s) in catalog, 0 without logo`. If there's a `WARNING: <id>: ...`, fix its mapping (Task 6, Step 2), delete the PNG if it was created and repeat.

Review the contact sheet of each country's downloaded crests (grey background) to spot leftover opaque backgrounds or wrong trimming.

- [ ] **Step 4: Verify idempotence, tests and validation**

Run: `python scripts/sync_clubs.py apply` and `git status --short data football`
Expected: same count and no new changes compared with Step 3.

Run: `python -m unittest discover -s tests` and `python scripts/validate_assets.py`
Expected: `OK` (103 tests); `Validation passed.` (low-resolution warnings only).

- [ ] **Step 5: Document**

In `README.md`, "Football clubs" section:
- Sources: the 25 European leagues come from luukhopman; the 16 Americas leagues from `data/football/rosters.json`, maintained by hand from Wikipedia.
- MLS clubs based in Canada have country `US`.
- "Update every season": for the Americas, add each league's new season to `rosters.json` (names from English Wikipedia, `YYYY` or `YYYY-YY` depending on the league) and run `plan` → review sheets → `accept` → `apply`; crests with no football-logos.cc version are marked with `"source": "url"` in `clubs-mapping.json`.

- [ ] **Step 6: Commit**

```bash
git add tests/test_football_clubs.py README.md data/football/clubs.json data/football/clubs-lookup.json data/sources.json data/all-assets.json football/clubs/br football/clubs/ar football/clubs/uy football/clubs/co football/clubs/cl football/clubs/py football/clubs/pe football/clubs/ec football/clubs/bo football/clubs/ve football/clubs/mx football/clubs/us football/clubs/ca football/clubs/cr football/clubs/gt football/clubs/pa
git commit -m "Add crests for clubs of the American leagues"
```
