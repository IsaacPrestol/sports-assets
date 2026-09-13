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
CACHE_FILE = ROOT / ".cache" / "wikimedia.json"

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"

USER_AGENT = "sports-assets/2.0 (+https://github.com/IsaacPrestol/sports-assets)"
ALLOWED_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

# Ordered from most to least trustworthy. The bonus dominates the text score so a
# Wikidata portrait always beats a lucky filename match from a full text search.
TIER_BONUS = {
    "override": 400,
    "wikidata-p18": 220,
    "wikipedia-lead": 190,
    "commons-category": 120,
    "commons-depicts": 100,
    "commons-search": 0,
}

HEADSHOT_POSITIVE = {
    "headshot": 55,
    "portrait": 45,
    "cropped": 45,
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
    "wax": 90,
    "graffiti": 90,
    "crowd": 60,
    "group photo": 70,
    "audience": 55,
    "referee": 50,
    "autograph": 45,
    "signing": 40,
    "red carpet": 40,
    "training": 30,
    "sparring": 30,
    "seminar": 35,
    "arena": 25,
    "collage": 60,
    "screenshot": 45,
    "map": 70,
}

MMA_KEYWORDS = (
    "mixed martial",
    "ufc",
    "mma",
    "ultimate fighting",
    "kickbox",
    "muay thai",
    "grappler",
)

_CACHE: dict[str, dict] = {}
_CACHE_DIRTY = False
_CACHE_ENABLED = True


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


def load_cache() -> None:
    global _CACHE
    if not _CACHE_ENABLED or not CACHE_FILE.exists():
        return
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            _CACHE = data
    except json.JSONDecodeError:
        _CACHE = {}


def save_cache() -> None:
    if not _CACHE_ENABLED or not _CACHE_DIRTY:
        return
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(_CACHE, ensure_ascii=False), encoding="utf-8")


def api_get(endpoint: str, params: dict[str, str | int], retries: int = 3) -> dict:
    """GET a MediaWiki API endpoint with retries and an on-disk response cache."""
    global _CACHE_DIRTY

    query = dict(params)
    query.setdefault("format", "json")
    query.setdefault("formatversion", 2)
    url = f"{endpoint}?{urlencode(query)}"

    if _CACHE_ENABLED and url in _CACHE:
        return _CACHE[url]

    last_error = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=30) as response:
                data = json.load(response)
            if _CACHE_ENABLED:
                _CACHE[url] = data
                _CACHE_DIRTY = True
            return data
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"MediaWiki API request failed ({endpoint}): {last_error}")


def http_json(params: dict[str, str | int], retries: int = 3) -> dict:
    return api_get(COMMONS_API, params, retries=retries)


def download_file(url: str, destination: Path, retries: int = 3) -> None:
    temporary = destination.with_name(destination.name + ".part")
    last_error = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=60) as response, temporary.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 128)
                    if not chunk:
                        break
                    output.write(chunk)
            if temporary.stat().st_size < 2048:
                raise RuntimeError("downloaded file is suspiciously small")
            temporary.replace(destination)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            temporary.unlink(missing_ok=True)
            if attempt + 1 < retries:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Image download failed: {last_error}")


# ---------------------------------------------------------------------------
# Entity resolution: name -> Wikipedia article -> Wikidata item
# ---------------------------------------------------------------------------


def name_variants(name: str) -> list[str]:
    variants = [name]
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    if ascii_name and ascii_name != name:
        variants.append(ascii_name)
    variants.append(f"{name} (fighter)")
    variants.append(f"{name} (mixed martial artist)")
    seen: set[str] = set()
    ordered = []
    for variant in variants:
        if variant not in seen:
            seen.add(variant)
            ordered.append(variant)
    return ordered


def wikipedia_page(title: str) -> dict | None:
    data = api_get(
        WIKIPEDIA_API,
        {
            "action": "query",
            "titles": title,
            "redirects": 1,
            "prop": "pageprops|pageimages|extracts",
            "ppprop": "wikibase_item|disambiguation",
            "piprop": "original",
            "exintro": 1,
            "explaintext": 1,
            "exchars": 600,
        },
    )
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None
    page = pages[0]
    if page.get("missing") or page.get("invalid"):
        return None
    props = page.get("pageprops", {}) or {}
    if "disambiguation" in props:
        return None
    return page


def wikipedia_search(name: str, limit: int = 5) -> list[str]:
    data = api_get(
        WIKIPEDIA_API,
        {
            "action": "query",
            "list": "search",
            "srsearch": f'"{name}" mixed martial artist UFC',
            "srlimit": limit,
            "srnamespace": 0,
        },
    )
    return [item.get("title", "") for item in data.get("query", {}).get("search", []) if item.get("title")]


def looks_like_fighter(page: dict) -> bool:
    haystack = " ".join(
        [
            page.get("extract", "") or "",
            (page.get("pageprops", {}) or {}).get("description", "") or "",
        ]
    ).lower()
    return any(keyword in haystack for keyword in MMA_KEYWORDS)


def resolve_entity(name: str, strict: bool) -> dict:
    """Return {'title', 'qid', 'lead_image', 'commons_category', 'verified'}."""
    page = None
    for variant in name_variants(name):
        candidate_page = wikipedia_page(variant)
        if candidate_page and looks_like_fighter(candidate_page):
            page = candidate_page
            break
        if candidate_page and page is None:
            page = candidate_page

    if page is None or not looks_like_fighter(page):
        for title in wikipedia_search(name):
            candidate_page = wikipedia_page(title)
            if candidate_page and looks_like_fighter(candidate_page):
                page = candidate_page
                break

    entity: dict = {
        "title": "",
        "qid": "",
        "lead_image": "",
        "commons_category": "",
        "verified": False,
    }
    if page is None:
        return entity

    entity["title"] = page.get("title", "")
    entity["verified"] = looks_like_fighter(page)
    if strict and not entity["verified"]:
        return entity

    original = page.get("original") or {}
    if original.get("source"):
        entity["lead_image"] = original["source"].rsplit("/", 1)[-1]

    qid = (page.get("pageprops", {}) or {}).get("wikibase_item", "")
    if not qid:
        return entity
    entity["qid"] = qid

    data = api_get(WIKIDATA_API, {"action": "wbgetentities", "ids": qid, "props": "claims"})
    claims = ((data.get("entities") or {}).get(qid) or {}).get("claims", {})

    def first_claim(prop: str) -> str:
        for statement in claims.get(prop, []) or []:
            value = ((statement.get("mainsnak") or {}).get("datavalue") or {}).get("value")
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    entity["p18"] = first_claim("P18")
    entity["commons_category"] = first_claim("P373")
    return entity


# ---------------------------------------------------------------------------
# Candidate collection
# ---------------------------------------------------------------------------


def candidate_from_page(page: dict, tier: str = "commons-search") -> dict | None:
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
        "tier": tier,
        "url": info.get("thumburl") or info.get("url"),
        "original_url": info.get("url"),
        "width": info.get("thumbwidth") or info.get("width"),
        "height": info.get("thumbheight") or info.get("height"),
        "orig_width": info.get("width"),
        "orig_height": info.get("height"),
        "extmetadata": ext,
    }


IMAGEINFO_PROPS = {
    "prop": "imageinfo",
    "iiprop": "url|mime|size|extmetadata",
    "iiurlwidth": 1000,
}


def fetch_exact_file(title: str, tier: str = "override") -> dict | None:
    if not title:
        return None
    if not title.lower().startswith("file:"):
        title = f"File:{title}"
    params = {"action": "query", "titles": title, "redirects": 1}
    params.update(IMAGEINFO_PROPS)
    data = http_json(params)
    pages = data.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return None
    return candidate_from_page(pages[0], tier=tier)


def category_files(category: str, limit: int = 40) -> list[dict]:
    if not category:
        return []
    if not category.lower().startswith("category:"):
        category = f"Category:{category}"
    params = {
        "action": "query",
        "generator": "categorymembers",
        "gcmtitle": category,
        "gcmtype": "file",
        "gcmlimit": limit,
    }
    params.update(IMAGEINFO_PROPS)
    try:
        data = http_json(params)
    except RuntimeError:
        return []
    results = []
    for page in data.get("query", {}).get("pages", []) or []:
        candidate = candidate_from_page(page, tier="commons-category")
        if candidate:
            results.append(candidate)
    return results


def depicts_files(qid: str, limit: int = 30) -> list[dict]:
    if not qid:
        return []
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"haswbstatement:P180={qid}",
        "gsrnamespace": 6,
        "gsrlimit": limit,
    }
    params.update(IMAGEINFO_PROPS)
    try:
        data = http_json(params)
    except RuntimeError:
        return []
    results = []
    for page in data.get("query", {}).get("pages", []) or []:
        candidate = candidate_from_page(page, tier="commons-depicts")
        if candidate:
            results.append(candidate)
    return results


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
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": search_term,
            "gsrnamespace": 6,
            "gsrlimit": limit,
        }
        params.update(IMAGEINFO_PROPS)
        try:
            data = http_json(params)
        except RuntimeError:
            continue

        for page in data.get("query", {}).get("pages", []) or []:
            candidate = candidate_from_page(page, tier="commons-search")
            if not candidate:
                continue
            title = candidate["title"]
            if title in seen:
                continue
            seen.add(title)
            candidates.append(candidate)

    return candidates


def collect_candidates(name: str, entity: dict, deep: bool) -> list[dict]:
    """Merge every source, keeping the best tier for each distinct file."""
    by_title: dict[str, dict] = {}

    def add(items: list[dict]) -> None:
        for item in items:
            existing = by_title.get(item["title"])
            if existing is None:
                by_title[item["title"]] = item
                continue
            if TIER_BONUS.get(item["tier"], 0) > TIER_BONUS.get(existing["tier"], 0):
                existing["tier"] = item["tier"]

    p18 = entity.get("p18", "")
    if p18:
        exact = fetch_exact_file(p18, tier="wikidata-p18")
        if exact:
            add([exact])

    lead = entity.get("lead_image", "")
    if lead:
        exact = fetch_exact_file(lead.replace("_", " "), tier="wikipedia-lead")
        if exact:
            add([exact])

    add(category_files(entity.get("commons_category", "")))
    if not entity.get("commons_category"):
        add(category_files(entity.get("title", "") or name))

    add(depicts_files(entity.get("qid", "")))

    if deep or len(by_title) < 3:
        add(search_commons(name))

    return list(by_title.values())


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def normalized_file_stem(title: str) -> str:
    value = title.lower().replace("file:", "")
    value = re.sub(r"\.(jpg|jpeg|png|webp)$", "", value)
    return slugify(value).replace("-", " ")


def surname(name: str) -> str:
    parts = [part for part in slugify(name).split("-") if len(part) > 2]
    return parts[-1] if parts else ""


def describe_text(candidate: dict) -> str:
    ext = candidate.get("extmetadata", {}) or {}

    def meta(key: str) -> str:
        return clean_html((ext.get(key) or {}).get("value"))

    return " ".join([meta("ObjectName"), meta("ImageDescription"), meta("Categories")]).lower()


def score_candidate(name: str, candidate: dict) -> float:
    if "_score" in candidate:
        return candidate["_score"]

    title = candidate["title"].lower().replace("file:", "")
    normalized_name = slugify(name).replace("-", " ")
    stem = normalized_file_stem(candidate["title"])
    tier = candidate.get("tier", "commons-search")

    score = float(TIER_BONUS.get(tier, 0))

    # Exact filenames are usually the cleanest portrait-style Commons image.
    if stem == normalized_name:
        score += 120
    elif stem in {f"{normalized_name} cropped", f"{normalized_name} crop"}:
        score += 135
    elif stem.startswith(normalized_name):
        score += 65
    elif normalized_name in stem:
        score += 45
    elif surname(name) and surname(name) in stem:
        score += 20
    elif tier in {"wikidata-p18", "wikipedia-lead", "override"}:
        pass  # trusted source, the filename does not need to match the name
    else:
        # The file never mentions the fighter, so the tier bonus alone must not
        # be enough to get it selected.
        score -= 80
        score -= 60 if tier in {"commons-category", "commons-depicts"} else 150

    for word, points in HEADSHOT_POSITIVE.items():
        if word in title:
            score += points

    for word, points in CONTEXT_PENALTIES.items():
        if word in title:
            score -= points

    # The filename alone is a thin signal, so the Commons description and
    # categories are scanned too, at half weight to avoid false negatives.
    description = describe_text(candidate)
    if description:
        for word, points in CONTEXT_PENALTIES.items():
            if word in description and word not in title:
                score -= points * 0.5
        for word, points in HEADSHOT_POSITIVE.items():
            if word in description and word not in title:
                score += points * 0.5

    # Photos naming another person alongside the fighter are usually contextual,
    # not a clean headshot.
    if " with " in title or " and " in title:
        score -= 45

    width = candidate.get("orig_width") or candidate.get("width") or 0
    height = candidate.get("orig_height") or candidate.get("height") or 0
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
        if height < 320 or width < 240:
            score -= 60

    candidate["_score"] = score
    return score


def commons_page_url(title: str) -> str:
    title = title.replace(" ", "_")
    return "https://commons.wikimedia.org/wiki/" + quote(title, safe=":_()-,")


def metadata_record(name: str, candidate: dict, relative_path: str, entity: dict) -> dict:
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
        "selection_tier": candidate.get("tier", ""),
        "selection_score": round(score_candidate(name, candidate), 1),
        "wikidata_id": entity.get("qid", ""),
        "wikipedia_title": entity.get("title", ""),
    }


def load_json_dict(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def save_json_dict(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def save_sources(sources: dict) -> None:
    save_json_dict(SOURCES_FILE, sources)


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


def remove_existing_assets(slug: str, keep: Path | None = None) -> None:
    for extension in ALLOWED_MIME.values():
        path = FIGHTERS_DIR / f"{slug}{extension}"
        if keep is not None and path == keep:
            continue
        path.unlink(missing_ok=True)


def drop_stale_sources(sources: dict, slug: str, keep: str) -> None:
    prefix = (FIGHTERS_DIR / slug).relative_to(ROOT).as_posix()
    for key in [k for k in sources if k.startswith(prefix + ".") and k != keep]:
        sources.pop(key, None)


def ranked_candidates(
    name: str,
    use_overrides: bool = True,
    deep: bool = False,
    strict: bool = False,
) -> tuple[list[dict], dict]:
    overrides = load_json_dict(OVERRIDES_FILE)
    if use_overrides and name in overrides:
        exact = fetch_exact_file(str(overrides[name]), tier="override")
        if exact:
            exact["_override"] = True
            return [exact], {"title": "", "qid": "", "verified": True}

    entity = resolve_entity(name, strict=strict)
    candidates = collect_candidates(name, entity, deep=deep)
    candidates.sort(key=lambda item: score_candidate(name, item), reverse=True)
    return candidates, entity


def process_fighter(
    name: str,
    sources: dict,
    overrides: dict,
    args: argparse.Namespace,
) -> tuple[bool, str]:
    slug = slugify(name)
    current = existing_asset(slug)
    if current and not args.force:
        return True, f"SKIP -> {name}: already exists as {current.name}"

    candidates, entity = ranked_candidates(
        name,
        use_overrides=not args.no_overrides,
        deep=args.deep,
        strict=args.strict,
    )
    if not candidates:
        return False, f"MISS -> {name}: no reusable headshot candidate found"

    selected = candidates[0]
    selected_score = score_candidate(name, selected)
    used_override = bool(selected.get("_override"))

    if not used_override and selected_score < args.min_score:
        return False, (
            f"MISS -> {name}: best candidate is not headshot-like enough "
            f"({selected_score:.1f} < {args.min_score}) -> {selected['title']}"
        )

    if args.dry_run:
        preview = []
        for index, candidate in enumerate(candidates[: max(1, args.show_top)], start=1):
            preview.append(
                f"#{index} [{candidate.get('tier')}] {candidate['title']} "
                f"({score_candidate(name, candidate):.1f})"
            )
        origin = entity.get("qid") or "no-wikidata"
        return True, f"DRY -> {name} <{origin}>: " + " | ".join(preview)

    extension = ALLOWED_MIME[selected["mime"]]
    destination = FIGHTERS_DIR / f"{slug}{extension}"
    relative_path = destination.relative_to(ROOT).as_posix()

    download_file(selected["url"], destination)
    remove_existing_assets(slug, keep=destination)
    drop_stale_sources(sources, slug, relative_path)

    sources[relative_path] = metadata_record(name, selected, relative_path, entity)
    if args.save_overrides and not used_override:
        overrides[name] = selected["title"]

    label = "OVERRIDE" if used_override else selected.get("tier", "auto").upper()
    return True, f"OK -> {destination.name} <= {selected['title']} ({label} {selected_score:.1f})"


def build_indexes() -> None:
    subprocess.run([sys.executable, str(BUILD_INDEX)], check=True, cwd=ROOT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download reusable UFC fighter headshots from Wikimedia Commons using "
            "Wikidata and Commons categories, and record attribution metadata."
        )
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
    parser.add_argument(
        "--save-overrides",
        action="store_true",
        help="Write every automatic pick back into the overrides file for reproducible runs.",
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Always run the Commons full text search in addition to the structured sources.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Reject articles that do not clearly describe a mixed martial artist.",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=50.0,
        help="Minimum score required to accept an automatic pick. Default: 50.",
    )
    parser.add_argument("--no-cache", action="store_true", help="Do not read or write the API response cache.")
    parser.add_argument("--no-index", action="store_true", help="Do not rebuild JSON indexes.")
    return parser.parse_args()


def main() -> int:
    global _CACHE_ENABLED

    args = parse_args()
    _CACHE_ENABLED = not args.no_cache
    load_cache()
    FIGHTERS_DIR.mkdir(parents=True, exist_ok=True)

    fighters = args.fighters if args.fighters else load_seed()
    if args.limit is not None:
        fighters = fighters[: max(0, args.limit)]

    if not fighters:
        print("No fighters to process.")
        return 1

    sources = load_json_dict(SOURCES_FILE)
    overrides = load_json_dict(OVERRIDES_FILE)
    success = 0
    missed = 0
    failures: list[str] = []

    print(f"Processing {len(fighters)} UFC fighter(s) in HEADSHOT mode...")
    for index, name in enumerate(fighters, start=1):
        try:
            ok, message = process_fighter(name, sources, overrides, args)
            print(f"[{index}/{len(fighters)}] {message}")
            if ok:
                success += 1
            else:
                missed += 1
                failures.append(name)
        except Exception as exc:  # noqa: BLE001
            missed += 1
            failures.append(name)
            print(f"[{index}/{len(fighters)}] ERROR -> {name}: {exc}")

        if index < len(fighters):
            time.sleep(0.6)

    save_cache()

    if not args.dry_run:
        save_sources(sources)
        if args.save_overrides:
            save_json_dict(OVERRIDES_FILE, overrides)
        if not args.no_index:
            build_indexes()

    print()
    print(f"Done: {success} successful, {missed} missing/error.")
    if failures:
        print("Review manually: " + ", ".join(failures))
        print("Missing fighters should be reviewed manually and added only with compatible reuse rights.")

    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
