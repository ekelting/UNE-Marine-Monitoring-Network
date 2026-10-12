# 🌊 UNE Marine Monitoring Network

**Live website:** <https://ekelting.github.io/UNE-Marine-Monitoring-Network/>

This is the public website for the University of New England's coastal monitoring network: buoys in Saco Bay and along the southern Maine coast, plus weather, salt-marsh and pond stations. It is one repository and one website. The home page shows every station on one map, and each station has its own detailed page with a plain-language "What do these numbers mean?" guide. Everything updates automatically every hour.

| Buoy | Type | Page | Data and settings |
|---|---|---|---|
| Camp Ellis | Wave (Sofar Spotter SPOT-32787C) | [/camp-ellis/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/camp-ellis/) | [`buoys/camp-ellis`](buoys/camp-ellis) |
| Biddeford Pool | Wave (Sofar Spotter SPOT-32905C) | [/biddeford-pool/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/biddeford-pool/) | [`buoys/biddeford-pool`](buoys/biddeford-pool) |
| Ram Island Radar | Wave radar (SeaSignals X-band, CUMULUS 12579) | [/ram-island-radar/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/ram-island-radar/) | [`buoys/ram-island-radar`](buoys/ram-island-radar) |
| Wood Island | Water quality (BlueSonde BB1.23) | [/wood-island/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/wood-island/) | [`buoys/wood-island`](buoys/wood-island) |
| Jordan Point | Water quality (BlueSonde BB1.12) | [/jordan-point/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/jordan-point/) | [`buoys/jordan-point`](buoys/jordan-point) |
| Ferry Beach | Water quality (BlueSonde BB1.47) | [/ferry-beach/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/ferry-beach/) | [`buoys/ferry-beach`](buoys/ferry-beach) |
| Goose Rocks Beach | Water quality (BlueSonde BB1.48) | [/goose-rocks-beach/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/goose-rocks-beach/) | [`buoys/goose-rocks-beach`](buoys/goose-rocks-beach) |
| Fathom Buoy | Fish-tag receiver buoy + water sensors (temp, salinity, oxygen, CDOM), May–Sep 2026 | [/fathom-buoy/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/fathom-buoy/) | [`buoys/fathom-buoy`](buoys/fathom-buoy) |
| Ram Island | Coastal weather station | [/ram-island/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/ram-island/) | [`buoys/ram-island`](buoys/ram-island) |
| 363 Acre Woods | Forest weather + soil station | [/une-363-woods/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/une-363-woods/) | [`buoys/une-363-woods`](buoys/une-363-woods) |
| Biddeford Pool Marsh | Salt-marsh water + weather station | [/biddeford-pool-marsh/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/biddeford-pool-marsh/) | [`buoys/biddeford-pool-marsh`](buoys/biddeford-pool-marsh) |
| Great Pond | Pond water-quality station | [/great-pond/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/great-pond/) | [`buoys/great-pond`](buoys/great-pond) |

## Using the data

- **Downloads:** every buoy page has buttons for a spreadsheet and CSV files.
- **A Google Sheet that stays current:** type this into any cell, with the buoy's name in the address:
  ```
  =IMPORTDATA("https://ekelting.github.io/UNE-Marine-Monitoring-Network/wood-island/data/daily.csv")
  ```
- **Raw readings:** these live in `buoys/<buoy>/data/`, in UTC.
- **Latest values as JSON:** `https://ekelting.github.io/UNE-Marine-Monitoring-Network/<buoy>/data/latest.json` gives the latest values plus the last 14 days, hourly.

## How it works

- **Every hour,** [`.github/workflows/update.yml`](.github/workflows/update.yml) runs:
  1. One job per buoy, in parallel, fetches new data and commits it to `buoys/<buoy>/data/`. Wave buoys come from Sofar's API, using the `SOFAR_API_TOKEN` secret. BlueSondes come from the public CUMULUS (Coastal Measures) sensor pages and need no key. Weather, marsh and pond stations come from the public UNE monitoring data service on ArcGIS (the same data behind UNE's ArcGIS dashboards), which needs no key either. The complete raw archive is on [UNE Box](https://une.app.box.com/s/6gm2pq078kwrdsxzy94zenltzu4gppmy). If one buoy has trouble, the others still update.
  2. One job then builds every page with [`tools/build_all.py`](tools/build_all.py) and publishes the site.
- **Code:**
  - [`wave/`](wave) builds the Sofar Spotter dashboards.
  - [`sonde/`](sonde) builds the BlueSonde dashboards.
  - [`radar/`](radar) measures each hourly radar scan from CUMULUS (sea sparkle, boats, whitewater, experimental wave period) and builds the radar page. Images are downloaded fresh each hour and not stored. Offline test: `python radar/tests/run_offline.py`.
  - [`station/`](station) builds the weather, marsh and pond station pages. Each station's measurements are described in its `site.json` (`vars`).
  - [`shared/explain.py`](shared/explain.py) holds the plain-language explanation of every measurement, used on every page.
  - [`shared/mapjs.py`](shared/mapjs.py) is the map with buoy icons, used by both.
  - [`web/index.html`](web/index.html) is the network home page. It reads each buoy's `latest.json` in the browser.
- **Settings:** each buoy has `buoys/<buoy>/site.json`. It holds the device ID, name, location, tide station, and the links to the other buoys.

## Adding a buoy

1. Create `buoys/<new-slug>/site.json`. Copy one from a buoy of the same kind and change the device ID (`spotter_id` or `device_uuid`), the names, and the latitude and longitude.
2. Add the new buoy to [`buoys.json`](buoys.json) and to `SITES` in [`web/index.html`](web/index.html).
3. Add it to `sister_sites` in the other buoys' `site.json` files, so their maps and buttons show it.
4. Commit. The workflow runs, creates the buoy's data folder on its first fetch, and the page appears.

## History

The two wave buoys started in their own repositories (`UNE-Camp-Ellis-SPOT-32787C`, `UNE-Biddeford-Pool-SPOT-32905C`). Those repositories are kept as archives, and their old web addresses forward here. The BlueSonde buoys briefly had their own repositories too. Their full data history was copied here on October 12, 2026. Old page addresses (for example `/saco-bay/` and `/saco-river-estuary/`) forward to the current ones; they are listed as `aliases` in `buoys.json`.

Data: Sofar Ocean (wave buoys), BlueSonde via CUMULUS / Coastal Measures (water quality), NOAA (tide predictions). University of New England.
