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
SOURCES_FILE = ROOT / "data" / "sources.json"
BUILD_INDEX = ROOT / "scripts" / "build_index.py"

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "sports-assets/1.0 (+https://github.com/IsaacPrestol/sports-assets)"
ALLOWED_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

PREFERRED_WORDS = ("portrait", "headshot", "profile", "face", "fighter")
PENALTY_WORDS = (
    "poster",
    "logo",
    "banner",
    "fight night",
    "weigh-in",
    "weigh in",
    "press conference",
    "versus",
    " vs ",
    "crowd",
    "octagon",
)


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


def search_commons(name: str, limit: int = 12) -> list[dict]:
    queries = [f'"{name}" portrait', f'"{name}" UFC', f'"{name}"']
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
            title = page.get("title", "")
            if not title or title in seen:
                continue
            seen.add(title)

            info_list = page.get("imageinfo") or []
            if not info_list:
                continue
            info = info_list[0]
            mime = info.get("mime", "")
            if mime not in ALLOWED_MIME:
                continue

            ext = info.get("extmetadata", {})
            license_short = clean_html((ext.get("LicenseShortName") or {}).get("value"))
            if not license_short:
                continue

            candidates.append(
                {
                    "title": title,
                    "pageid": page.get("pageid"),
                    "mime": mime,
                    "url": info.get("thumburl") or info.get("url"),
                    "original_url": info.get("url"),
                    "width": info.get("thumbwidth") or info.get("width"),
                    "height": info.get("thumbheight") or info.get("height"),
                    "extmetadata": ext,
                }
            )

        if candidates:
            break

    return candidates


def score_candidate(name: str, candidate: dict) -> float:
    title = candidate["title"].lower().replace("file:", "")
    normalized_name = slugify(name).replace("-", " ")
    normalized_title = slugify(title).replace("-", " ")

    score = 0.0
    if normalized_name in normalized_title:
        score += 50

    for word in PREFERRED_WORDS:
        if word in title:
            score += 7

    for word in PENALTY_WORDS:
        if word in title:
            score -= 8

    width = candidate.get("width") or 0
    height = candidate.get("height") or 0
    if width and height:
        ratio = width / height
        if 0.55 <= ratio <= 0.95:
            score += 10
        elif 0.40 <= ratio <= 1.20:
            score += 4
        if height >= 700:
            score += 3

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
    }


def load_sources() -> dict:
    if not SOURCES_FILE.exists():
        return {}
    try:
        data = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
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


def process_fighter(name: str, sources: dict, force: bool, dry_run: bool) -> tuple[bool, str]:
    slug = slugify(name)
    current = existing_asset(slug)
    if current and not force:
        return True, f"SKIP -> {name}: already exists as {current.name}"

    candidates = search_commons(name)
    if not candidates:
        return False, f"MISS -> {name}: no suitable Wikimedia Commons image found"

    selected = max(candidates, key=lambda item: score_candidate(name, item))
    extension = ALLOWED_MIME[selected["mime"]]
    destination = FIGHTERS_DIR / f"{slug}{extension}"
    relative_path = destination.relative_to(ROOT).as_posix()

    if dry_run:
        score = score_candidate(name, selected)
        return True, f"DRY -> {name}: {selected['title']} (score {score:.1f})"

    if force:
        remove_existing_assets(slug)

    download_file(selected["url"], destination)
    sources[relative_path] = metadata_record(name, selected, relative_path)
    return True, f"OK -> {destination.name} <= {selected['title']}"


def build_indexes() -> None:
    subprocess.run([sys.executable, str(BUILD_INDEX)], check=True, cwd=ROOT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download reusable UFC fighter images from Wikimedia Commons and record attribution metadata."
    )
    parser.add_argument(
        "--fighter",
        action="append",
        dest="fighters",
        help="Download one fighter by name. Repeat this option for multiple fighters.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N fighters from the seed list.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing image for the same fighter.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Search and show the selected Commons file without downloading it.",
    )
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="Do not run scripts/build_index.py after downloading.",
    )
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

    sources = load_sources()
    success = 0
    missed = 0

    print(f"Processing {len(fighters)} UFC fighter(s)...")
    for index, name in enumerate(fighters, start=1):
        try:
            ok, message = process_fighter(name, sources, args.force, args.dry_run)
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
        print("Review missing fighters manually and add only images with compatible reuse rights.")

    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
