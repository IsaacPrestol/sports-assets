# Sports Assets CDN

Logos, crests and images for football, MLB, NBA, NHL, NFL and UFC, with JSON
catalogs that turn a name like `"Atlético de Madrid"` or `"GSW"` into a stable id and an
image URL. Everything is served straight from GitHub through
[jsDelivr](https://www.jsdelivr.com/), so there is nothing to host.

```text
https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@main/football/clubs/es/real-madrid.png
```

## What's inside

| Collection | Count | Images | Catalog |
|---|---:|---|---|
| Football competitions | 66 | `football/competitions/<continent>/<id>.png` | `data/football/competitions.json` |
| Football clubs | 8,807 catalogued, 1,531 with a crest | `football/clubs/<country>/<id>.png` | `data/football/clubs.json` |
| MLB | 30 teams + league | `baseball/` | `data/baseball/` |
| NBA | 30 teams + league | `basketball/` | `data/basketball/` |
| NHL | 32 teams + league | `hockey/` | `data/hockey/` |
| NFL | 32 teams + league | `american-football/` | `data/american-football/` |
| UFC | fighter photos and logos (none downloaded yet) | `ufc/` | `data/fighters.json`, `data/ufc-logos.json` |

Football clubs cover 41 leagues (the current season plus every club that has
played in them since 2021/22 in Europe or 2022 in the Americas) and the full
entrant lists of the English, Spanish, Italian, German and French domestic cups,
including qualifying rounds. Clubs without a verified transparent crest are
still in the catalog with `logo: null`, so you can recognise them and fall back
to your own placeholder.

All images are transparent PNGs, trimmed, never upscaled, with the longest side
at most 1024 px.

## Using the ids

Every asset has an **id**: a lowercase, hyphenated slug such as `real-madrid`,
`uefa-champions-league` or `golden-state-warriors`.

- **Ids are stable.** Once published, an id never changes, even if the club or
  team is renamed. A renamed team keeps its id and gets the new name, with the
  old name kept as an alias (e.g. `utah-mammoth` still resolves
  `"Utah Hockey Club"`).
- **The id is the file name.** `real-madrid` is `football/clubs/es/real-madrid.png`.
- **Ids are unique within a collection.** No two football clubs share an id,
  even in different countries. Clubs that share a name get a suffix:
  `liverpool` (Liverpool FC), `afc-liverpool` and `liverpool-uy` (Uruguay).
- **Store the id, not the name or the path.** Save `real-madrid` in your
  database and build the URL when you need it. Names have spelling variants,
  and paths are better read from the catalog than assembled by hand.

### From a name to an image

Data from an API or a scoreboard comes as names: `"Atlético de Madrid"`,
`"LaLiga EA Sports"`, `"NYY"`. Resolve them in three steps.

**1. Normalize the name.** Lookups are keyed by a normalized form: letters that
don't decompose are transliterated (`ø→o`, `æ→ae`, `œ→oe`, `ł→l`, `ı→i`, `đ/ð→d`,
`þ→th`, `ß→ss`), accents are stripped, everything is lowercased, anything that
isn't a letter or digit becomes a space, and spaces are collapsed.

```text
"Wisła Kraków"        → "wisla krakow"
"LaLiga EA Sports"    → "laliga ea sports"
"Brøndby IF"          → "brondby if"
```

**2. Look it up to get the id.** Ids, official names, aliases and (for US
leagues) abbreviations are all indexed.

| Collection | Lookup file | Key |
|---|---|---|
| Football competitions | `data/football/competitions-lookup.json` | `lookup[name]` |
| Football clubs | `data/football/clubs-lookup.json` | `lookup[country][name]` |
| MLB / NBA / NHL / NFL teams | `data/<sport>/teams-lookup.json` | `lookup[league][name]` |
| MLB / NBA / NHL / NFL leagues | `data/<sport>/competitions-lookup.json` | `lookup[name]` |

Football clubs must be looked up **inside their country**, because names like
"Sporting", "Dinamo" or "Liverpool" exist in several countries. The country
key is an ISO code, with England and Scotland as `GB-ENG` and `GB-SCT`.

```text
clubs-lookup["ES"]["real madrid"]          → "real-madrid"
clubs-lookup["GB-ENG"]["liverpool"]        → "liverpool"
competitions-lookup["laliga ea sports"]    → "laliga"
basketball teams-lookup["nba"]["gsw"]      → "golden-state-warriors"
baseball teams-lookup["mlb"]["nyy"]        → "new-york-yankees"
```

**3. Get the path and build the URL.** Find the id in the catalog (or in
`data/all-assets.json`) and prefix its `logo` / `path`:

```text
https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@main/ + football/clubs/es/real-madrid.png
```

If a name isn't found, it isn't a known alias yet. Add it to `aliases` in the
catalog (see [Contributing](#contributing)) rather than hard-coding a mapping in
your app.

### Clubs with similar or identical names

**Always pass the country.** 18 club names exist in more than one country, such
as Arsenal (England and Argentina), Everton (England and Chile), Santos (Brazil
and Costa Rica), Racing (Spain, Argentina and Uruguay) or Atlético Nacional
(Colombia and Panama). The lookup is split by country, so `"Everton"` in
`GB-ENG` and in `CL` resolve to different clubs.

**Ids are disambiguated, never shared.** The best-known club keeps the plain id
and the others get a suffix, usually their country code:

| Name | Country | Id |
|---|---|---|
| Liverpool FC | `GB-ENG` | `liverpool` |
| Liverpool | `UY` | `liverpool-uy` |
| Everton | `CL` | `everton-cl` |
| Santos | `CR` | `santos-cr` |
| Atlético Nacional | `PA` | `atletico-nacional-pa` |

Don't derive the club from the id: `everton-cl` is not Everton FC. Always go
through the lookup or the catalog.

**Different clubs in the same country stay separate.** Liverpool FC and AFC
Liverpool, Mansfield Town and AFC Mansfield, or RC Strasbourg and AS
Strasbourg are distinct entries with their own crests. A short name points to
the club it normally means (`"Liverpool"` → `liverpool`, `"Strasbourg"` →
`rc-strasbourg-alsace`). The other club needs its full name
(`"AFC Liverpool"` → `afc-liverpool`). An alias is only added when it is
unambiguous within the country, and validation rejects collisions. So if a
short name like `"Sporting"` in Spain doesn't resolve, that is deliberate: use
the full name (`"Sporting Gijón"` → `real-sporting-de-gijon`).

**French amateur clubs with the same name** carry their FFF (French federation)
id in the name and in `external_ids.fff`: `"Afa"` resolves to one club, and the
other is `"Afa (FFF 14858)"` → `afa-fr`. If your data comes from the FFF, match
on that id rather than the name.

**Numbers and suffixes are part of the name.** `CSKA 1948` and `CSKA Sofia` are
different clubs, and `SSV Jeddeloh II` is the club's actual name, not a reserve
side. Don't strip years or numerals before looking a name up.

**Match on provider ids when you have them.** Clubs may have
`external_ids.espn` and `external_ids.fff`, and US teams have `espn_id` or
`mlb_id`. If your feed uses one of those providers, build a reverse index once.
It's more reliable than any name:

```js
const clubs = (await fetch(CDN + "data/football/clubs.json").then((r) => r.json())).clubs;
const byEspnId = Object.fromEntries(
  clubs.filter((c) => c.external_ids?.espn).map((c) => [c.external_ids.espn, c])
);
byEspnId["86"].logo; // "football/clubs/es/real-madrid.png"
```

### Women's, reserve and youth teams

The catalog currently contains **clubs' first teams only**: there are no
separate entries for women's teams, B / II reserve sides, or youth teams (U19,
U21, U23). A club whose official name happens to include such a word, like
`SSV Jeddeloh II`, is listed under that name like any other club.

Most women's, reserve and youth sides play under the main club's crest, so a
practical approach is:

1. Look the name up **exactly as received** first. This keeps clubs like
   `SSV Jeddeloh II` correct.
2. If it isn't found, remove the team marker and look up the parent club:
   `Women`, `Ladies`, `Femenino`, `Féminine`, `Frauen`, `Femminile`, `(W)`,
   `B`, `II`, `U19`, `U21`, `U23`, `Reserves`.
3. Use the parent's crest, but keep the team type in your own data. Don't add
   `"Arsenal Women"` as an alias of `arsenal`: an alias means *the same team*,
   and women's teams may get their own entries later.

```js
const TEAM_MARKER = /\s*(\(w\)|women|ladies|femenino|f[eé]minine|frauen|femminile|reserves|\bb\b|\bii\b|u-?19|u-?21|u-?23)\s*$/i;

function resolveClub(country, name) {
  const table = lookup[country] ?? {};
  const exact = table[normalizeName(name)];
  if (exact) return { id: exact, parentCrest: false };
  const parent = table[normalizeName(name.replace(TEAM_MARKER, ""))];
  return parent ? { id: parent, parentCrest: true } : null;
}

resolveClub("GB-ENG", "Arsenal Women"); // { id: "arsenal", parentCrest: true }
resolveClub("DE", "SSV Jeddeloh II");   // { id: "ssv-jeddeloh-ii", parentCrest: false }
```

Some women's clubs are independent, or use a different crest from the men's
club with the same name. Treat a parent crest as a fallback, not a guarantee.

### One file for everything: `all-assets.json`

`data/all-assets.json` lists every asset that has an image, grouped by
collection, as `{id: {name, path}}`. If you already know your ids, this is the
only file you need.

```json
{
  "clubs": {
    "real-madrid": { "name": "Real Madrid", "path": "football/clubs/es/real-madrid.png" }
  },
  "competitions": { "...": "..." },
  "baseball-teams": { "...": "..." },
  "basketball-teams": { "...": "..." },
  "hockey-teams": { "...": "..." },
  "american-football-teams": { "...": "..." }
}
```

Collections: `competitions`, `clubs`, `baseball-teams`, `baseball-competitions`,
`basketball-teams`, `basketball-competitions`, `hockey-teams`,
`hockey-competitions`, `american-football-teams`,
`american-football-competitions`, `fighters`, `ufc-logos`. Clubs with
`logo: null` are not included.

### Example: JavaScript

```js
const CDN = "https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@main/";

const TRANSLIT = { ø: "o", Ø: "o", æ: "ae", Æ: "ae", œ: "oe", Œ: "oe", ł: "l", Ł: "l",
  ı: "i", đ: "d", Đ: "d", ð: "d", Ð: "d", þ: "th", Þ: "th", ß: "ss" };

function normalizeName(value) {
  return value
    .replace(/[øØæÆœŒłŁıđĐðÐþÞß]/g, (c) => TRANSLIT[c])
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

const [lookup, assets] = await Promise.all([
  fetch(CDN + "data/football/clubs-lookup.json").then((r) => r.json()),
  fetch(CDN + "data/all-assets.json").then((r) => r.json()),
]);

function clubCrestUrl(country, name) {
  const id = lookup[country]?.[normalizeName(name)];
  const asset = id && assets.clubs[id];
  return asset ? CDN + asset.path : null; // null: unknown club or no crest yet
}

clubCrestUrl("ES", "Atlético de Madrid");
// → https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@main/football/clubs/es/atletico-madrid.png
```

### Example: Python

The repo's own normalizer is `normalize_name` in `scripts/football_catalog.py`.

```python
import json, re, unicodedata, urllib.request

CDN = "https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@main/"
TRANSLIT = str.maketrans({"ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "œ": "oe", "Œ": "oe",
                          "ł": "l", "Ł": "l", "ı": "i", "đ": "d", "Đ": "d", "ð": "d",
                          "Ð": "d", "þ": "th", "Þ": "th", "ß": "ss"})

def normalize_name(value):
    decomposed = unicodedata.normalize("NFKD", value.translate(TRANSLIT))
    no_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", no_marks.lower()).split())

def load(path):
    with urllib.request.urlopen(CDN + path) as response:
        return json.load(response)

teams = load("data/basketball/teams-lookup.json")
assets = load("data/all-assets.json")

team_id = teams["nba"][normalize_name("GSW")]           # "golden-state-warriors"
print(CDN + assets["basketball-teams"][team_id]["path"])
```

### Pin a version in production

`@main` follows the latest commit, but jsDelivr caches it, so changes can take
a while to show up. For production, pin a commit or a tag so images and catalogs never
change under you:

```text
https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@40e3764/football/clubs/es/real-madrid.png
https://cdn.jsdelivr.net/gh/IsaacPrestol/sports-assets@v1.0.0/football/clubs/es/real-madrid.png
```

## Football competitions

`data/football/competitions.json` is the hand-edited source of truth.
Logos live in `football/competitions/<continent>/<id>.png`. Older collages
(league logo plus club crests) are kept in `football/collages/`.

| Field | Description |
|---|---|
| `id` | stable id; matches the file name |
| `name` | official name |
| `aliases` | other common names, in any language |
| `type` | `league`, `cup`, `super-cup` or `international` |
| `scope` | `club` or `national-team` |
| `continent` | logo folder: `europe`, `south-america`, `north-america`, `asia`, `africa`, `oceania` or `world` |
| `confederation` | `UEFA`, `CONMEBOL`, `CONCACAF`, `AFC`, `CAF`, `OFC` or `FIFA` |
| `country` | ISO code (`ES`, `GB-ENG`…) or `null` for international competitions |
| `logo` | logo path, or `null` if there is no clean logo yet |
| `collage` | collage path, or `null` |

**Check the country.** Names like "Premier League", "Serie A", "Bundesliga"
or "Ligue 1" are also used by leagues in other countries. If your source tells
you the country, compare it with `country` (or `confederation` for
international competitions) and treat a mismatch as "no logo".

## Football clubs

`data/football/clubs.json` has `version` and a `clubs` list:

```json
{
  "id": "real-madrid",
  "name": "Real Madrid",
  "aliases": ["Real Madrid CF"],
  "country": "ES",
  "league": "laliga",
  "logo": "football/clubs/es/real-madrid.png",
  "external_ids": { "espn": "86" }
}
```

| Field | Description |
|---|---|
| `id` | stable id; matches the file name |
| `name` | club name as used on English Wikipedia |
| `aliases` | other common names |
| `country` | ISO code of the club's league (`ES`, `GB-ENG`, `GB-SCT`…) |
| `league` | competition id of its league this season, or `null` if it plays outside the 41 covered leagues |
| `logo` | crest path, or `null` if there is no verified crest yet |
| `external_ids` | optional ids from other providers: `espn`, `fff` (French federation). Useful for matching, never a replacement for `id` |

- **Country is the league's country.** Toronto FC, Vancouver Whitecaps and
  CF Montréal play in MLS, so their country is `US`.
- **The folder never changes.** A crest stays in `football/clubs/<country>/`
  when the club is promoted or relegated.
- **Different clubs stay apart.** AFC Liverpool and Liverpool FC, AFC
  Mansfield and Mansfield Town, or AS Strasbourg and RC Strasbourg are
  separate entries. Spellings like "Leeds United AFC" are aliases of the same
  club. When two French clubs have indistinguishable names, the catalog adds
  their FFF id instead of an ambiguous alias.

### Sources

- **Europe (25 leagues):** club lists from
  [luukhopman/football-logos](https://github.com/luukhopman/football-logos).
- **Americas (16 leagues: the 10 CONMEBOL countries, Liga MX, MLS, Canadian
  Premier League, Costa Rica, Guatemala and Panama):** club lists in
  `data/football/rosters.json`, maintained by hand from Wikipedia.
- **Crests:** [football-logos.cc](https://github.com/Leo4815162342/football-logos)
  (1024 px) first. Otherwise the luukhopman PNG (139×181) or, in the Americas,
  the crest from the club's Wikipedia article or another recorded source. The
  validator warns about low-resolution crests.

### Domestic cup coverage

`data/football/domestic-coverage.json` records the 2026/27 audit, checked on
30 October 2026: sources, club ids per competition, entry round where known,
and an explicit list of missing crests.

| Competition | Entrants catalogued | List coverage |
|---|---:|---|
| Premier League / LaLiga / Serie A | 20 each | complete |
| Bundesliga / Ligue 1 | 18 each | complete |
| FA Cup | 743 | official accepted entries, from the extra preliminary round |
| EFL Cup | 92 | complete |
| Copa del Rey | 126 | includes the 20 preliminary-round clubs and their 10 losers |
| Coppa Italia | 44 | includes the preliminary round; no placeholder TBD teams |
| DFB-Pokal | 64 | complete |
| Super cups of the five countries | 2 each; Spain 4 | all participants covered |
| Coupe de France | 7,031 | partial: 7,002 regional FFF identities plus other national entrants |

"Complete" refers to the **list of participants**, not to crest availability.
A club without a verified transparent crest has `logo: null` and is left out of
`all-assets.json`. Generic images, another club's crest, or white backgrounds
removed automatically are never used.

For France, 190 match pages across 19 groups (including Mayotte and Réunion)
were read through the TheFootData mirror of FFF competition 449168. The list
does not replace the full register: for example, LAURA shows 892 clubs in
matches against 897 officially entered. Withdrawals before kick-off, byes, and
the local rounds of New Caledonia, French Polynesia and Saint-Pierre-et-Miquelon
are not reconciled yet, so the file marks this competition as incomplete.

Cup participation lives only in the audit. `league` holds the current league,
or `null` for clubs outside the covered leagues. The top five divisions were
checked against 2026/27 lists.

## MLB, NBA, NHL and NFL

Each sport has its own image folder and data folder:

| League | Teams | Images | Data |
|---|---:|---|---|
| MLB | 30 | `baseball/` | `data/baseball/` |
| NBA | 30 | `basketball/` | `data/basketball/` |
| NHL | 32 | `hockey/` | `data/hockey/` |
| NFL | 32 | `american-football/` | `data/american-football/` |

Each image folder has `competitions/north-america/<league>.png` and
`teams/<country>/<id>.png`. `american-football` keeps the NFL apart from
association football in `football/`. Here `country` is where the team is based:
`CA` for the Toronto Blue Jays, the Toronto Raptors and the seven Canadian NHL
teams, `US` for everyone else. The leagues themselves have `country: null`.

`teams.json` has `version` and a `teams` list:

```json
{
  "id": "toronto-raptors",
  "name": "Toronto Raptors",
  "aliases": ["Raptors"],
  "abbreviation": "TOR",
  "espn_id": 28,
  "country": "CA",
  "league": "nba",
  "conference": "Eastern",
  "division": "Atlantic",
  "logo": "basketball/teams/ca/toronto-raptors.png"
}
```

- **MLB** teams have `mlb_id` (the official MLB Stats API id) and `division`
  (`AL East`, `AL Central`, `AL West`, `NL East`, `NL Central`, `NL West`), with
  no `conference`.
- **NBA, NHL and NFL** teams have `espn_id` (ESPN's id, not an official league
  id), `conference` (`Eastern` / `Western` for NBA and NHL, `AFC` / `NFC` for the
  NFL) and `division` without the conference name.
- **Abbreviations are indexed**, so `"NYY"`, `"GSW"` or `"KC"` resolve directly.
- **Old names resolve to the current logo**, not to a historical one. The
  current MLB name is `Athletics`; `Oakland Athletics`, `OAK` and `A's` are
  aliases of the same team.

Logos come from ESPN (500 px before trimming, never upscaled). Names, ids and
divisions were checked on 30 October 2026 against the MLB Stats API and the
official [NBA](https://www.nba.com/teams), [NHL](https://www.nhl.com/info/teams/)
and [NFL](https://www.nfl.com/teams/) directories: 2026 for MLB and NFL,
2026-27 for NBA and NHL.

## UFC

`scripts/download_ufc_fighters.py` searches Wikimedia Commons for reusable
fighter photos, saves them to `ufc/fighters/`, records author, license and
source in `data/sources.json`, and rebuilds the indexes. The file extension
depends on the image found, so read the exact path from `data/fighters.json`.

```bash
python scripts/download_ufc_fighters.py --limit 5                         # try five fighters
python scripts/download_ufc_fighters.py                                   # the full starter list of 30
python scripts/download_ufc_fighters.py --fighter "Ilia Topuria"          # one fighter
python scripts/download_ufc_fighters.py --fighter "Ilia Topuria" --dry-run  # show the pick, download nothing
python scripts/download_ufc_fighters.py --fighter "Ilia Topuria" --force    # replace an existing image
```

The search is automatic and may pick a photo whose license is fine but that
isn't the best portrait for a graphic, so review the results by eye.

## Repository layout

```text
sports-assets/
├── football/
│   ├── competitions/<continent>/<id>.png
│   ├── clubs/<country>/<id>.png        # es, gb-eng, pt…
│   └── collages/
├── baseball/       competitions/, teams/<country>/
├── basketball/     competitions/, teams/<country>/
├── hockey/         competitions/, teams/<country>/
├── american-football/  competitions/, teams/us/
├── ufc/
│   ├── fighters/
│   └── logos/
├── data/
│   ├── football/
│   │   ├── competitions.json          # catalog (source of truth, edited by hand)
│   │   ├── competitions-lookup.json   # generated: normalized name → id
│   │   ├── clubs.json                 # club catalog (updated by sync_clubs.py)
│   │   ├── clubs-mapping.json         # reviewed club → crest matches
│   │   ├── rosters.json               # Americas clubs per league and season (by hand)
│   │   ├── clubs-lookup.json          # generated: country → normalized name → id
│   │   └── domestic-coverage.json     # league and cup audit, including qualifiers
│   ├── baseball/ basketball/ hockey/ american-football/
│   │   ├── competitions.json, teams.json              # catalogs
│   │   └── competitions-lookup.json, teams-lookup.json  # generated
│   ├── fighters.json
│   ├── ufc-logos.json
│   ├── ufc-fighters-seed.json
│   ├── all-assets.json                # generated: every asset with an image
│   └── sources.json                   # origin and license of every image
├── scripts/
└── tests/
```

File names use lowercase letters, digits and hyphens only: no spaces, accents
or special characters.

## Contributing

Install the dependencies once:

```bash
pip install -r requirements.txt
```

After any change, review new images by eye, then run:

```bash
python scripts/build_index.py              # regenerate lookups and all-assets.json
python -m unittest discover -s tests
python scripts/validate_assets.py
```

Validation fails if a catalog points to a missing file, an image has no catalog
entry, a logo isn't transparent or is larger than 1024 px, two entries share an
id or an alias (within a country or league), or a club or team points to a
league or division that doesn't exist. CI runs the same validation on every
pull request.

### Add a missing alias

If a name from your data source doesn't resolve, add it to `aliases` of the
right entry in the catalog (`competitions.json`, `clubs.json` or `teams.json`)
and run `python scripts/build_index.py`. Validation will reject it if it
collides with another entry.

### Add or replace a football logo or crest

Look in logo repositories first (for example
[football-logos](https://github.com/Leo4815162342/football-logos)), then
Wikipedia / Wikimedia Commons. Reject anything with a watermark or an opaque
background.

```bash
python scripts/normalize_logo.py download.png football/competitions/europe/laliga.png
```

Then set `logo` in the catalog, record the origin in `data/sources.json`, and
run `python scripts/build_index.py`. For a club in the cup audit, also update
`missing_logos` in `data/football/domestic-coverage.json`.

### Update football clubs for a new season

```bash
python scripts/sync_clubs.py plan      # propose crests for new clubs, write .cache/clubs/review-*.jpg
python scripts/sync_clubs.py accept    # copy the proposals into data/football/clubs-mapping.json
# review the contact sheets and fix wrong matches in clubs-mapping.json
python scripts/sync_clubs.py apply     # download crests, update clubs.json and each club's league, rebuild indexes
```

`apply` never overwrites existing crests, or names and aliases edited by hand
in `clubs.json`.

For the Americas, add the new season of each league to
`data/football/rosters.json` before running `plan`:

```json
"liga-mx": {
  "2026-27": ["América", "Atlas", "..."]
}
```

- Seasons are `YYYY` for calendar-year leagues and `YYYY-YY` for Liga MX,
  Costa Rica and Guatemala (Apertura and Clausura together). The latest season
  is the current one.
- Use the club name as written on English Wikipedia, spelled the same way in
  every season.
- If football-logos.cc has no crest, set `"source": "url"` in
  `clubs-mapping.json` with the https URL of a PNG from Wikipedia / Wikimedia,
  or `"source": "none"` if there isn't one.

### Update MLB, NBA, NHL or NFL

1. Check names, aliases, conferences and divisions in `teams.json` against the
   official league directory. Keep published ids and add old names as aliases.
2. Check the logo URLs in `data/sources.json` before changing them.
3. Download missing logos. The scripts normalize the images, record the date
   and rebuild the indexes, and reject an invalid catalog before downloading.
   Add `--force` to replace every logo of that league from the reviewed URLs.

   ```bash
   python scripts/sync_mlb.py
   python scripts/sync_league.py nba
   python scripts/sync_league.py nhl
   python scripts/sync_league.py nfl
   ```

For metadata-only changes, `python scripts/build_index.py` is enough.

## Licensing

The MIT license in `LICENSE-CODE` covers the code, scripts and original
documentation only. Logos, crests, trademarks and fighter photos belong to
their owners, and downloading them here does not grant a license to
redistribute them. `data/sources.json` records where every image came from and
any license or attribution information available. Check the source page and
terms of each asset before redistributing it or using it commercially. See
`ASSETS-LICENSE.md`.
