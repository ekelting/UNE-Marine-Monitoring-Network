# 🌊 UNE Marine Monitoring Network

**Live website:** <https://ekelting.github.io/UNE-Marine-Monitoring-Network/>

This is the public website for the University of New England's buoys in Saco Bay and along the southern Maine coast. It is one repository and one website. The home page shows all buoys on one map, and each buoy has its own detailed page. Everything updates automatically every hour.

| Buoy | Type | Page | Data and settings |
|---|---|---|---|
| Camp Ellis | Wave (Sofar Spotter SPOT-32787C) | [/camp-ellis/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/camp-ellis/) | [`buoys/camp-ellis`](buoys/camp-ellis) |
| Biddeford Pool | Wave (Sofar Spotter SPOT-32905C) | [/biddeford-pool/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/biddeford-pool/) | [`buoys/biddeford-pool`](buoys/biddeford-pool) |
| Saco Bay | Water quality (BlueSonde BB1.23) | [/saco-bay/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/saco-bay/) | [`buoys/saco-bay`](buoys/saco-bay) |
| Saco River Estuary | Water quality (BlueSonde BB1.12) | [/saco-river-estuary/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/saco-river-estuary/) | [`buoys/saco-river-estuary`](buoys/saco-river-estuary) |
| Ferry Beach | Water quality (BlueSonde BB1.47) | [/ferry-beach/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/ferry-beach/) | [`buoys/ferry-beach`](buoys/ferry-beach) |
| Goose Rocks Beach | Water quality (BlueSonde BB1.48) | [/goose-rocks-beach/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/goose-rocks-beach/) | [`buoys/goose-rocks-beach`](buoys/goose-rocks-beach) |

## Using the data

- **Downloads:** every buoy page has buttons for a spreadsheet and CSV files.
- **A Google Sheet that stays current:** type this into any cell, with the buoy's name in the address:
  ```
  =IMPORTDATA("https://ekelting.github.io/UNE-Marine-Monitoring-Network/saco-bay/data/daily.csv")
  ```
- **Raw readings:** these live in `buoys/<buoy>/data/`, in UTC.
- **Latest values as JSON:** `https://ekelting.github.io/UNE-Marine-Monitoring-Network/<buoy>/data/latest.json` gives the latest values plus the last 14 days, hourly.

## How it works

- **Every hour,** [`.github/workflows/update.yml`](.github/workflows/update.yml) runs:
  1. One job per buoy, in parallel, fetches new data and commits it to `buoys/<buoy>/data/`. Wave buoys come from Sofar's API, using the `SOFAR_API_TOKEN` secret. BlueSondes come from the public CUMULUS (Coastal Measures) sensor pages and need no key. If one buoy has trouble, the others still update.
  2. One job then builds every page with [`tools/build_all.py`](tools/build_all.py) and publishes the site.
- **Code:**
  - [`wave/`](wave) builds the Sofar Spotter dashboards.
  - [`sonde/`](sonde) builds the BlueSonde dashboards.
  - [`shared/mapjs.py`](shared/mapjs.py) is the map with buoy icons, used by both.
  - [`web/index.html`](web/index.html) is the network home page. It reads each buoy's `latest.json` in the browser.
- **Settings:** each buoy has `buoys/<buoy>/site.json`. It holds the device ID, name, location, tide station, and the links to the other buoys.

## Adding a buoy

1. Create `buoys/<new-slug>/site.json`. Copy one from a buoy of the same kind and change the device ID (`spotter_id` or `device_uuid`), the names, and the latitude and longitude.
2. Add the new buoy to [`buoys.json`](buoys.json) and to `SITES` in [`web/index.html`](web/index.html).
3. Add it to `sister_sites` in the other buoys' `site.json` files, so their maps and buttons show it.
4. Commit. The workflow runs, creates the buoy's data folder on its first fetch, and the page appears.

## History

Each buoy started in its own repository (`UNE-Camp-Ellis-SPOT-32787C`, `UNE-Biddeford-Pool-SPOT-32905C`, `UNE-BlueSonde-BB1.xx`). On its first run here, each buoy's full data history was copied from its old repository. The old repositories now redirect to this site and are archived.

Data: Sofar Ocean (wave buoys), BlueSonde via CUMULUS / Coastal Measures (water quality), NOAA (tide predictions). University of New England.
