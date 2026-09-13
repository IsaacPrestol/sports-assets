from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "ufc" / "private-fighters"
USER_AGENT = "sports-assets/1.0 (+https://github.com/IsaacPrestol/sports-assets)"

# ESPN athlete IDs. These images are for local/personal fallback use only.
# The output folder is ignored by Git and must not be committed to the public repo.
FIGHTERS = {
    "Tom Aspinall": "4010976",
    "Natalia Silva": "4054605",
    "Erin Blanchfield": "4350796",
    "Carlos Ulberg": "4695736",
}

BASE = "https://a.espncdn.com/i/headshots/mma/players/full/{athlete_id}.png"


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def download(name: str, athlete_id: str, force: bool = False) -> tuple[bool, str]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    destination = OUT_DIR / f"{slugify(name)}.png"

    if destination.exists() and not force:
        return True, f"SKIP -> {name}: {destination.name} already exists"

    url = BASE.format(athlete_id=athlete_id)
    request = Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urlopen(request, timeout=30) as response:
            content_type = response.headers.get("Content-Type", "")
            if "image" not in content_type.lower():
                return False, f"MISS -> {name}: ESPN returned {content_type or 'non-image content'}"
            data = response.read()
    except Exception as exc:  # noqa: BLE001
        return False, f"MISS -> {name}: {exc}"

    destination.write_bytes(data)
    return True, f"OK -> {name}: {destination.relative_to(ROOT).as_posix()}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download local-only UFC headshots for fighters whose reusable Commons image "
            "is missing. The output directory is ignored by Git."
        )
    )
    parser.add_argument(
        "--fighter",
        action="append",
        help="Download a specific fighter by exact name. Repeat for multiple fighters.",
    )
    parser.add_argument("--force", action="store_true", help="Replace existing local files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    names = args.fighter if args.fighter else list(FIGHTERS)

    unknown = [name for name in names if name not in FIGHTERS]
    if unknown:
        for name in unknown:
            print(f"UNKNOWN -> {name}")
        return 2

    success = 0
    failed = 0
    print(f"Downloading {len(names)} local-only UFC headshot(s)...")

    for name in names:
        ok, message = download(name, FIGHTERS[name], force=args.force)
        print(message)
        if ok:
            success += 1
        else:
            failed += 1

    print()
    print(f"Done: {success} successful, {failed} failed.")
    print("These files live under ufc/private-fighters/ and are ignored by Git.")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
