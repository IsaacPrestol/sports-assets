"""Country and region flags: catalog, validation, lookup and assets.

`data/flags.json` is the source of truth. Ids are lowercase ISO codes
(`es`, `gb-eng`, `es-pv`), so a club's `country` maps to its flag directly.
Flags are opaque rectangles, so unlike logos they don't need transparent pixels.
"""
import json
from pathlib import Path
import re

from PIL import Image

from football_catalog import ID_RE, ROOT, build_lookup

FLAGS_FILE = ROOT / "data" / "flags.json"
FLAGS_LOOKUP_FILE = ROOT / "data" / "flags-lookup.json"
FLAGS_DIR = "flags"
MAX_SIDE = 1024
CODE_RE = re.compile(r"^[A-Z]{2}(?:-[A-Z0-9]{1,3})?$")
TYPES = {"country", "subdivision"}
REQUIRED = ("id", "code", "name", "aliases", "type", "parent", "flag")


def load_flags(root: Path = ROOT) -> dict:
    return json.loads((root / "data" / "flags.json").read_text(encoding="utf-8"))


def flag_path(flag_id: str) -> str:
    return f"{FLAGS_DIR}/{flag_id}.png"


def normalize_flag(src: Path, dst: Path, max_side: int = MAX_SIDE) -> tuple[int, int]:
    """Trim fully transparent margins (if any) and cap the longest side. Opaque flags are fine."""
    with Image.open(src) as image:
        rgba = image.convert("RGBA")
    bbox = rgba.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"{src} is fully transparent")
    flag = rgba.crop(bbox)
    flag.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    flag.save(dst, "PNG", optimize=True)
    return flag.size


def flag_assets(flags: list[dict]) -> dict[str, dict]:
    return {f["id"]: {"name": f["name"], "path": f["flag"]} for f in flags if f["flag"]}


def validate_flags(root: Path, catalog, *, check_images: bool = True) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(catalog, dict) or not isinstance(catalog.get("flags"), list):
        return ["Flags catalog must contain a 'flags' list"], warnings
    if catalog.get("version") != 1:
        errors.append("Unsupported flags catalog version")
    flags = catalog["flags"]
    for entry in flags:
        if not isinstance(entry, dict) or any(field not in entry for field in REQUIRED):
            errors.append(f"Flag entry is missing required fields: {entry!r}")
            continue
        label = entry["id"]
        if not isinstance(label, str) or not ID_RE.fullmatch(label):
            errors.append(f"Invalid flag id: {label!r}")
            continue
        if not isinstance(entry["code"], str) or not CODE_RE.fullmatch(entry["code"]):
            errors.append(f"Flag '{label}' has invalid code {entry['code']!r}")
        elif entry["code"].lower() != label:
            errors.append(f"Flag '{label}' id must be its code in lowercase")
        if not isinstance(entry["name"], str) or not entry["name"].strip():
            errors.append(f"Flag '{label}' has invalid name")
        aliases = entry["aliases"]
        if not isinstance(aliases, list) or not all(isinstance(a, str) and a.strip() for a in aliases):
            errors.append(f"Flag '{label}' has invalid aliases")
        if entry["type"] not in TYPES:
            errors.append(f"Flag '{label}' has invalid type {entry['type']!r}")
        if entry["flag"] is not None and entry["flag"] != flag_path(label):
            errors.append(f"Flag '{label}' image must be '{flag_path(label)}'")
    if errors:
        return errors, warnings

    by_id: dict[str, dict] = {}
    for entry in flags:
        if entry["id"] in by_id:
            errors.append(f"Duplicate flag id: {entry['id']}")
        by_id[entry["id"]] = entry
    for entry in flags:
        label, parent = entry["id"], entry["parent"]
        if entry["type"] == "country":
            if parent is not None:
                errors.append(f"Country flag '{label}' must not have a parent")
        elif parent not in by_id or by_id[parent]["type"] != "country":
            errors.append(f"Subdivision flag '{label}' has unknown parent {parent!r}")
        elif not entry["code"].startswith(by_id[parent]["code"] + "-"):
            errors.append(f"Subdivision flag '{label}' code must start with its parent's code")

    referenced = set()
    for entry in flags:
        relative = entry["flag"]
        if relative is None:
            warnings.append(f"Flag '{entry['id']}' has no image yet")
            continue
        referenced.add(relative)
        if not check_images:
            continue
        path = root / relative
        if not path.is_file():
            errors.append(f"Flag image not found: {relative}")
            continue
        try:
            with Image.open(path) as image:
                if image.format != "PNG":
                    errors.append(f"Flag image is not PNG: {relative}")
                if max(image.size) > MAX_SIDE:
                    errors.append(f"Flag image exceeds {MAX_SIDE} px: {relative}")
                if image.convert("RGBA").getchannel("A").getbbox() is None:
                    errors.append(f"Flag image is fully transparent: {relative}")
        except OSError:
            errors.append(f"Cannot decode flag image: {relative}")
    folder = root / FLAGS_DIR
    if folder.exists():
        for path in sorted(folder.rglob("*")):
            if path.is_file() and not path.name.startswith("."):
                relative = path.relative_to(root).as_posix()
                if relative not in referenced:
                    errors.append(f"Flag image not referenced: {relative}")
    errors.extend(build_lookup(flags)[1])
    return errors, warnings


def missing_country_flags(flags: list[dict], countries) -> list[str]:
    """Country codes used by other catalogs that have no flag entry."""
    known = {entry["code"] for entry in flags}
    return sorted({c for c in countries if c and c not in known})
