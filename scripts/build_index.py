from pathlib import Path
import json
import sys

from football_catalog import LOOKUP_FILE, build_lookup, competition_assets, load_catalog
from football_clubs import CLUBS_FILE, CLUBS_LOOKUP_FILE, build_club_lookup, club_assets, load_json
from baseball_catalog import DATA as BASEBALL_DATA, baseball_assets, build_team_lookup, load_baseball
from league_catalog import LEAGUES, load_league, catalog_assets

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

COLLECTIONS = {
    "fighters": ROOT / "ufc" / "fighters",
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


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    league_assets = {}
    for league, config in LEAGUES.items():
        league_competitions, league_teams = load_league(league)
        competition_lookup, competition_errors = build_lookup(league_competitions['competitions'])
        league_team_lookup, league_team_errors = build_team_lookup(league_teams['teams'])
        if competition_errors or league_team_errors:
            for error in competition_errors + league_team_errors:
                print('ERROR:', error)
            sys.exit(1)
        folder = DATA / config['sport']
        write_json(folder / 'competitions-lookup.json', competition_lookup)
        write_json(folder / 'teams-lookup.json', league_team_lookup)
        league_assets[config['sport'] + '-competitions'] = catalog_assets(league_competitions['competitions'])
        league_assets[config['sport'] + '-teams'] = catalog_assets(league_teams['teams'])
    baseball_competitions, baseball_teams = load_baseball()
    baseball_lookup, baseball_errors = build_lookup(baseball_competitions['competitions'])
    team_lookup, team_errors = build_team_lookup(baseball_teams['teams'])
    if baseball_errors or team_errors:
        for error in baseball_errors + team_errors:
            print('ERROR:', error)
        sys.exit(1)
    write_json(BASEBALL_DATA / 'competitions-lookup.json', baseball_lookup)
    write_json(BASEBALL_DATA / 'teams-lookup.json', team_lookup)
    competitions = load_catalog()["competitions"]
    lookup, errors = build_lookup(competitions)
    if errors:
        for error in errors:
            print("ERROR:", error)
        sys.exit(1)
    write_json(LOOKUP_FILE, lookup)

    clubs = load_json(CLUBS_FILE, {"clubs": []})["clubs"]
    club_lookup, club_errors = build_club_lookup(clubs)
    if club_errors:
        for error in club_errors:
            print("ERROR:", error)
        sys.exit(1)
    write_json(CLUBS_LOOKUP_FILE, club_lookup)

    all_assets = {
        **league_assets,
        'baseball-competitions': baseball_assets(baseball_competitions['competitions']),
        'baseball-teams': baseball_assets(baseball_teams['teams']),
        "fighters": build_collection(COLLECTIONS["fighters"]),
        "competitions": competition_assets(competitions),
        "clubs": club_assets(clubs),
        "ufc-logos": build_collection(COLLECTIONS["ufc-logos"]),
    }
    for collection in COLLECTIONS:
        write_json(DATA / f"{collection}.json", all_assets[collection])
    write_json(DATA / "all-assets.json", all_assets)

    print("Indexes generated:")
    for collection, items in all_assets.items():
        print(f"  {collection}: {len(items)} asset(s)")
    print(f"  competition lookup: {len(lookup)} name(s)")
    print(f"  club lookup: {sum(len(t) for t in club_lookup.values())} name(s)")


if __name__ == "__main__":
    main()
