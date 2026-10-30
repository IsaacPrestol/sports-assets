"""NBA, NHL and NFL catalogs using the same contracts as MLB.

Lookups share MLB's league-scoped team resolver and football's normalizer.
The sport folders keep American football separate from association football.
"""
import json
from pathlib import Path

from PIL import Image

from baseball_catalog import build_team_lookup, baseball_assets as catalog_assets
from football_catalog import ROOT, ID_RE, build_lookup

LEAGUES = {
    'nba': {'sport': 'basketball', 'name': 'National Basketball Association', 'count': 30,
            'country': None, 'divisions': {
                'Eastern': {'Atlantic', 'Central', 'Southeast'},
                'Western': {'Northwest', 'Pacific', 'Southwest'}}},
    'nhl': {'sport': 'hockey', 'name': 'National Hockey League', 'count': 32,
            'country': None, 'divisions': {
                'Eastern': {'Atlantic', 'Metropolitan'}, 'Western': {'Central', 'Pacific'}}},
    'nfl': {'sport': 'american-football', 'name': 'National Football League', 'count': 32,
            'country': 'US', 'divisions': {
                'AFC': {'East', 'North', 'South', 'West'}, 'NFC': {'East', 'North', 'South', 'West'}}},
}


def load_league(league, root=ROOT):
    data = root / 'data' / LEAGUES[league]['sport']
    return tuple(json.loads((data / f'{kind}.json').read_text(encoding='utf-8'))
                 for kind in ('competitions', 'teams'))


def validate_league(root: Path, league, competitions, teams, *, check_images=True):
    config = LEAGUES[league]
    sport = config['sport']
    errors, warnings = [], []
    required = {
        'competitions': ('id', 'name', 'aliases', 'type', 'scope', 'continent', 'country', 'logo'),
        'teams': ('id', 'name', 'aliases', 'abbreviation', 'espn_id', 'country',
                  'league', 'conference', 'division', 'logo'),
    }
    for kind, catalog in [('competitions', competitions), ('teams', teams)]:
        if not isinstance(catalog, dict) or not isinstance(catalog.get(kind), list):
            errors.append(f"{league.upper()} catalog must contain a '{kind}' list")
            continue
        if catalog.get('version') != 1:
            errors.append(f'Unsupported {league.upper()} {kind} catalog version')
        for entry in catalog[kind]:
            if not isinstance(entry, dict) or any(f not in entry for f in required[kind]):
                errors.append(f'{league.upper()} {kind} entry is missing required fields')
                continue
            for field in required[kind]:
                value = entry[field]
                if field == 'aliases':
                    valid = isinstance(value, list) and all(isinstance(a, str) and a.strip() for a in value)
                elif field == 'espn_id':
                    valid = type(value) is int and value > 0
                elif field == 'logo' or (field == 'country' and kind == 'competitions'):
                    valid = value is None or isinstance(value, str) and bool(value.strip())
                else:
                    valid = isinstance(value, str) and bool(value.strip())
                if not valid:
                    errors.append(f"{league.upper()} '{entry.get('id')}' has invalid {field}")
            if not isinstance(entry['id'], str) or not ID_RE.fullmatch(entry['id']):
                errors.append(f"Invalid {league.upper()} id: {entry['id']!r}")
    if errors:
        return errors, warnings

    competitions, teams = competitions['competitions'], teams['teams']
    if len(teams) != config['count']:
        errors.append(f"{league.upper()} team count must be {config['count']}, got {len(teams)}")
    known_leagues = {c['id'] for c in competitions if c['type'] == 'league'}
    if known_leagues != {league}:
        errors.append(f'{sport} competitions must contain the {league} league')
    referenced = set()
    for kind, entries in [('competitions', competitions), ('teams', teams)]:
        seen, provider_ids = set(), set()
        for entry in entries:
            label = entry['id']
            if label in seen:
                errors.append(f'Duplicate {sport} {kind} id: {label}')
            seen.add(label)
            if kind == 'teams':
                if entry['league'] not in known_leagues or entry['league'] != league:
                    errors.append(f"Team '{label}' has unknown league '{entry['league']}'")
                countries = {'US'} if league == 'nfl' else {'US', 'CA'}
                if entry['country'] not in countries:
                    errors.append(f"Team '{label}' has invalid country")
                if entry['division'] not in config['divisions'].get(entry['conference'], set()):
                    errors.append(f"Team '{label}' has invalid conference/division")
                if entry['espn_id'] in provider_ids:
                    errors.append(f"Duplicate {league.upper()} ESPN id: {entry['espn_id']}")
                provider_ids.add(entry['espn_id'])
                expected = f"{sport}/teams/{entry['country'].lower()}/{label}.png"
            else:
                if (entry['id'] != league or entry['type'] != 'league' or entry['scope'] != 'club'
                        or entry['continent'] != 'north-america' or entry['country'] != config['country']):
                    errors.append(f"Competition '{label}' has invalid league metadata")
                expected = f'{sport}/competitions/north-america/{label}.png'
            logo = entry['logo']
            if logo is None:
                warnings.append(f"{league.upper()} '{label}' has no logo yet")
                continue
            referenced.add(logo)
            if logo != expected:
                errors.append(f"{league.upper()} '{label}' logo must be '{expected}'")
                continue
            if not check_images:
                continue
            path = root / logo
            if not path.is_file():
                errors.append(f'League logo not found: {logo}')
                continue
            try:
                with Image.open(path) as image:
                    alpha = image.convert('RGBA').getchannel('A')
                    if image.format != 'PNG':
                        errors.append(f'League logo is not PNG: {logo}')
                    if alpha.getextrema()[0] == 255 or alpha.getbbox() is None:
                        errors.append(f'League logo must have visible content and transparent pixels: {logo}')
                    if max(image.size) > 1024:
                        errors.append(f'League logo exceeds 1024 px: {logo}')
            except OSError:
                errors.append(f'Cannot decode league logo: {logo}')
    for kind in ('competitions', 'teams'):
        for path in sorted((root / sport / kind).rglob('*')):
            if path.is_file() and not path.name.startswith('.') and path.relative_to(root).as_posix() not in referenced:
                errors.append(f'League image not referenced: {path.relative_to(root)}')
    errors.extend(build_lookup(competitions)[1])
    errors.extend(build_team_lookup(teams)[1])
    return errors, warnings
