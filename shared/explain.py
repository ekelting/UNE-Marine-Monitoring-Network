"""
explain.py — plain-language explanations of every measurement on the UNE monitoring pages,
written for visitors who are not oceanographers or meteorologists. Shared by the wave-buoy,
water-quality-buoy and weather/environmental-station pages.

Each entry: key → (emoji, name, what it is, why it matters, how to read the number)
"""
import html

E = {
    # ---------------- water ----------------
    'water_temp': ('🌡️', 'Water temperature',
                   'How warm or cold the water is, measured by a sensor just below the surface.',
                   'Temperature controls almost everything in the water: how much oxygen it can hold, how fast algae grow, '
                   'which fish and shellfish are comfortable, and when lobsters and other animals move or molt.',
                   'Gulf of Maine coastal water runs roughly 38–45 °F (3–7 °C) in late winter and 60–68 °F (15–20 °C) in late summer. '
                   'Shallow ponds and marshes swing much more, warming fast on sunny days.'),
    'salinity': ('💧', 'Salinity (how salty)',
                 'The amount of dissolved salt in the water, in PSU (practical salinity units) — about the same as grams of salt '
                 'per kilogram of water.',
                 'Saltiness tells you where the water came from. Fresh water from rain, streams, rivers or groundwater lowers it; '
                 'ocean water raises it. Many plants and animals can only live within a certain salt range.',
                 'Drinking water ≈ 0. Brackish (mixed) water ≈ 5–18. Open Gulf of Maine ≈ 31–33. Sudden drops usually follow heavy rain.'),
    'do': ('🫧', 'Dissolved oxygen',
           'Oxygen gas dissolved in the water — the oxygen that fish, crabs, clams and worms breathe through their gills or skin. '
           'Shown in mg/L (milligrams per litre), and sometimes as % saturation: 100% means the water holds as much oxygen as it '
           'naturally can at that temperature and saltiness.',
           'Low oxygen stresses or kills marine life. It drops when water is warm, still, or full of decaying plant material, '
           'and it swings up and down every day because algae make oxygen in sunlight and everything uses it up at night.',
           'Above 5 mg/L: healthy. 2–5 mg/L: stressful for many species. Below 2 mg/L: hypoxic — most fish leave or die. '
           'Saturation above 100% means algae are photosynthesising hard.'),
    'chl': ('🌿', 'Chlorophyll',
            'The green pigment inside microscopic floating algae (phytoplankton). The sensor shines blue light into the water and '
            'measures how much the chlorophyll glows back. Units: µg/L (micrograms per litre).',
            'Phytoplankton are the base of the ocean food web — and they make about half of the oxygen on Earth. Too much, though, '
            'can mean a bloom that later uses up oxygen as it decays, and a few kinds of algae are toxic.',
            'Under ~2 µg/L: clear, low-algae water. 2–10: normal coastal levels. Above ~10: bloom conditions.'),
    'trp': ('🔬', 'Tryptophan (pollution early-warning)',
            'Tryptophan is one of the building blocks of proteins. It glows under ultraviolet light, and the sensor measures that glow. '
            'It is abundant in sewage, septic-system leaks, animal waste and freshly decaying plant and animal matter.',
            'A rise in tryptophan signal is an early warning that wastewater or other organic pollution may be reaching the water — '
            'often before bacteria tests come back from a lab. It helps decide when to check shellfish beds or swimming beaches.',
            'Watch for changes, not the number itself: these sensors are not calibrated to an absolute scale (they can even read below '
            'zero). A sharp rise above the usual level, especially after rain, is the thing to notice.'),
    'cdom': ('🍵', 'CDOM (coloured dissolved organic matter)',
             'The "tea" in the water: dissolved bits of decaying leaves, marsh grass and soil that tint water yellow-brown. The sensor '
             'measures how much it glows under ultraviolet light, in ppb (parts per billion, quinine-sulfate equivalents).',
             'CDOM mostly comes from land — rivers, marshes and runoff — so it is a handy tracer of fresh water reaching the bay. It also '
             'soaks up sunlight (including UV), shading seaweed and plankton below.',
             'Low single digits: clear ocean water. Tens: noticeable land or marsh influence. It usually rises when salinity drops.'),
    'turb': ('🟤', 'Turbidity (cloudiness)',
             'How cloudy the water is, from mud, sand, algae or other particles. The sensor measures how much light scatters off '
             'them, in NTU (nephelometric turbidity units).',
             'Cloudy water blocks sunlight from reaching seagrass and seaweed, can clog the gills of shellfish, and often carries '
             'pollutants stirred up by storms or washed off the land.',
             'Under ~5 NTU: clear. 5–20: a little cloudy. 20–100: murky (storm waves, runoff). Single sharp spikes are often something '
             'drifting past the sensor.'),
    'cond': ('⚡', 'Conductivity',
             'How easily electricity passes through the water. Dissolved salt carries the current, so conductivity is how the sensor '
             'measures salinity. "Specific" conductivity is adjusted to 25 °C so readings can be compared.',
             'It is the raw measurement behind the salinity number, and a quick check that the sensor is underwater — '
             'it drops to about zero in air.',
             'Seawater ≈ 50,000 µS/cm (50 mS/cm). Fresh river water ≈ 50–500 µS/cm.'),
    'tide': ('🌙', 'Tide / water level',
             'The height of the water surface. Along the Maine coast the sea rises and falls about 9 feet twice a day (every ~12 h 25 min), '
             'pulled by the Moon and Sun.',
             'The tide moves water — and everything in it — back and forth past a sensor, so many readings change with the tide. '
             'In marshes and ponds, water level shows how often the tide floods in and how high storms push it.',
             'Heights on tide charts are measured above average low tide (MLLW). Storms and strong onshore winds can push water higher than predicted.'),
    # ---------------- waves ----------------
    'wave_height': ('🌊', 'Wave height',
                    '"Significant wave height": the average height of the biggest third of the waves, trough to crest. It is close to what '
                    'an experienced sailor would estimate by eye.',
                    'Wave height drives beach erosion, coastal flooding and safe boating. A few big storms each year do most of the work of '
                    'moving sand along the coast.',
                    'Under 1 ft: calm. 1–3 ft: normal. Over 3 ft (1 m) for hours: a storm event here. Single waves can be about twice the '
                    'significant height.'),
    'wave_period': ('⏱️', 'Wave period (rhythm)',
                    'Seconds between one wave crest and the next.',
                    'Short-period waves (under ~6 s) are choppy and made by local wind. Long-period swell (10 s or more) was made by a distant '
                    'storm, carries much more energy for its height, and reaches farther up the beach.',
                    'Tip: count the seconds between waves at the beach — that is the period.'),
    'wave_dir': ('🧭', 'Wave direction',
                 'The compass direction the waves are coming from (like wind direction).',
                 'Direction decides which beaches take the hit and which way sand is pushed along the shore.',
                 '"E" means waves rolling in from the east.'),
    'wave_energy': ('⚡', 'Wave energy',
                    'How much energy the waves carry toward shore, per metre (or foot) of coastline. It grows with the square of wave height '
                    'and with the period.',
                    'It is the best single measure of how hard the ocean is working on the coast — useful for erosion studies.',
                    '1 kWh ≈ running a microwave for an hour.'),
    'pressure': ('🌬️', 'Air pressure',
                 'The weight of the air above, in hPa (hectopascals) or kPa (1 kPa = 10 hPa).',
                 'Falling pressure usually means a storm or front is coming; rising pressure means clearing weather. Very low pressure also '
                 'lets the sea rise a little higher (storm surge).',
                 '~1013 hPa (101.3 kPa) is average. Under ~1000 hPa usually means a storm.'),
    'current': ('🌀', 'Current',
                'How fast and in which direction the water itself is moving, measured below the buoy.',
                'Currents carry larvae, nutrients, sediment and pollution, and matter for swimmers and boaters.',
                'Tidal currents here typically reach a few tenths of a knot; 10 cm/s ≈ 0.2 knots.'),
    # ---------------- wave radar ----------------
    'radar_scan': ('📡', 'Scans and sweeps',
                   'The radar antenna spins about once every 1.3 seconds; each turn is one "sweep" — a single radar picture of everything '
                   'within about 2.7 km (1.7 miles). About once an hour the radar records a "scan": roughly 229 sweeps in a row, a 5-minute movie '
                   'of the sea surface.',
                   'Watching the same water for 5 minutes lets the radar tell what stays still (land, rocks, moorings) from what moves (waves, '
                   'breaking surf, boats) — day or night, in fog or rain.',
                   'One scan ≈ every hour. Gaps in the "Radar diary" chart mean the radar was offline or being serviced.'),
    'radar_rough': ('🌬️', 'Surface roughness (radar echo)',
                    'The share of nearby open water (300–1,500 m from the radar) that bounces the radar signal back on a typical sweep. '
                    'The radar\'s microwaves are about 3 cm long — the size of tiny wind ripples. Ripples scatter the signal back to the radar, so '
                    'rough, wind-blown water shows up bright; flat, glassy water reflects the signal away like a mirror and looks dark.',
                    'It shows how wind-roughened the whole bay surface is, not just one spot — a picture between the buoys, at night and in fog. '
                    'It rises with wind first, and with waves as they build.',
                    'Shown as a rank against every scan this radar has taken: Glassy (calmest 15%), Gentle, Choppy, Rough, Wild (roughest 10%). '
                    'The raw % depends on the radar\'s settings, so only compare it with this radar — and it is not a wave height.'),
    'radar_motion': ('🎨', 'Motion',
                     'How much each spot\'s radar echo changes during the 5-minute scan. Moving water flickers constantly; land and rocks barely change.',
                     'Motion is how the radar maps where the water is active, and it feeds the "Zones" map and the whitewater measurement.',
                     'On the Motion map, warm colours = lots of change (waves, surf, boats); cool or clear = steady (land, sheltered water).'),
    'radar_zones': ('🗺️', 'Zones',
                    'SeaSignals sorts every spot the radar can see into land, open sea, "active" water (bright and moving — like breaking waves), '
                    'and shadow (places hidden behind islands or the shore, which the radar cannot see).',
                    'The zones decide which pixels count as "open water" for surface roughness and which count as breaking water near the shore.',
                    'Shadows are normal: radar travels in straight lines, so it cannot see behind Ram Island or headlands.'),
    'radar_white': ('💥', 'Whitewater',
                    'The area of "active" water within 150 m (500 ft) of the shoreline — mostly breaking, churning surf. Shown in square metres or '
                    'square feet.',
                    'Breaking waves are what move sand and erode beaches and dunes, so more whitewater along the shore means more work being done on the coast. '
                    'It also tracks surf conditions.',
                    'Rises with wave height and changes with the tide: some sandbars and ledges only break at low water. Boat wakes near shore can add a little.'),
    'radar_boats': ('🚤', 'Moving targets (boats)',
                    'Things the radar followed from sweep to sweep during a scan — usually boats. Speed is in knots (1 knot ≈ 1.15 mph ≈ 0.51 m/s).',
                    'Shows how busy the bay is, when, and along which routes ("boat highways").',
                    'The tracker is automatic, so a track is "probably a boat": occasionally a bird flock, a big wave crest or a buoy swinging on its mooring.'),
    'radar_rhythm': ('🎵', 'Wave rhythm from radar (experimental)',
                     'When the sea is rough, each patch of water flickers on radar in time with the waves passing through. Timing that flicker gives an '
                     'estimate of the wave period — seconds between wave crests.',
                     'If it works, a radar could measure waves over a whole area, not just at a single buoy.',
                     'Only shown when the flicker signal is clear enough (quality ≥ 2.2) — usually in rougher seas. Compare it with the buoy\'s period: '
                     'dots on the dashed line mean a perfect match.'),
    'radar_vs_buoy': ('🤝', 'Checking the radar against the buoy',
                      'The Camp Ellis wave buoy sits about 700 m (2,300 ft) from the radar, inside its view. Every hour we pair the radar scan with '
                      'the buoy\'s wave height and wind, and measure how closely they rise and fall together ("r", the correlation).',
                      'If the radar\'s roughness follows the buoy, we can trust it to describe the rest of the bay where there is no buoy.',
                      'r = +1: in perfect step. Around 0.5: clearly related. Near 0: unrelated.'),
    # ---------------- weather & land ----------------
    'air_temp': ('🌡️', 'Air temperature',
                 'How warm the air is, measured in a shaded, ventilated shield about 2 m (6 ft) above the ground.',
                 'It sets the weather we feel, and it warms or cools the water and soil around it.',
                 'Coastal stations stay milder than inland ones — cooler on summer afternoons, warmer on winter nights.'),
    'humidity': ('💦', 'Relative humidity',
                 'How much water vapour is in the air compared with the most it could hold at that temperature.',
                 'High humidity feels muggy, means fog and dew are likely, and slows evaporation.',
                 '100% means the air is saturated — fog, dew or rain.'),
    'dewpoint': ('🌫️', 'Dew point',
                 'The temperature the air would have to cool to for dew or fog to form. Unlike humidity, it does not change just because '
                 'the air warms up during the day.',
                 'It is the best measure of how muggy it feels and when fog will form.',
                 'Dew point above ~65 °F (18 °C): sticky. Below ~50 °F (10 °C): crisp. When air temperature falls to the dew point, fog forms.'),
    'wind': ('💨', 'Wind',
             'Average wind speed, the strongest gust, and the direction the wind is blowing from.',
             'Wind builds waves, pushes water against the shore, mixes oxygen into the water and dries out soils.',
             'Light: under 10 mph. Breezy: 10–20 mph. Strong: 25+ mph. Gale: 39+ mph.'),
    'rain': ('🌧️', 'Rain',
             'Rain measured in a gauge, totalled for each hour and day.',
             'Rain washes fresh water, sediment, nutrients and sometimes pollution off the land into ponds, marshes and the bay — watch '
             'salinity drop and turbidity rise after a big storm.',
             '1 inch = 25.4 mm. A summer thunderstorm can drop an inch in an hour; Maine averages about 45 inches a year.'),
    'solar': ('☀️', 'Sunlight',
              'Solar radiation (W/m²) is the total energy arriving from the Sun. PAR (photosynthetically active radiation) is the part of '
              'that light plants can use, counted as light particles (µmol/m²/s).',
              'Sunlight powers photosynthesis on land and in the water, and warms the air and ground.',
              'Midday summer sun ≈ 1000 W/m²; heavy overcast ≈ 100 W/m². It is zero at night.'),
    'soil_temp': ('🪨', 'Soil temperature (by depth)',
                  'Temperature of the ground at several depths below the surface.',
                  'Soil warmth controls when seeds sprout, roots grow and insects become active. Deeper soil changes slowly and lags '
                  'the seasons — it is the last to cool in fall.',
                  'Near the surface it follows day and night; at 45 cm (18 in) it barely changes from day to day.'),
    'soil_moist': ('🌱', 'Soil moisture',
                   'How much of the soil, by volume, is water.',
                   'Plants depend on it; very wet soil means rain runs off instead of soaking in, very dry soil means drought stress.',
                   'Roughly 10–20%: dry. 20–35%: moist. Above 40%: soaked. It jumps after rain, then slowly drains and dries.'),
}

# which explanation goes with which data key on each kind of page
FOR_KEY = {
    'temp_c': 'water_temp', 'water_temp_c': 'water_temp', 'sal_psu': 'salinity', 'do_mgl': 'do', 'do_pct': 'do',
    'chl_ugl': 'chl', 'cdom_ppb': 'cdom', 'trp_ppb': 'trp', 'turb_ntu': 'turb', 'spcond_uscm': 'cond', 'water_level_m': 'tide',
    'air_temp_c': 'air_temp', 'rh_pct': 'humidity', 'dewpt_c': 'dewpoint', 'wind_ms': 'wind', 'gust_ms': 'wind',
    'wind_dir': 'wind', 'rain_mm': 'rain', 'solar_wm2': 'solar', 'par': 'solar', 'pres_kpa': 'pressure',
    'soil_t_4': 'soil_temp', 'soil_t_10': 'soil_temp', 'soil_t_20': 'soil_temp', 'soil_t_30': 'soil_temp',
    'soil_t_40': 'soil_temp', 'soil_t_45': 'soil_temp', 'soil_moist_15': 'soil_moist', 'soil_moist_30': 'soil_moist',
    'soil_moist_45': 'soil_moist',
}

CSS = """
.explain{grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr))}
.ex{display:flex;gap:12px;scroll-margin-top:12px}
.ex .i-emoji{font-size:28px;line-height:1.1}
.ex h4{margin:0 0 4px;font-size:15.5px}
.ex p{margin:0 0 6px;color:var(--ink2);font-size:14px}
.ex p b{color:var(--ink)}
.ex .read{background:var(--chip);border-radius:8px;padding:6px 9px;font-size:13.5px;color:var(--ink2);margin:6px 0 0}
.ex .here{font-size:13.5px;margin-top:6px;color:var(--ink)}
"""


def cards(keys, here=None):
    """HTML cards for the given explanation keys (duplicates removed, order kept). here = {exp_key: 'At this buoy …'}"""
    seen, out = set(), []
    for k in keys:
        if k not in E or k in seen:
            continue
        seen.add(k)
        em, name, what, why, read = E[k]
        h = (here or {}).get(k)
        out.append(f'<div class="card ex" id="ex-{k}"><div class="i-emoji">{em}</div><div><h4>{html.escape(name)}</h4>'
                   f'<p><b>What it is:</b> {html.escape(what)}</p><p><b>Why it matters:</b> {html.escape(why)}</p>'
                   f'<p class="read">📏 {html.escape(read)}</p>'
                   + (f'<p class="here">📍 <b>Here:</b> {html.escape(h)}</p>' if h else '') + '</div></div>')
    return ''.join(out)


SECTION = ('<section id="explain"><h2>📖 What do these numbers mean?</h2>'
           '<p class="lede">A quick guide to each measurement on this page — no science degree needed.</p>'
           '<div class="grid explain">{cards}</div></section>')
