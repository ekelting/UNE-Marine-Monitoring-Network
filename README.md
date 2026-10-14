# 🌊 UNE Marine Monitoring Network

**Live website: <https://ekelting.github.io/UNE-Marine-Monitoring-Network/>**

The University of New England (UNE) School of Marine and Environmental Programs runs instruments in the water, along the shore and on land around Saco Bay and Biddeford, Maine. This website brings them together. It shows what the ocean, the air, the marsh and the pond are doing right now, how that compares with the rest of the year, and what the numbers mean. You don't need a science background to use it.

Every page updates itself **every hour**, and anyone can see it or download the data. Nothing here requires an account.

## What's on the website

The **home page** shows every station on one map, the headline numbers for the whole area, and charts comparing the stations over the last two weeks. Click any station for its own page.

| Station | What it measures | Page |
|---|---|---|
| 🌊 **Camp Ellis** wave buoy | Waves (height, rhythm, direction), storms, wave energy; water temperature, oxygen and currents below the buoy | [/camp-ellis/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/camp-ellis/) |
| 🌊 **Biddeford Pool** wave buoy | Waves, storms, wave energy; water temperature and currents below the buoy | [/biddeford-pool/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/biddeford-pool/) |
| 📡 **Ram Island Radar** | An X-band radar that films the sea surface every hour: how rough it looks, breaking waves, boat traffic, and a wave-rhythm estimate | [/ram-island-radar/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/ram-island-radar/) |
| 💧 **Wood Island** water-quality buoy | Temperature, salinity, oxygen, chlorophyll (algae), turbidity | [/wood-island/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/wood-island/) |
| 💧 **Jordan Point** water-quality buoy (Saco River estuary) | Temperature, salinity, oxygen, chlorophyll, turbidity | [/jordan-point/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/jordan-point/) |
| 💧 **Ferry Beach** water-quality buoy | Temperature, salinity, oxygen, tryptophan (a pollution early-warning signal), turbidity | [/ferry-beach/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/ferry-beach/) |
| 💧 **Goose Rocks Beach** water-quality buoy | Temperature, salinity, oxygen, tryptophan, turbidity | [/goose-rocks-beach/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/goose-rocks-beach/) |
| 🐟 **Fathom Buoy** | A fish-tag receiver buoy with water sensors: temperature, salinity, oxygen, CDOM. **Currently offline** (out of the water for repairs); its May–September 2026 season is on its page | [/fathom-buoy/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/fathom-buoy/) |
| 🌦️ **Ram Island** weather station | Air temperature, humidity, wind, rain, sunlight | [/ram-island/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/ram-island/) |
| 🌲 **363 Acre Woods** station | Forest weather, plus soil temperature and moisture at several depths | [/une-363-woods/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/une-363-woods/) |
| 🌾 **Biddeford Pool Marsh** | Salt-marsh water level and temperature, plus air temperature, humidity and pressure | [/biddeford-pool-marsh/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/biddeford-pool-marsh/) |
| 🏞️ **Great Pond** | Pond oxygen, salinity, temperature, water level, rain | [/great-pond/](https://ekelting.github.io/UNE-Marine-Monitoring-Network/great-pond/) |

Every station page has:
- **the latest readings**, with an ⓘ on each box explaining it
- **a map** (street map or NOAA nautical chart) showing the other stations nearby
- **"What the data says"**: plain-English findings written automatically from the numbers
- **"What do these numbers mean?"**: a short guide to every measurement, with what's typical at that station
- **charts** of every reading, day-by-day summaries, a month-by-month table, and downloads

Use the **Units** switch (Metric / Imperial) and the **Theme** switch (Light / Dark) at the top of any page. Your choice is remembered across the site.

## Getting the data

- **Download buttons** on each page give a spreadsheet (.xlsx) and CSV files (hourly, daily, monthly, and for most stations every reading).
- **A Google Sheet that stays up to date:** type this into any cell, using the station's name from the table above (for example `camp-ellis` or `great-pond`):
  ```
  =IMPORTDATA("https://ekelting.github.io/UNE-Marine-Monitoring-Network/great-pond/data/daily.csv")
  ```
- **Latest values as JSON**, for programmers: `https://ekelting.github.io/UNE-Marine-Monitoring-Network/<station>/data/latest.json`. It holds the newest readings plus the last 14 days, hourly.
- **Raw readings** are kept in this repository under [`buoys/<station>/data/`](buoys), with times in UTC.
- **The complete raw archive** for all stations (one file per day) is on [UNE Box](https://une.app.box.com/s/6gm2pq078kwrdsxzy94zenltzu4gppmy).

Times on the website and in the downloads are US Eastern.

## Where the data comes from

- **Wave buoys:** Sofar Ocean Spotter buoys, through Sofar's data service.
- **Water-quality buoys and the radar:** BlueSonde buoys and a SeaSignals X-band radar, through the public [CUMULUS](https://cumulus.coastalmeasures.com/publicdata?lat=43.44875&lng=-70.36031&zoom=11.93) sensor pages (Coastal Measures).
- **Weather, marsh, pond and Fathom stations:** UNE's monitoring data service on ArcGIS, the same data behind [UNE's Marine and Environmental Monitoring dashboard](https://www.arcgis.com/apps/dashboards/68aa206f217b4325ae0a44372a1d73f0).
- **Tide predictions:** NOAA, station 8418606 (Camp Ellis, Saco River entrance).

## Data quality: please read before using the numbers

These are live, automatically processed readings, not a reviewed scientific dataset. Each page lists exactly what was cleaned. In short:

- Impossible values and single-reading spikes are removed.
- Water-quality readings taken while a sonde was out of the water are dropped. So are Fathom buoy readings taken away from its moorings.
- Optical sensors (chlorophyll, turbidity, tryptophan, CDOM) can drift as marine growth builds up between cleanings.
- The tryptophan sensors are not calibrated to an absolute scale, so compare their readings with each other, not with published thresholds.
- Wind on the wave-buoy pages is estimated from the shape of the waves, not measured.

Not for navigation. For research use, please contact us (below) about the reviewed data.

## Contact

| Who | For |
|---|---|
| **Dr. Will Kochtitzky**: [wkochtitzky@une.edu](mailto:wkochtitzky@une.edu) | The UNE monitoring network, the weather, marsh and pond stations, and the data archive |
| **Dr. Tricia Thibodeau**: [pthibodeau1@une.edu](mailto:pthibodeau1@une.edu) | The Fathom buoy |
| **Dr. Emily Kelting**: [ekelting@une.edu](mailto:ekelting@une.edu) | This website and its dashboards |

University of New England, School of Marine and Environmental Programs, Biddeford, Maine.

---

## For maintainers

**How it updates:** [`.github/workflows/update.yml`](.github/workflows/update.yml) runs every hour.
1. One job per station runs in parallel and fetches new data.
2. One job saves all of the new data in a single commit, builds every page with [`tools/build_all.py`](tools/build_all.py), and publishes the site with GitHub Pages.

If one station has trouble, the others still update. The wave buoys need the `SOFAR_API_TOKEN` secret; everything else is public.

**Code**

| Folder | What it builds |
|---|---|
| [`wave/`](wave) | Sofar Spotter wave-buoy pages |
| [`sonde/`](sonde) | BlueSonde water-quality pages |
| [`radar/`](radar) | The radar page; offline test: `python radar/tests/run_offline.py` |
| [`station/`](station) | Weather, marsh, pond and Fathom pages; each station's measurements are listed in its `site.json` under `vars` |
| [`shared/mapjs.py`](shared/mapjs.py) | The map, station icons and navigation buttons |
| [`shared/explain.py`](shared/explain.py) | The "What do these numbers mean?" text |
| [`web/index.html`](web/index.html) | The home page; it reads each station's `latest.json` in the browser |

**Settings:** each station has its own `buoys/<station>/site.json` (device ID, names, location, links to the other stations). [`buoys.json`](buoys.json) lists every station.

**Adding a station**
1. Create `buoys/<new-name>/site.json`. Copy one from a station of the same kind and change the device ID, names and location.
2. Add it to `buoys.json` and to `SITES` in `web/index.html`.
3. Add it to `sister_sites` in the other stations' `site.json`, so maps and buttons show it.
4. Commit. The next hourly run creates its data folder and page.

**Renaming a station:** change the names in its `site.json` and in `web/index.html`. To change its web address as well, rename its folder, update the name in `buoys.json`, and add the old name to that station's `aliases` so old links keep working.

**History:** the Camp Ellis and Biddeford Pool buoys first had their own repositories (`UNE-Camp-Ellis-SPOT-32787C`, `UNE-Biddeford-Pool-SPOT-32905C`). They are kept as archives, and their old web addresses forward here.
