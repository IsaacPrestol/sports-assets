# Americas club crests — Design

Date: 2026-09-30
Status: pending review

## Goal

Add the top-division clubs of the 10 CONMEBOL countries and 6 CONCACAF leagues to the club catalog, with the same format, validation and update flow as the 25 European leagues (`docs/superpowers/specs/2026-09-30-football-clubs-design.md`).

## Context

- luukhopman/football-logos, the roster source of the previous phase, only covers European leagues.
- openfootball has partial data (Chile, Peru, Uruguay, Bolivia, Venezuela, Mexico and Central America are missing), so it can't be the only source.
- Wikipedia has one article per league and season, but the titles and team tables differ between leagues, so a scraper would be fragile.
- football-logos.cc has 1500×1500 px crests for all 16 countries, mixing every division. Honduras, El Salvador and Jamaica only have the national team's crest, so they are left out.
- The crests of Toronto FC, Vancouver Whitecaps and CF Montréal are on the United States page of football-logos.cc.

## Requirements

1. Leagues: Brazil, Argentina, Uruguay, Colombia, Chile, Paraguay, Peru, Ecuador, Bolivia, Venezuela, Mexico, MLS, Canadian Premier League, Costa Rica, Guatemala and Panama.
2. Clubs of each league's current season, plus those that have played in it since 2022 (calendar-year leagues) or 2022-23 (leagues spanning two years).
3. A club's country is its league's country. Canadian MLS clubs get `US`.
4. Rosters maintained by hand in the repo, taken from Wikipedia.
5. Main crest from football-logos.cc; if there's no valid one, a URL given by hand (Wikimedia).
6. Every match is confirmed visually before it's published, as in Europe.
7. `sync_clubs.py plan|accept|apply` processes luukhopman and the new rosters together; running `apply` again changes nothing.

## Rosters — `data/football/rosters.json`

```json
{
  "brasileirao-serie-a": {
    "2022": ["Flamengo", "Palmeiras", "..."],
    "2026": ["..."]
  },
  "liga-mx": {
    "2022-23": ["..."],
    "2026-27": ["..."]
  }
}
```

- Top-level key: id of a competition in `competitions.json` with `type: league` and a non-null `country`. All its clubs get that competition's `country`.
- Season key: `YYYY` or `YYYY-YY`. All seasons within a league use the same format, so alphabetical order is chronological order. The current season is the greatest.
- Values: club names as they appear on (English) Wikipedia, with no repeats within a season.
- Apertura and Clausura count as a single season.

## Sync integration

`scripts/football_clubs.py`:

- `COUNTRY_CODES` and `FL_COUNTRIES` add the 16 countries (`"Brazil": "BR"` → `brazil`, `"United States": "US"` → `usa`, `"Costa Rica": "CR"` → `costa-rica`...).
- New function `roster_index(rosters, competitions)` that returns entries with the same shape as `luuk_index`, keyed `"<country>|<name>"` (e.g. `"Brazil|Flamengo"`):
  - `country_folder`: the `COUNTRY_CODES` country name for the league's `country`.
  - `latest_season`: the last season the club appears in; `latest_path`: `null`.
  - If the club is in its league's current season, the entry carries that league as current.
- Entries from both indexes carry a `league` field (competition id or `null`). `luuk_index` fills it from `LEAGUE_IDS`; `merge_clubs` uses that field instead of looking up `LEAGUE_IDS`.
- Mappings (`clubs-mapping.json`): `"source": "url"` with a `url` field is allowed, for crests that aren't on football-logos.cc. `apply` downloads and normalizes that URL and records it in `sources.json`.

`scripts/sync_clubs.py`:

- `plan`, `accept [COUNTRY]` and `apply` combine both indexes. `apply` fails before downloading if a key has no mapping.
- The review sheet shows the club name and the proposed crest; roster entries have no luukhopman image.
- If a roster entry has neither a slug nor a `url`, `apply` warns and leaves the club with `logo: null` (there is no luukhopman fallback).

## New competitions (12)

Uruguay, Colombia, Chile, Paraguay, Peru, Ecuador, Bolivia, Venezuela, Canadian Premier League, Costa Rica, Guatemala and Panama, with `type: league`, `scope: club`, the correct confederation and continent, and a transparent logo from football-logos.cc or Wikimedia.

## Validation

`validate_assets.py` checks `rosters.json`:

- Every key is a competition of type `league` with a `country`, and that country has a name in `COUNTRY_CODES`.
- Every season has the format `YYYY` or `YYYY-YY`, all with the same format within the league.
- Every season is a non-empty list of non-empty names, with no duplicates and no leading or trailing spaces.

Mappings with `"source": "url"` must have a `url`.

## Tests

- `roster_index`: current season, relegated clubs (`league: null`), key and country derived from the league.
- `merge_clubs` with roster entries: new club, relegated club, new name as an alias.
- `rosters.json` validation: unknown league, league that isn't a `league`, season format, duplicates.
- Real catalog: `lookup["US"]["toronto fc"]` and `lookup["BR"]["flamengo"]` resolve.

## Documentation

README: clubs section with the Americas leagues and how to add a new season to `rosters.json`.

## Out of scope

- Honduras, El Salvador, Jamaica and the rest of CONCACAF.
- Second divisions.
- An automatic Wikipedia scraper.
