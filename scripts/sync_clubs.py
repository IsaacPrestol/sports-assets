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
