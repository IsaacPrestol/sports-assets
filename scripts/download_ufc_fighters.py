from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
FIGHTERS_DIR = ROOT / "ufc" / "fighters"
SEED_FILE = ROOT / "data" / "ufc-fighters-seed.json"
OVERRIDES_FILE = ROOT / "data" / "ufc-fighter-overrides.json"
SOURCES_FILE = ROOT / "data" / "sources.json"
BUILD_INDEX = ROOT / "scripts" / "build_index.py"

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "sports-assets/1.0 (+https://github.com/IsaacPrestol/sports-assets)"
ALLOWED_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

HEADSHOT_POSITIVE = {
    "headshot": 55,
    "portrait": 45,
    "cropped": 30,
    "profile": 25,
    "face": 20,
}

CONTEXT_PENALTIES = {
    "oval office": 100,
    "white house": 100,
    "kremlin": 100,
    "president": 80,
    "palace": 70,
    "award": 65,
    "ceremony": 65,
    "meeting": 55,
    "football players": 55,
    "young players": 55,
    "interview": 45,
    "press conference": 40,
    "weigh-in": 28,
    "weigh in": 28,
    "belt": 18,
    "octagon": 18,
    "fight night": 20,
    "poster": 80,
    "banner": 80,
    "logo": 100,
    "versus": 70,
    " vs ": 70,
    "ninot": 100,
    "statue": 100,
    "mural": 100,
}


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def clean_html(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def http_json(params: dict[str, str | int], retries: int = 3) -> dict:
    url = f"{COMMONS_API}?{urlencode(params)}"
    last_error = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=30) as response:
                return json.load(response)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Wikimedia API request failed: {last_error}")


def download_file(url: str, destination: Path, retries: int = 3) -> None:
    last_error = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=60) as response, destination.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 128)
                    if not chunk:
                        break
                    output.write(chunk)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            destination.unlink(missing_ok=True)
            if attempt + 1 < retries:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Image download failed: {last_error}")


def candidate_from_page(page: dict) -> dict | None:
    title = page.get("title", "")
    info_list = page.get("imageinfo") or []
    if not title or not info_list:
        return None

    info = info_list[0]
    mime = info.get("mime", "")
    if mime not in ALLOWED_MIME:
        return None

    ext = info.get("extmetadata", {})
    license_short = clean_html((ext.get("LicenseShortName") or {}).get("value"))
    if not license_short:
        return None

    return {
        "title": title,
        "pageid": page.get("pageid"),
        "mime": mime,
        "url": info.get("thumburl") or info.get("url"),
        "original_url": info.get("url"),
        "width": info.get("thumbwidth") or info.get("width"),
        "height": info.get("thumbheight") or info.get("height"),
        "extmetadata": ext,
    }


def fetch_exact_file(title: str) -> dict | None:
    data = http_json(
        {
            "action": "query",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|mime|extmetadata",
            "iiurlwidth": 1000,
            "format": "json",
            "formatversion": 2,
        }
    )
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None
    return candidate_from_page(pages[0])


def search_commons(name: str, limit: int = 18) -> list[dict]:
    queries = [
        f'"{name}" headshot',
        f'"{name}" portrait',
        f'"{name}" cropped',
        f'"{name}" UFC',
        f'"{name}"',
    ]
    seen: set[str] = set()
    candidates: list[dict] = []

    for search_term in queries:
        data = http_json(
            {
                "action": "query",
                "generator": "search",
                "gsrsearch": search_term,
                "gsrnamespace": 6,
                "gsrlimit": limit,
                "prop": "imageinfo",
                "iiprop": "url|mime|extmetadata",
                "iiurlwidth": 1000,
                "format": "json",
                "formatversion": 2,
            }
        )

        for page in data.get("query", {}).get("pages", []):
            candidate = candidate_from_page(page)
            if not candidate:
                continue
            title = candidate["title"]
            if title in seen:
                continue
            seen.add(title)
            candidates.append(candidate)

    return candidates


def normalized_file_stem(title: str) -> str:
    value = title.lower().replace("file:", "")
    value = re.sub(r"\.(jpg|jpeg|png|webp)$", "", value)
    return slugify(value).replace("-", " ")


def score_candidate(name: str, candidate: dict) -> float:
    title = candidate["title"].lower().replace("file:", "")
    normalized_name = slugify(name).replace("-", " ")
    stem = normalized_file_stem(candidate["title"])

    score = 0.0

    # Exact filenames are usually the cleanest portrait-style Commons image.
    if stem == normalized_name:
        score += 120
    elif stem in {f"{normalized_name} cropped", f"{normalized_name} crop"}:
        score += 135
    elif stem.startswith(normalized_name):
        score += 65
    elif normalized_name in stem:
        score += 45
    else:
        score -= 80

    for word, points in HEADSHOT_POSITIVE.items():
        if word in title:
            score += points

    for word, points in CONTEXT_PENALTIES.items():
        if word in title:
            score -= points

    # Photos naming another person alongside the fighter are usually contextual,
    # not a clean headshot.
    if " with " in title:
        score -= 45

    width = candidate.get("width") or 0
    height = candidate.get("height") or 0
    if width and height:
        ratio = width / height
        if 0.58 <= ratio <= 0.86:
            score += 20
        elif 0.45 <= ratio <= 1.00:
            score += 10
        elif ratio > 1.35:
            score -= 25
        if height >= 700:
            score += 4

    return score


def commons_page_url(title: str) -> str:
    title = title.replace(" ", "_")
    return "https://commons.wikimedia.org/wiki/" + quote(title, safe=":_()-,")


def metadata_record(name: str, candidate: dict, relative_path: str) -> dict:
    ext = candidate.get("extmetadata", {})

    def meta(key: str) -> str:
        return clean_html((ext.get(key) or {}).get("value"))

    return {
        "name": name,
        "path": relative_path,
        "source": "Wikimedia Commons",
        "commons_title": candidate.get("title", ""),
        "source_page": commons_page_url(candidate.get("title", "")),
        "download_url": candidate.get("url", ""),
        "original_url": candidate.get("original_url", ""),
        "author": meta("Artist"),
        "credit": meta("Credit"),
        "license": meta("LicenseShortName") or meta("UsageTerms"),
        "license_url": meta("LicenseUrl"),
        "attribution_required": meta("AttributionRequired"),
        "description": meta("ImageDescription"),
        "asset_type": "headshot",
    }


def load_json_dict(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def save_sources(sources: dict) -> None:
    SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    SOURCES_FILE.write_text(
        json.dumps(sources, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_seed() -> list[str]:
    if not SEED_FILE.exists():
        return []
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in {SEED_FILE}")
    return [str(item).strip() for item in data if str(item).strip()]


def existing_asset(slug: str) -> Path | None:
    for extension in ALLOWED_MIME.values():
        path = FIGHTERS_DIR / f"{slug}{extension}"
        if path.exists():
            return path
    return None


def remove_existing_assets(slug: str) -> None:
    for extension in ALLOWED_MIME.values():
        (FIGHTERS_DIR / f"{slug}{extension}").unlink(missing_ok=True)


def ranked_candidates(name: str, use_overrides: bool = True) -> tuple[list[dict], bool]:
    overrides = load_json_dict(OVERRIDES_FILE)
    if use_overrides and name in overrides:
        exact = fetch_exact_file(str(overrides[name]))
        if exact:
            exact["_override"] = True
            return [exact], True

    candidates = search_commons(name)
    candidates.sort(key=lambda item: score_candidate(name, item), reverse=True)
    return candidates, False


def process_fighter(
    name: str,
    sources: dict,
    force: bool,
    dry_run: bool,
    show_top: int,
    use_overrides: bool,
) -> tuple[bool, str]:
    slug = slugify(name)
    current = existing_asset(slug)
    if current and not force:
        return True, f"SKIP -> {name}: already exists as {current.name}"

    candidates, used_override = ranked_candidates(name, use_overrides=use_overrides)
    if not candidates:
        return False, f"MISS -> {name}: no reusable headshot candidate found"

    selected = candidates[0]
    selected_score = score_candidate(name, selected)

    if not used_override and selected_score < 50:
        return False, f"MISS -> {name}: best candidate is not headshot-like enough ({selected_score:.1f})"

    if dry_run:
        preview = []
        for index, candidate in enumerate(candidates[: max(1, show_top)], start=1):
            marker = "OVERRIDE " if candidate.get("_override") else ""
            preview.append(
                f"#{index} {marker}{candidate['title']} [{score_candidate(name, candidate):.1f}]"
            )
        return True, f"DRY -> {name}: " + " | ".join(preview)

    extension = ALLOWED_MIME[selected["mime"]]
    destination = FIGHTERS_DIR / f"{slug}{extension}"
    relative_path = destination.relative_to(ROOT).as_posix()

    if force:
        remove_existing_assets(slug)

    download_file(selected["url"], destination)
    sources[relative_path] = metadata_record(name, selected, relative_path)
    label = "OVERRIDE" if used_override else "AUTO"
    return True, f"OK -> {destination.name} <= {selected['title']} ({label})"


def build_indexes() -> None:
    subprocess.run([sys.executable, str(BUILD_INDEX)], check=True, cwd=ROOT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download reusable UFC fighter headshots from Wikimedia Commons and record attribution metadata."
    )
    parser.add_argument(
        "--fighter",
        action="append",
        dest="fighters",
        help="Process one fighter by name. Repeat for multiple fighters.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N seed fighters.")
    parser.add_argument("--force", action="store_true", help="Replace an existing fighter image.")
    parser.add_argument("--dry-run", action="store_true", help="Preview selections without downloading.")
    parser.add_argument(
        "--show-top",
        type=int,
        default=3,
        help="In dry-run mode, show the top N candidates. Default: 3.",
    )
    parser.add_argument(
        "--no-overrides",
        action="store_true",
        help="Ignore curated headshot overrides and use automatic ranking only.",
    )
    parser.add_argument("--no-index", action="store_true", help="Do not rebuild JSON indexes.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    FIGHTERS_DIR.mkdir(parents=True, exist_ok=True)

    fighters = args.fighters if args.fighters else load_seed()
    if args.limit is not None:
        fighters = fighters[: max(0, args.limit)]

    if not fighters:
        print("No fighters to process.")
        return 1

    sources = load_json_dict(SOURCES_FILE)
    success = 0
    missed = 0

    print(f"Processing {len(fighters)} UFC fighter(s) in HEADSHOT mode...")
    for index, name in enumerate(fighters, start=1):
        try:
            ok, message = process_fighter(
                name,
                sources,
                args.force,
                args.dry_run,
                args.show_top,
                not args.no_overrides,
            )
            print(f"[{index}/{len(fighters)}] {message}")
            if ok:
                success += 1
            else:
                missed += 1
        except Exception as exc:  # noqa: BLE001
            missed += 1
            print(f"[{index}/{len(fighters)}] ERROR -> {name}: {exc}")

        if index < len(fighters):
            time.sleep(0.6)

    if not args.dry_run:
        save_sources(sources)
        if not args.no_index:
            build_indexes()

    print()
    print(f"Done: {success} successful, {missed} missing/error.")
    if missed:
        print("Missing fighters should be reviewed manually and added only with compatible reuse rights.")

    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
