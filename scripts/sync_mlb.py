"""Download MLB logos from the reviewed URLs in data/sources.json.

Names, aliases, MLB IDs and divisions live in data/baseball/teams.json.
Existing PNGs are preserved unless --force is passed. After a brand change,
review the new source URL before replacing the logo.
"""
import argparse
from datetime import date
from pathlib import Path
import subprocess
import sys
from urllib.request import Request, urlopen

from baseball_catalog import ROOT, load_baseball, validate_baseball
from football_clubs import load_json
from normalize_logo import normalize_logo
from build_index import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--force', action='store_true', help='Replace existing logos from reviewed source URLs')
    args = parser.parse_args()
    competitions, teams = load_baseball()
    # Missing files are what this command downloads. Reject every other
    # catalog error before writing files or making network requests.
    preflight, _ = validate_baseball(ROOT, competitions, teams)
    preflight = [error for error in preflight if not error.startswith('Baseball logo not found:')]
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
        if destination.exists() and not args.force:
            print('SKIP:', relative)
            continue
        source = sources.get(relative, {})
        url = source.get('url', '')
        if not url.startswith('https://'):
            failures.append(f'{relative}: missing reviewed https source URL')
            continue
        raw = ROOT / '.cache/mlb' / (entry['id'] + '.png')
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
    errors, warnings = validate_baseball(ROOT, competitions, teams)
    for message in warnings:
        print('WARNING:', message)
    for message in failures + errors:
        print('ERROR:', message)
    if failures or errors:
        return 1
    subprocess.run([sys.executable, str(ROOT / 'scripts/build_index.py')], check=True, cwd=ROOT)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
