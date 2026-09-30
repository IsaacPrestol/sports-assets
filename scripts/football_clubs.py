"""Football clubs catalog helpers and the luukhopman/football-logos sync logic."""

import difflib
import re

from football_catalog import ROOT, normalize_name

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
