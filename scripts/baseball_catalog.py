"""Baseball catalogs, name lookups and offline asset validation.

Catalogs are maintained explicitly, like the football catalogs; generated
lookups use the same name normalization as football.
"""
import json
from pathlib import Path

from PIL import Image

from football_catalog import ROOT, ID_RE, build_lookup, normalize_name

DATA = ROOT / 'data' / 'baseball'
COMPETITIONS_FILE = DATA / 'competitions.json'
TEAMS_FILE = DATA / 'teams.json'


def load_baseball():
    return tuple(json.loads(path.read_text(encoding='utf-8'))
                 for path in (COMPETITIONS_FILE, TEAMS_FILE))


def build_team_lookup(teams):
    lookup, errors = {}, []
    for team in teams:
        table = lookup.setdefault(team['league'], {})
        for raw in [team['id'], team['name'], team['abbreviation'], *team['aliases']]:
            key = normalize_name(raw)
            if not key:
                errors.append(f"Team '{team['id']}' has an empty normalized name")
                continue
            owner = table.setdefault(key, team['id'])
            if owner != team['id']:
                errors.append(f"Team '{team['id']}' name '{raw}' collides with '{owner}'")
    return {league: dict(sorted(table.items())) for league, table in sorted(lookup.items())}, errors


def baseball_assets(entries):
    return {e['id']: {'name': e['name'], 'path': e['logo']} for e in entries if e['logo']}


def validate_baseball(root: Path, competitions, teams):
    errors, warnings = [], []
    fields = {
        'competitions': ('id', 'name', 'aliases', 'type', 'scope', 'continent', 'country', 'logo'),
        'teams': ('id', 'name', 'aliases', 'abbreviation', 'mlb_id', 'country', 'league', 'division', 'logo'),
    }
    catalogs = {'competitions': competitions, 'teams': teams}
    for kind, catalog in catalogs.items():
        if not isinstance(catalog, dict) or not isinstance(catalog.get(kind), list):
            errors.append(f"Baseball {kind} catalog must contain a '{kind}' list")
            continue
        if catalog.get('version') != 1:
            errors.append(f'Unsupported baseball {kind} catalog version')
        for entry in catalog[kind]:
            if not isinstance(entry, dict) or any(f not in entry for f in fields[kind]):
                errors.append(f'Baseball {kind} entry is missing required fields')
                continue
            for field in fields[kind]:
                value = entry[field]
                if field == 'aliases':
                    valid = isinstance(value, list) and all(isinstance(a, str) and a.strip() for a in value)
                elif field == 'mlb_id':
                    valid = type(value) is int and value > 0
                elif field == 'logo' or (field == 'country' and kind == 'competitions'):
                    valid = value is None or isinstance(value, str) and bool(value.strip())
                else:
                    valid = isinstance(value, str) and bool(value.strip())
                if not valid:
                    errors.append(f"Baseball {kind} '{entry.get('id')}' has invalid {field}")
            if not isinstance(entry['id'], str) or not ID_RE.fullmatch(entry['id']):
                errors.append(f"Invalid baseball id: {entry['id']!r}")
    if errors:
        return errors, warnings

    competitions, teams = competitions['competitions'], teams['teams']
    leagues = {c['id'] for c in competitions if c['type'] == 'league'}
    referenced = set()
    for kind, entries in [('competitions', competitions), ('teams', teams)]:
        seen = set()
        mlb_ids = set()
        for entry in entries:
            label = entry['id']
            if label in seen:
                errors.append(f'Duplicate baseball {kind} id: {label}')
            seen.add(label)
            if kind == 'teams':
                if entry['league'] not in leagues:
                    errors.append(f"Team '{label}' has unknown league '{entry['league']}'")
                if entry['country'] not in {'US', 'CA'}:
                    errors.append(f"Team '{label}' has invalid country")
                if entry['division'] not in {f'{l} {d}' for l in ('AL', 'NL') for d in ('East', 'Central', 'West')}:
                    errors.append(f"Team '{label}' has invalid division")
                if entry['mlb_id'] in mlb_ids:
                    errors.append(f"Duplicate MLB team id: {entry['mlb_id']}")
                mlb_ids.add(entry['mlb_id'])
                expected = f"baseball/teams/{entry['country'].lower()}/{label}.png"
            else:
                if entry['type'] != 'league' or entry['scope'] != 'club' or entry['continent'] != 'north-america':
                    errors.append(f"Competition '{label}' has invalid type, scope or continent")
                expected = f"baseball/competitions/{entry['continent']}/{label}.png"
            logo = entry['logo']
            if logo is None:
                warnings.append(f"Baseball '{label}' has no logo yet")
                continue
            referenced.add(logo)
            if logo != expected:
                errors.append(f"Baseball '{label}' logo must be '{expected}'")
                continue
            path = root / logo
            if not path.is_file():
                errors.append(f'Baseball logo not found: {logo}')
                continue
            try:
                with Image.open(path) as image:
                    alpha = image.convert('RGBA').getchannel('A')
                    if image.format != 'PNG':
                        errors.append(f'Baseball logo is not PNG: {logo}')
                    if alpha.getextrema()[0] == 255 or alpha.getbbox() is None:
                        errors.append(f'Baseball logo must have visible content and transparent pixels: {logo}')
                    if max(image.size) > 1024:
                        errors.append(f'Baseball logo exceeds 1024 px: {logo}')
            except OSError:
                errors.append(f'Cannot decode baseball logo: {logo}')
    for folder in ('baseball/competitions', 'baseball/teams'):
        for path in sorted((root / folder).rglob('*')):
            if path.is_file() and not path.name.startswith('.') and path.relative_to(root).as_posix() not in referenced:
                errors.append(f'Baseball image not referenced: {path.relative_to(root)}')
    errors.extend(build_lookup(competitions)[1])
    errors.extend(build_team_lookup(teams)[1])
    return errors, warnings
