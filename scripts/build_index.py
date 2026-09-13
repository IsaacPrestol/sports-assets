from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

COLLECTIONS = {
    "fighters": ROOT / "ufc" / "fighters",
    "competitions": ROOT / "football" / "competitions",
    "ufc-logos": ROOT / "ufc" / "logos",
}

ALLOWED = {".png", ".webp", ".jpg", ".jpeg", ".svg"}


def pretty_name(slug: str) -> str:
    special = {
        "ufc": "UFC",
        "uefa": "UEFA",
        "fifa": "FIFA",
        "afc": "AFC",
        "caf": "CAF",
        "concacaf": "CONCACAF",
        "conmebol": "CONMEBOL",
        "mls": "MLS",
    }
    return " ".join(special.get(word, word.capitalize()) for word in slug.split("-"))


def build_collection(folder: Path):
    result = {}
    if not folder.exists():
        return result

    for file in sorted(folder.iterdir()):
        if not file.is_file() or file.name.startswith("."):
            continue
        if file.suffix.lower() not in ALLOWED:
            continue

        slug = file.stem
        result[slug] = {
            "name": pretty_name(slug),
            "path": file.relative_to(ROOT).as_posix(),
        }
    return result


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    all_assets = {}

    for collection, folder in COLLECTIONS.items():
        data = build_collection(folder)
        all_assets[collection] = data
        (DATA / f"{collection}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    (DATA / "all-assets.json").write_text(
        json.dumps(all_assets, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Indexes generated:")
    for collection, items in all_assets.items():
        print(f"  {collection}: {len(items)} asset(s)")


if __name__ == "__main__":
    main()
