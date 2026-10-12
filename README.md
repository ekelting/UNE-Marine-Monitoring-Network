# 🌊 UNE Marine Monitoring Network

**Live dashboard:** <https://ekelting.github.io/UNE-Marine-Monitoring-Network/>

This page shows all of the University of New England's buoys in Saco Bay and along the southern Maine coast on one page:

- a map of every buoy, with drawn buoy icons and live values on the labels (switch between street map and NOAA nautical chart)
- headline numbers across the network: the water-temperature range, the biggest waves, the freshest water, the lowest oxygen
- a card for each buoy with its latest readings, a 7-day sparkline, and a link to its full dashboard
- charts comparing the last two weeks of water temperature, salinity, dissolved oxygen and wave height
- the top findings from each buoy's own dashboard

## How it works

Each buoy has its own repository that rebuilds every hour and publishes a small `data/latest.json` (latest values plus the last 14 days hourly). This page is a single static `index.html` that reads those files in the browser every time it loads, and again every 10 minutes. It has no build step and no data of its own.

| Buoy | Type | Dashboard |
|---|---|---|
| Camp Ellis | Wave (Sofar Spotter SPOT-32787C) | <https://ekelting.github.io/UNE-Camp-Ellis-SPOT-32787C/> |
| Biddeford Pool | Wave (Sofar Spotter SPOT-32905C) | <https://ekelting.github.io/UNE-Biddeford-Pool-SPOT-32905C/> |
| Saco Bay | Water quality (BlueSonde BB1.23) | <https://ekelting.github.io/UNE-BlueSonde-BB1.23/> |
| Saco River Estuary | Water quality (BlueSonde BB1.12) | <https://ekelting.github.io/UNE-BlueSonde-BB1.12/> |
| Ferry Beach | Water quality (BlueSonde BB1.47) | <https://ekelting.github.io/UNE-BlueSonde-BB1.47/> |
| Goose Rocks Beach | Water quality (BlueSonde BB1.48) | <https://ekelting.github.io/UNE-BlueSonde-BB1.48/> |

**Adding a buoy:** add one line to the `SITES` list near the top of the script in `index.html`. Give its repo name, display name, kind (`wave` or `wq`), latitude, longitude, and a colour.
