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
