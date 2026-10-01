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
ROSTERS_FILE = ROOT / "data" / "football" / "rosters.json"
CLUBS_DIR = "football/clubs"
COUNTRY_RE = re.compile(r"^[A-Z]{2}(?:-[A-Z]{3})?$")
LOW_RES_SIDE = 400
SEASON_RE = re.compile(r"^\d{4}(?:-\d{2})?$")
REQUIRED_FIELDS = ("id", "name", "aliases", "country", "league", "logo")
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
    words = set(target.split())
    contained = [c for c in candidates if set(c.split()) <= words]
    if contained:
        return candidates[max(contained, key=lambda c: (len(c.split()), len(c)))], "partial"
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


CURRENT_SEASON = "~current"

COUNTRY_CODES = {
    "Austria": "AT", "Belgium": "BE", "Bulgaria": "BG", "Croatia": "HR",
    "Czech Republic": "CZ", "Denmark": "DK", "England": "GB-ENG", "France": "FR",
    "Germany": "DE", "Greece": "GR", "Hungary": "HU", "Israel": "IL", "Italy": "IT",
    "Netherlands": "NL", "Norway": "NO", "Poland": "PL", "Portugal": "PT",
    "Romania": "RO", "Russia": "RU", "Scotland": "GB-SCT", "Serbia": "RS",
    "Spain": "ES", "Sweden": "SE", "Switzerland": "CH", "Türkiye": "TR", "Ukraine": "UA",
    # Americas (data/football/rosters.json)
    "Argentina": "AR", "Bolivia": "BO", "Brazil": "BR", "Canada": "CA", "Chile": "CL",
    "Colombia": "CO", "Costa Rica": "CR", "Ecuador": "EC", "Guatemala": "GT",
    "Mexico": "MX", "Panama": "PA", "Paraguay": "PY", "Peru": "PE",
    "United States": "US", "Uruguay": "UY", "Venezuela": "VE",
}

FL_COUNTRIES = {
    folder: folder.lower().replace(" ", "-") for folder in COUNTRY_CODES
} | {"Türkiye": "turkey", "United States": "usa"}

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
            "league": None,
            "latest_season": "",
            "latest_path": "",
        })
        if season == CURRENT_SEASON:
            club["league_folder"] = league_folder
            club["league"] = LEAGUE_IDS.get(league_folder)
        if season > club["latest_season"]:
            club["latest_season"], club["latest_path"] = season, path
    return clubs


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
        if slug:
            source = "football-logos"
        elif club["latest_path"]:
            source = "luukhopman"
        else:
            source = "url"
        proposals[key] = {
            "id": club_id,
            "source": source,
            "slug": slug,
            "match": match,
        }
    return proposals


def _drop_colliding_aliases(by_id: dict[str, dict], added: dict[str, list[str]]) -> list[str]:
    """Drop the aliases listed in `added` that collide with another club of the same country."""
    owners: dict[tuple[str, str], str] = {}
    for club in by_id.values():
        fresh = {normalize_name(alias) for alias in added.get(club["id"], [])}
        names = [club["id"], club["name"], *(a for a in club["aliases"] if normalize_name(a) not in fresh)]
        for name in names:
            owners.setdefault((club["country"], normalize_name(name)), club["id"])
    skipped = []
    for club_id in sorted(added):
        club = by_id[club_id]
        fresh = set(added[club_id])
        kept = []
        for alias in club["aliases"]:
            if alias not in fresh:
                kept.append(alias)
                continue
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
    by_id = {club["id"]: dict(club, aliases=list(club["aliases"])) for club in existing}
    keys_by_id: dict[str, list[str]] = {}
    for key in sorted(mapping):
        keys_by_id.setdefault(mapping[key]["id"], []).append(key)

    added: dict[str, list[str]] = {}
    for club_id, keys in keys_by_id.items():
        entries = [luuk[key] for key in keys if key in luuk]
        if not entries:
            continue
        country = COUNTRY_CODES[entries[0]["country_folder"]]
        current = [entry for entry in entries if entry["league"]]
        league = current[0]["league"] if current else None
        logo = None if club_id in missing_logos else f"{CLUBS_DIR}/{country.lower()}/{club_id}.png"
        if club_id in by_id:
            club = by_id[club_id]
            club.update(league=league, logo=logo)
            known = {normalize_name(n) for n in [club["id"], club["name"], *club["aliases"]]}
            new_names = []
            for entry in entries:
                if normalize_name(entry["name"]) not in known:
                    known.add(normalize_name(entry["name"]))
                    new_names.append(entry["name"])
            if new_names:
                club["aliases"].extend(new_names)
                added[club_id] = new_names
            continue
        latest = max(entries, key=lambda entry: entry["latest_season"])
        slug = next((mapping[key]["slug"] for key in keys if mapping[key].get("slug")), None)
        aliases = auto_aliases(latest["name"], [entry["name"] for entry in entries], slug)
        by_id[club_id] = {
            "id": club_id,
            "name": latest["name"],
            "aliases": aliases,
            "country": country,
            "league": league,
            "logo": logo,
        }
        added[club_id] = list(aliases)

    skipped = _drop_colliding_aliases(by_id, added)
    clubs = sorted(by_id.values(), key=lambda club: (club["country"], club["id"]))
    return clubs, skipped


def finalize_clubs(existing: list[dict], mapping: dict, luuk: dict,
                   missing_logos: set[str] = frozenset()) -> tuple[list[dict], list[str], list[str]]:
    """Merge and check the per-country lookup, so callers can refuse to write a broken catalog."""
    clubs, skipped = merge_clubs(existing, mapping, luuk, missing_logos)
    return clubs, skipped, build_club_lookup(clubs)[1]


def unknown_folders(luuk: dict) -> list[str]:
    problems = set()
    for club in luuk.values():
        if club["country_folder"] not in COUNTRY_CODES:
            problems.add(f"Unknown luukhopman country folder: '{club['country_folder']}'")
        if club["league_folder"] and club["league_folder"] not in LEAGUE_IDS:
            problems.add(f"Unknown luukhopman league folder: '{club['league_folder']}'")
    return sorted(problems)


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
    ids = [club["id"] for club in clubs]
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
        entry = mapping[key]
        if entry["id"] not in known:
            errors.append(f"Mapping '{key}' points to unknown club '{entry['id']}'")
        url = entry.get("url")
        if entry.get("source") == "url" and not (isinstance(url, str) and url.startswith("https://")):
            errors.append(f"Mapping '{key}' uses source 'url' without an https url")
    return errors, warnings
