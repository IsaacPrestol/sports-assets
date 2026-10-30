"""Download NBA, NHL or NFL logos from reviewed data/sources.json URLs.

Usage: python scripts/sync_league.py nba [--force]
Maintain names, aliases, ESPN IDs and alignment in data/<sport>/teams.json.
As with MLB, existing logos are preserved unless --force is requested.
"""
import argparse
from datetime import date
import subprocess
import sys
from urllib.request import Request, urlopen

from football_catalog import ROOT
from football_clubs import load_json
from build_index import write_json
from league_catalog import LEAGUES, load_league, validate_league
from normalize_logo import normalize_logo


def sync(league, force=False):
    competitions, teams = load_league(league, ROOT)
    # Validate catalog metadata and paths before any writes. Image checks run
    # after downloads so --force can repair damaged or opaque existing files.
    preflight, _ = validate_league(ROOT, league, competitions, teams, check_images=False)
    if preflight:
        for error in preflight:
            print('ERROR:', error)
        return 1
    sources_path = ROOT / 'data/sources.json'
    sources = load_json(sources_path, {})
    failures = []
    for entry in competitions['competitions'] + teams['teams']:
        relative = entry['logo']
        if relative is None:
            continue
        destination = ROOT / relative
        if destination.exists() and not force:
            print('SKIP:', relative)
            continue
        source = sources.get(relative, {})
        url = source.get('url', '')
        if not isinstance(url, str) or not url.startswith('https://'):
            failures.append(f'{relative}: missing reviewed https source URL')
            continue
        raw = ROOT / '.cache' / league / (entry['id'] + '.png')
        raw.parent.mkdir(parents=True, exist_ok=True)
        try:
            request = Request(url, headers={'User-Agent': 'sports-assets/1.0'})
            with urlopen(request, timeout=30) as response:
                raw.write_bytes(response.read())
            normalize_logo(raw, destination)
        except (OSError, ValueError) as exc:
            failures.append(f'{relative}: {exc}')
            continue
        source['retrieved'] = date.today().isoformat()
        print('OK:', relative)
    write_json(sources_path, dict(sorted(sources.items())))
    errors, warnings = validate_league(ROOT, league, competitions, teams)
    for message in warnings:
        print('WARNING:', message)
    for message in failures + errors:
        print('ERROR:', message)
    if failures or errors:
        return 1
    subprocess.run([sys.executable, str(ROOT / 'scripts/build_index.py')], check=True, cwd=ROOT)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('league', choices=sorted(LEAGUES))
    parser.add_argument('--force', action='store_true', help='Replace logos using reviewed source URLs')
    args = parser.parse_args()
    return sync(args.league, args.force)


if __name__ == '__main__':
    raise SystemExit(main())
