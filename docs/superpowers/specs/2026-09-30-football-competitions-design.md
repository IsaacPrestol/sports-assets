# Football competitions by continent — Design

Date: 2026-09-30
Status: pending review

## Goal

An external app will read this repository's images (through jsDelivr / GitHub raw). It needs a JSON catalog that identifies each competition unambiguously so it never shows the wrong logo.

This phase covers football **competitions** only. Club crests for the top 5 leagues are the next phase and are outside this design.

## Context

- `football/competitions/` currently holds 17 flat images.
- 11 of them aren't logos but FootyLogos.com collages (league logo + every club crest, white background, watermark): Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Eredivisie, Liga Portugal, Brasileirão Série A, Liga Profesional Argentina, Liga MX and MLS.
- The other 6 look like standalone logos: UEFA Champions League, UEFA Europa League, UEFA Conference League, Copa del Rey, Copa Libertadores and FIFA Club World Cup. They'll be reviewed one by one before being accepted.
- `data/competitions.json` is generated from the file name (which produces wrong names such as "Laliga" or "Liga Mx").
- The app doesn't consume the repository yet, so there's no need to stay compatible with old paths.

## Requirements

1. Organize competition logos in folders by continent.
2. Keep the collages (don't delete them) in a separate location.
3. A JSON catalog with a stable id, official name and aliases for each competition.
4. An alias → id index so the app can resolve names coming from other sources.
5. Clean logos found online: no watermark, transparent background.
6. Automatic validation (locally and in GitHub Actions) that prevents publishing an inconsistent catalog.

## Folder structure

```text
football/
├── competitions/
│   ├── europe/
│   ├── south-america/
│   ├── north-america/
│   ├── asia/
│   └── world/
└── collages/
```

- The `africa/` and `oceania/` folders aren't created until there's a competition from those continents.
- National-team tournaments go in their confederation's continent (Euro → `europe`, Copa América → `south-america`, Gold Cup → `north-america`). FIFA tournaments go in `world/`.
- The 11 collages are moved to `football/collages/<id>.png` unchanged.

## Image format

- PNG with an alpha channel (transparent background).
- Trimmed to the edges of the content.
- Longest side at most 1024 px; smaller images aren't upscaled.
- File name: `<id>.png`.
- Preferred source: official high-resolution SVG or PNG. Nothing with a watermark.

A script `scripts/normalize_logo.py <input> <output>` does the trimming and resizing. It uses Pillow (a `requirements.txt` is added).

## Catalog — `data/football/competitions.json`

This is the source of truth. No script generates it: Claude maintains it at the repository owner's request (or the owner does directly).

```json
{
  "version": 1,
  "competitions": [
    {
      "id": "laliga",
      "name": "LaLiga",
      "aliases": ["La Liga", "LaLiga EA Sports", "Spanish La Liga"],
      "type": "league",
      "scope": "club",
      "continent": "europe",
      "confederation": "UEFA",
      "country": "ES",
      "logo": "football/competitions/europe/laliga.png",
      "collage": "football/collages/laliga.png"
    }
  ]
}
```

Fields:

| Field | Type | Rules |
|---|---|---|
| `id` | string | kebab-case, unique, stable once published; equal to the logo file name without extension |
| `name` | string | current official name |
| `aliases` | string[] | other common names (sponsors, languages, former names); may be empty |
| `type` | enum | `league`, `cup`, `super-cup`, `international` (tournaments between clubs or national teams from several countries; `scope` tells them apart) |
| `scope` | enum | `club`, `national-team` |
| `continent` | enum | `europe`, `south-america`, `north-america`, `asia`, `africa`, `oceania`, `world` |
| `confederation` | enum | `UEFA`, `CONMEBOL`, `CONCACAF`, `AFC`, `CAF`, `OFC`, `FIFA` |
| `country` | string \| null | ISO 3166-1 alpha-2, or ISO 3166-2 for UK nations (`GB-ENG`); `null` for international tournaments |
| `logo` | string \| null | path relative to the repository root; `null` while the clean logo is missing |
| `collage` | string \| null | collage path, or `null` if there isn't one |

Entries are sorted by continent and, within each, in the order of the list below.

## Competitions included (36)

**europe (24)**

| id | name | type | scope | country |
|---|---|---|---|---|
| uefa-champions-league | UEFA Champions League | international | club | null |
| uefa-europa-league | UEFA Europa League | international | club | null |
| uefa-conference-league | UEFA Conference League | international | club | null |
| uefa-super-cup | UEFA Super Cup | super-cup | club | null |
| premier-league | Premier League | league | club | GB-ENG |
| laliga | LaLiga | league | club | ES |
| serie-a | Serie A | league | club | IT |
| bundesliga | Bundesliga | league | club | DE |
| ligue-1 | Ligue 1 | league | club | FR |
| eredivisie | Eredivisie | league | club | NL |
| liga-portugal | Liga Portugal | league | club | PT |
| fa-cup | FA Cup | cup | club | GB-ENG |
| efl-cup | EFL Cup | cup | club | GB-ENG |
| community-shield | FA Community Shield | super-cup | club | GB-ENG |
| copa-del-rey | Copa del Rey | cup | club | ES |
| supercopa-de-espana | Supercopa de España | super-cup | club | ES |
| coppa-italia | Coppa Italia | cup | club | IT |
| supercoppa-italiana | Supercoppa Italiana | super-cup | club | IT |
| dfb-pokal | DFB-Pokal | cup | club | DE |
| dfl-supercup | DFL-Supercup | super-cup | club | DE |
| coupe-de-france | Coupe de France | cup | club | FR |
| trophee-des-champions | Trophée des Champions | super-cup | club | FR |
| uefa-euro | UEFA European Championship | international | national-team | null |
| uefa-nations-league | UEFA Nations League | international | national-team | null |

**south-america (5)**

| id | name | type | scope | country |
|---|---|---|---|---|
| copa-libertadores | CONMEBOL Libertadores | international | club | null |
| copa-sudamericana | CONMEBOL Sudamericana | international | club | null |
| brasileirao-serie-a | Campeonato Brasileiro Série A | league | club | BR |
| liga-profesional-argentina | Liga Profesional de Fútbol | league | club | AR |
| copa-america | Copa América | international | national-team | null |

**north-america (4)**

| id | name | type | scope | country |
|---|---|---|---|---|
| liga-mx | Liga MX | league | club | MX |
| mls | Major League Soccer | league | club | US |
| concacaf-champions-cup | Concacaf Champions Cup | international | club | null |
| concacaf-gold-cup | Concacaf Gold Cup | international | national-team | null |

**asia (1)**

| id | name | type | scope | country |
|---|---|---|---|---|
| saudi-pro-league | Saudi Pro League | league | club | SA |

**world (2)**

| id | name | type | scope | country |
|---|---|---|---|---|
| fifa-world-cup | FIFA World Cup | international | national-team | null |
| fifa-club-world-cup | FIFA Club World Cup | international | club | null |

The ids of the 17 current competitions stay the same as their current file names. MLS has `country: "US"` even though it includes Canadian clubs.

## Alias index — `data/football/competitions-lookup.json`

Generated by `scripts/build_index.py` from the catalog. It's a flat `normalized key → id` object. For each competition it includes its `id`, its `name` and all its `aliases`.

Normalization (the same one the app must apply before looking up):

1. Unicode NFKD decomposition and removal of diacritical marks.
2. Lowercase.
3. Every character that isn't `a-z` or `0-9` is replaced by a space.
4. Repeated spaces are collapsed and the ends are trimmed.

Example: `"LaLiga EA Sports"` → `"laliga ea sports"`; `"Primera División"` → `"primera division"`; `"laliga"` (id) → `"laliga"`.

Intended use in the app:

1. Normalize the received name.
2. Look it up in `competitions-lookup.json` → `id`.
3. Look the `id` up in `competitions.json` → `logo`.
4. Build the URL: `https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@<tag>/<logo>`.

The JSON is written with sorted keys so regeneration is deterministic (CI compares with `git diff`).

## Changes to existing scripts

`scripts/build_index.py`:

- Stops generating `data/competitions.json` (the file is deleted).
- Generates `data/football/competitions-lookup.json`.
- `data/all-assets.json` includes `competitions` as `{id: {name, path}}` taken from the catalog, only for entries with a `logo`. The UFC collections don't change.

`scripts/validate_assets.py` keeps its current checks and also walks `football/competitions/*/` and `football/collages/`. It adds:

Errors (fail validation):

- The catalog isn't valid JSON or is missing a required field.
- A `type`, `scope`, `continent` or `confederation` value outside the allowed ones.
- Duplicate `id`, or one that isn't kebab-case.
- `logo` isn't `football/competitions/<continent>/<id>.png`, or the file doesn't exist.
- `collage` isn't `football/collages/<id>.png`, or the file doesn't exist.
- An image in `football/competitions/` or `football/collages/` with no catalog entry.
- An image directly in `football/competitions/` (outside a continent folder).
- Two different competitions produce the same normalized key.
- A logo without an alpha channel.

Warnings (don't fail):

- Competitions with `logo: null`.

GitHub Actions installs `requirements.txt` before validating, because the alpha-channel check uses Pillow.

## Sourcing logos

- They're searched for online: official competition and federation websites, press kits, Wikimedia Commons and watermark-free logo repositories.
- Every accepted logo is recorded in `data/sources.json`, keyed by path: `{"url": ..., "retrieved": "YYYY-MM-DD", "license": ... | null, "notes": ... | null}`.
- The 6 current images that look like logos are reviewed visually; if they have a watermark, a non-transparent background or are outdated, they're replaced.
- If no acceptable logo is found, the entry is left with `logo: null` and the owner is told.

## Documentation

`README.md` is updated with the new structure, the catalog schema, the normalization rules and the example of use from the app.

## Out of scope

- Club crests (next phase).
- Logo variants (monochrome, dark background) and SVG format.
- A script for adding competitions (rejected by the owner).
- Changes to the UFC assets or scripts, except what's strictly needed in `build_index.py` and `validate_assets.py`.
