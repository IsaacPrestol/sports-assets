"""Shared helpers for the football competitions catalog."""

from pathlib import Path
import json
import re
import unicodedata

from PIL import Image

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
