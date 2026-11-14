"""Build the flag catalog from Wikidata and download flags from Wikimedia Commons.

Usage:
  python scripts/sync_flags.py seed       # add missing entries to data/flags.json and sources.json
  python scripts/sync_flags.py download   # download missing flags (add --force to replace all)

`seed` never changes entries already in data/flags.json: names, aliases and
images edited by hand are kept. Review new entries and their sources before
running `download`.
"""
import argparse
from datetime import date
import html
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from football_catalog import ROOT, normalize_name
from football_clubs import load_json
from build_index import write_json
from flags_catalog import FLAGS_FILE, flag_path, load_flags, normalize_flag, validate_flags

SOURCES_FILE = ROOT / "data" / "sources.json"
CACHE = ROOT / ".cache" / "flags"
HEADERS = {"User-Agent": "sports-assets-sync/1.0 (https://github.com/IsaacPrestol/sports-assets)"}
SPARQL = "https://query.wikidata.org/sparql"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
# Commons renders SVG flags to PNG at this width; normalize_flag caps the result at 1024 px.
RENDER_WIDTH = 1280
LANGUAGES = ("es", "fr", "de", "it", "pt")

# Exceptionally reserved ISO codes that Wikidata also tags with P297: not separate flags.
RESERVED = {"AC", "CP", "CQ", "DG", "TA"}

# Regions with their own flag and, often, their own sports teams.
# Code -> (parent, extra Wikidata label languages).
SUBDIVISIONS = {
    "GB-ENG": ("GB", ()),
    "GB-SCT": ("GB", ("gd",)),
    "GB-WLS": ("GB", ("cy",)),
    "GB-NIR": ("GB", ("ga",)),
    "ES-PV": ("ES", ("eu",)),
    "ES-CT": ("ES", ("ca",)),
    "ES-GA": ("ES", ("gl",)),
}

# Codes whose Wikidata item has no single flag (P41).
FLAG_FILES = {
    "AQ": "Flag of the Antarctic Treaty.svg",
    "BQ": "Flag of the Netherlands.svg",
    "CY": "Flag of Cyprus.svg",
    "EH": "Flag of the Sahrawi Arab Democratic Republic.svg",
    # Wikidata's "local" files for these two are regional logos; the official flag is France's.
    "GP": "Flag of France.svg",
    "YT": "Flag of France.svg",
    # Wikidata has the Taliban flag; FIFA and the IOC still use the tricolour.
    "AF": "Flag of Afghanistan (2013–2021).svg",
    # No official flag: the Ulster Banner is the one used by its football and Commonwealth Games teams.
    "GB-NIR": "Flag of Northern Ireland (1953–1972).svg",
}

NAMES = {
    "AQ": "Antarctica",
    "CN": "China",
    "MF": "Saint Martin",
    "NL": "Netherlands",
    "GB": "United Kingdom",
    "ES-PV": "Basque Country",
}

ALIASES = {
    "US": ["USA", "United States of America"],
    "GB": ["UK", "Great Britain"],
    "ES-PV": ["Euskadi", "País Vasco", "Basque Country", "Euskal Herria"],
    "ES-CT": ["Catalunya", "Cataluña"],
    "ES-GA": ["Galiza"],
    "XK": ["Kosova"],
    "NL": ["Holland", "Holanda", "Países Bajos"],
    "PF": ["Tahiti"],
    "AQ": ["Antártida", "Antarctique", "Antarktis"],
}


def fetch_json(url: str, params: dict) -> dict:
    request = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers=HEADERS)
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def fetch_bytes(url: str, attempts: int = 5) -> bytes:
    """GET with backoff: Wikimedia answers 429 when thumbnails are requested too fast."""
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 503) or attempt == attempts - 1:
                raise
            time.sleep(int(exc.headers.get("Retry-After") or 0) or 5 * 2 ** attempt)
    raise AssertionError("unreachable")


def sparql(query: str) -> list[dict]:
    rows = fetch_json(SPARQL, {"query": query, "format": "json"})["results"]["bindings"]
    return [{key: value["value"] for key, value in row.items()} for row in rows]


def file_name(url: str) -> str:
    return urllib.parse.unquote(url.rsplit("/", 1)[-1])


def wikidata_entries() -> dict[str, dict]:
    """Code -> {item, type, parent, a3, fifa, file}."""
    entries: dict[str, dict] = {}
    rows = sparql("""SELECT ?item ?code ?a3 ?flag WHERE {
      ?item wdt:P297 ?code. FILTER NOT EXISTS { ?item wdt:P576 ?dissolved }
      OPTIONAL { ?item wdt:P298 ?a3 } OPTIONAL { ?item wdt:P41 ?flag }
    }""")
    subdivision_codes = " ".join(f'"{code}"' for code in SUBDIVISIONS)
    rows += sparql(f"""SELECT ?item ?code ?flag WHERE {{
      VALUES ?code {{ {subdivision_codes} }} ?item wdt:P300 ?code. OPTIONAL {{ ?item wdt:P41 ?flag }}
    }}""")
    for row in rows:
        code = row["code"]
        if code in RESERVED:
            continue
        item = row["item"].rsplit("/", 1)[-1]
        entry = entries.setdefault(code, {"item": item, "a3": set(), "fifa": set(), "files": set()})
        if entry["item"] != item:
            # Several items share a code (e.g. Cyprus); keep the one that has a flag.
            if "flag" not in row or entry["files"]:
                continue
            entry.update(item=item, a3=set(), fifa=set(), files=set())
        if "a3" in row:
            entry["a3"].add(row["a3"])
        if "flag" in row:
            entry["files"].add(file_name(row["flag"]))
    for code, codes in fifa_codes().items():
        if code in entries:
            entries[code]["fifa"] |= codes
    for code, entry in entries.items():
        parent, _ = SUBDIVISIONS.get(code, (None, ()))
        entry["type"] = "subdivision" if parent else "country"
        entry["parent"] = parent.lower() if parent else None
        files = sorted(entry.pop("files"))
        entry["file"] = FLAG_FILES.get(code) or (files[0] if len(files) == 1 else None)
        if entry["file"] is None:
            raise ValueError(f"{code}: choose a flag in FLAG_FILES, Wikidata has {files or 'none'}")
    return entries


def fifa_codes() -> dict[str, set[str]]:
    """ISO code -> FIFA codes, read from each men's senior national team (FIFA codes live on teams)."""
    rows = sparql("""SELECT ?code ?fifa WHERE {
      ?team wdt:P3441 ?fifa; wdt:P1532 ?country; rdfs:label ?label. FILTER(lang(?label) = "en")
      FILTER(REGEX(?label, "^.+ men's national (association )?(football|soccer) team$"))
      { ?country wdt:P297 ?code } UNION { ?country wdt:P300 ?code }
    }""")
    result: dict[str, set[str]] = {}
    for row in rows:
        result.setdefault(row["code"], set()).add(row["fifa"])
    return result


def labels(items: list[str], languages: set[str]) -> dict[str, dict[str, str]]:
    result = {}
    for start in range(0, len(items), 50):
        data = fetch_json(WIKIDATA_API, {
            "action": "wbgetentities", "ids": "|".join(items[start:start + 50]), "props": "labels",
            "languages": "|".join(sorted(languages)), "format": "json",
        })
        for item, entity in data["entities"].items():
            result[item] = {lang: label["value"] for lang, label in entity.get("labels", {}).items()}
    return result


def plain(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def commons_metadata(files: list[str]) -> dict[str, dict]:
    result = {}
    for start in range(0, len(files), 50):
        data = fetch_json(COMMONS_API, {
            "action": "query", "prop": "imageinfo", "iiprop": "extmetadata", "format": "json",
            "titles": "|".join("File:" + name for name in files[start:start + 50]),
        })
        normalized = {n["to"]: n["from"] for n in data["query"].get("normalized", [])}
        for page in data["query"]["pages"].values():
            if "missing" in page:
                raise ValueError(f"Commons file not found: {page['title']}")
            name = normalized.get(page["title"], page["title"]).removeprefix("File:")
            meta = page["imageinfo"][0]["extmetadata"]
            result[name] = {
                "license": plain(meta.get("LicenseShortName", {}).get("value", "")) or None,
                "artist": plain(meta.get("Artist", {}).get("value", "")) or None,
            }
    return result


def drop_colliding_aliases(flags: list[dict]) -> list[str]:
    """Remove aliases that would resolve to more than one flag; ids and names always win."""
    owners: dict[str, set[str]] = {}
    for entry in flags:
        for raw in [entry["id"], entry["name"], *entry["aliases"]]:
            owners.setdefault(normalize_name(raw), set()).add(entry["id"])
    reserved = {normalize_name(raw) for entry in flags for raw in (entry["id"], entry["name"])}
    dropped = []
    for entry in flags:
        kept = []
        for alias in entry["aliases"]:
            key = normalize_name(alias)
            if len(owners[key]) > 1 or (key in reserved and owners[key] != {entry["id"]}):
                dropped.append(f"{entry['id']}: {alias}")
            else:
                kept.append(alias)
        entry["aliases"] = kept
    return dropped


def seed() -> int:
    catalog = load_json(FLAGS_FILE, {"version": 1, "flags": []})
    existing = {entry["id"] for entry in catalog["flags"]}
    sources = load_json(SOURCES_FILE, {})
    entries = {code: e for code, e in wikidata_entries().items() if code.lower() not in existing}
    if not entries:
        print("Nothing to add.")
        return 0
    languages = {"en", *LANGUAGES, *(lang for _, langs in SUBDIVISIONS.values() for lang in langs)}
    names = labels(sorted({e["item"] for e in entries.values()}), languages)
    metadata = commons_metadata(sorted({e["file"] for e in entries.values()}))
    new = []
    for code, entry in sorted(entries.items()):
        item_labels = names.get(entry["item"], {})
        name = NAMES.get(code) or item_labels.get("en")
        if not name:
            raise ValueError(f"{code}: no English label on {entry['item']}")
        extra = SUBDIVISIONS.get(code, (None, ()))[1]
        candidates = [*ALIASES.get(code, []), *(item_labels.get(lang) for lang in (*LANGUAGES, *extra)),
                      item_labels.get("en"), *sorted(entry["a3"]), *sorted(entry["fifa"])]
        aliases, seen = [], {normalize_name(code), normalize_name(name)}
        for alias in candidates:
            if alias and normalize_name(alias) not in seen:
                seen.add(normalize_name(alias))
                aliases.append(alias)
        flag_id = code.lower()
        new.append({"id": flag_id, "code": code, "name": name, "aliases": aliases,
                    "type": entry["type"], "parent": entry["parent"], "flag": flag_path(flag_id)})
        meta = metadata[entry["file"]]
        sources[flag_path(flag_id)] = {
            "url": "https://commons.wikimedia.org/wiki/Special:FilePath/"
                   + urllib.parse.quote(entry["file"].replace(" ", "_")) + f"?width={RENDER_WIDTH}",
            "retrieved": None,
            "license": meta["license"],
            "notes": f"Wikimedia Commons, File:{entry['file']}"
                     + (f"; author: {meta['artist']}" if meta["artist"] else "")
                     + f"; flag chosen via Wikidata {entry['item']}",
        }
    catalog["flags"] = sorted(catalog["flags"] + new, key=lambda e: e["id"])
    for message in drop_colliding_aliases(catalog["flags"]):
        print("DROPPED ambiguous alias:", message)
    write_json(FLAGS_FILE, catalog)
    write_json(SOURCES_FILE, dict(sorted(sources.items())))
    print(f"Added {len(new)} flag(s) to {FLAGS_FILE.relative_to(ROOT).as_posix()}. Review them, then run download.")
    return 0


def download(force: bool = False) -> int:
    catalog = load_flags()
    preflight, _ = validate_flags(ROOT, catalog, check_images=False)
    if preflight:
        for error in preflight:
            print("ERROR:", error)
        return 1
    sources = load_json(SOURCES_FILE, {})
    failures = []
    for entry in catalog["flags"]:
        relative = entry["flag"]
        if relative is None:
            continue
        destination = ROOT / relative
        if destination.exists() and not force:
            continue
        source = sources.get(relative, {})
        url = source.get("url", "")
        if not isinstance(url, str) or not url.startswith("https://"):
            failures.append(f"{relative}: missing reviewed https source URL")
            continue
        raw = CACHE / f"{entry['id']}.png"
        raw.parent.mkdir(parents=True, exist_ok=True)
        try:
            raw.write_bytes(fetch_bytes(url))
            width, height = normalize_flag(raw, destination)
        except (OSError, ValueError) as exc:
            failures.append(f"{relative}: {exc}")
            continue
        source["retrieved"] = date.today().isoformat()
        print(f"OK: {relative} ({width}x{height})")
    write_json(SOURCES_FILE, dict(sorted(sources.items())))
    errors, warnings = validate_flags(ROOT, catalog)
    for message in warnings:
        print("WARNING:", message)
    for message in failures + errors:
        print("ERROR:", message)
    if failures or errors:
        return 1
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_index.py")], check=True, cwd=ROOT)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("seed", "download"))
    parser.add_argument("--force", action="store_true", help="download: replace existing flags")
    args = parser.parse_args()
    return seed() if args.command == "seed" else download(args.force)


if __name__ == "__main__":
    raise SystemExit(main())
