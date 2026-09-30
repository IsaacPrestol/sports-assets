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
