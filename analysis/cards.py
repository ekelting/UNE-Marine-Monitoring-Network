"""Text for every card on the Analysis page. Numbers come from compute.py's results (R), so the words
stay true as the data update. Plain language first; the method sits in the "Is this sound?" box."""
import calendar

OK, CARE = ('ok', '✓ Solid'), ('care', '⚠ Use with care')
OC, MA, GE, MS, ME = '🌊 oceanographers', '📐 mathematicians', '🗺️ geographers', '🐟 marine scientists', '🦞 Mainers'
# Topics follow the seven questions on "Saco Bay, explained", from the big picture to the details.
GROUPS = [('glance', 'The year at a glance', ''),
          ('sea', 'Sea level, storms and flooding', 'These use NOAA\'s Portland tide gauge, running since 1912, so they are the most reliable comparisons on the page.'),
          ('temp', 'Warm year or cold?', ''),
          ('sand', 'Sand, waves and the seabed at Camp Ellis', ''),
          ('river', 'Where the river meets the sea', ''),
          ('algae', 'Algae', ''),
          ('land', 'Marsh, woods and wind', '')]
# Card order: (group, title prefix). Cards keep their own text; this only decides where each one sits.
ORDER = [('glance', 'Days that matter'),
         ('sea', 'Sea level is rising'), ('sea', 'Flooding is becoming routine'), ('sea', 'How high can the water get?'),
         ('sea', 'Same storm, higher sea'), ('sea', 'Storm surge this year'),
         ('temp', 'Was the sea warmer than normal?'), ('temp', 'Was the air warmer than normal?'), ('temp', 'Layers in the sea'),
         ('sand', 'Camp Ellis through time'), ('sand', 'Littoral drift: which way'), ('sand', 'Littoral drift: when'),
         ('sand', 'When does the seabed move?'), ('sand', 'Where does the bottom water go?'),
         ('river', 'The Saco River is running'), ('river', 'Rain, river and tide'), ('river', 'Tide clock'), ('river', 'Bigger tides, bigger salinity swings'),
         ('river', 'A salinity model for Jordan Point'), ('river', 'Estuary mixing calculator'), ('river', 'Are the four water-quality buoys'),
         ('algae', 'Chlorophyll: how much algae'), ('algae', 'Chlorophyll: why it'),
         ('land', 'The marsh'), ('land', 'How fast heat sinks into the forest soil'), ('land', 'Where does the wind come from?'),
         ('land', 'Does the radar agree with the weather station?')]


def arrange(C):
    """Put every card in its topic and in reading order; anything not listed keeps its place at the end of its old group."""
    def key(c):
        for i, (g, t) in enumerate(ORDER):
            if c['t'].startswith(t):
                c['g'] = g
                return i
        c['g'] = {'past': 'sea', 'one': 'land', 'compare': 'river', 'phys': 'sand'}.get(c['g'], c['g'])
        return len(ORDER)
    C.sort(key=key)
    return C


DIRS = ['north', 'north-northeast', 'northeast', 'east-northeast', 'east', 'east-southeast', 'southeast', 'south-southeast',
        'south', 'south-southwest', 'southwest', 'west-southwest', 'west', 'west-northwest', 'northwest', 'north-northwest']


def Lb(m): return f'<b data-len="{m:.3f}"></b>'
def Ls(m): return f'<span data-len="{m:.3f}"></span>'
def Tb(c): return f'<b data-temp="{c:.2f}"></b>'
def dTb(c): return f'<b data-dtemp="{c:.2f}"></b>'
def dTs(c): return f'<span data-dtemp="{c:.2f}"></span>'
def Rb(mm): return f'<b data-rain="{mm:.1f}"></b>'
def Fb(q): return f'<b data-flow="{q:.2f}"></b>'
def pct(x, d=0): return f'{x:.{d}f}%'
def pv(p): return '< 0.001' if p < 0.001 else f'{p:.3f}'
def sci(p):
    if p >= 0.001: return f'{p:.3f}'
    e = int(f'{p:e}'.split('e')[1]); sup = str.maketrans('-0123456789', '⁻⁰¹²³⁴⁵⁶⁷⁸⁹')
    return '10' + str(e).translate(sup)


def compass(deg): return DIRS[int(((deg % 360) + 11.25) // 22.5) % 16]


def ordinal(n):
    n = int(round(n)); return f'{n}{"th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")}'


def build(R):
    C = []
    add = lambda **k: C.append(k)  # noqa: E731

    # ------------------------------------------------------------------ PAST
    if 'msl' in R:
        m = R['msl']
        add(g='past', t='Sea level is rising', w='NOAA tide gauge, Portland · yearly averages since 1912', c=[OC, GE, ME],
            plain=f'The ocean at Portland is higher than it used to be. The tide gauge has measured it every month since {m["first"]}, so the trend shows clearly through all the ups and downs.',
            read='Each dot is one year\'s average sea level, measured as how much higher it was than in 1912. The orange line is the long-term trend. Watch the dots climb.',
            found=[f'Sea level at Portland has risen about <b>{m["slope"]*1000:.1f} mm per year</b> on average since {m["first"]}. That adds up to about {Lb(m["rise"])} so far.',
                   f'Over the last 30 years it has risen <b>{m["slope30"]*1000:.1f} mm per year</b>, about {m["slope30"]/m["slope"]:.1f}× the long-term pace.',
                   'Every high tide, storm and flood now starts from that higher level, which matters for beach and dune erosion.'],
            v=OK, math=f'''<p>Yearly averages of NOAA's monthly mean sea level (years with at least 11 months), with a least-squares trend. Because one year's sea level is related to the next, the error bar is widened to account for that.</p>
<div class="formula">trend = {m["slope"]*1000:.2f} ± {m["ci"]*1000:.2f} mm/yr (95%) · last 30 years: {m["slope30"]*1000:.1f} ± {m["ci30"]*1000:.1f} mm/yr</div>
<p>Assumes the land under the gauge is stable. Maine's land is close to stable, so this is close to true sea-level rise.</p>''',
            charts=[('pmsl', '')], cap='Yearly average sea level at Portland (above MLLW, the average lowest tide).', src='NOAA CO-OPS station 8418150')
    if 'flood' in R:
        fl = R['flood']; ratio = fl['last'] / fl['first'] if fl['first'] > 0 else None
        add(g='past', t='Flooding is becoming routine', w='NOAA tide gauge, Portland · days each year the water reached 12 ft', c=[ME, GE, OC],
            plain='At 12 feet above the low-tide datum, the National Weather Service\'s "minor flood" level for Portland, the lowest wharves and side streets near Portland Pier take on a few inches of water. Counting how many days a year that happens turns "a few millimetres of sea-level rise per year" into something you can see on the waterfront.',
            read='Each bar is one year: the number of days the highest tide reached 12 ft. The orange steps are the average for each decade.',
            found=[f'Before 1950 the water reached 12 ft on about <b>{fl["first"]:.1f} days a year</b>. Over {fl["last_span"][0]}–{fl["last_span"][1]} it averaged <b>{fl["last"]:.1f} days a year</b>' + (f', about {ratio:.0f}× as often.' if ratio and ratio >= 1.5 else '.'),
                   f'The most was <b>{fl["max"][1]} days</b>, in {fl["max"][0]}.',
                   'Most of these are not storms. As the sea rises, ordinary high tides (especially king tides) reach the level that once took a storm.'],
            v=OK, math=f'<p>Daily highest water from NOAA\'s verified hourly heights at Portland (station 8418150), {fl["start"]} to today. A day counts if any hourly reading reached 12.0 ft (3.66 m) above MLLW: the National Weather Service minor flood stage for this gauge, at which wharves and the most vulnerable side streets near Portland Pier flood 4 to 6 inches deep. Years with fewer than 330 days of data are left out. Hourly readings can miss the very top of a tide by a few centimetres, so counts are slightly conservative.</p>',
            charts=[('pflood', '')], cap='Days per year the water at Portland reached 12 ft above MLLW.', src='NOAA CO-OPS station 8418150')
    if 'amax' in R:
        a = R['amax']; rl = a['rl']; t = a['top']
        add(g='past', t='How high can the water get?', w='NOAA tide gauge, Portland · highest water each year · extreme-value fit', c=[OC, ME, MA],
            plain='Each year has one highest water level, usually a big storm on top of a high tide. With more than a century of these, we can estimate how high the water gets once every 10 or 100 years at today\'s sea level.',
            read='Each dot is one year\'s highest water, adjusted to today\'s sea level. Big orange dots reached the 1-in-10-year level. Dashed lines are the 10- and 100-year levels; the dotted line is an ordinary high tide.',
            found=[f'The record is {Lb(t[0][1])} above the low-tide datum, set in <b>{t[0][0]}</b>. Next highest: {t[1][0]} and {t[2][0]}.',
                   f'At today\'s sea level, a <b>1-in-10-year</b> storm tide reaches about {Lb(rl["10"])} and a <b>1-in-100-year</b> one about {Lb(rl["100"])} (likely range {Ls(a["ci100"][0])} to {Ls(a["ci100"][1])}).',
                   f'A 1-in-10-year storm tide is about {Lb(rl["10"]-a["mhhw"])} above an ordinary high tide.'],
            v=OK, math='''<p>Each year's highest monthly reading, shifted to today's sea level using the trend above. A generalized extreme value (GEV) distribution is fitted by maximum likelihood; the likely range comes from 300 bootstrap resamples.</p>
<div class="formula">return level z_T = GEV⁻¹(1 − 1/T)</div>
<p>"1-in-10-year" means a 10% chance in any year, not once every 10 years like clockwork. Assumes years are independent and storms aren't changing apart from sea level. Portland is about 20 km from Saco Bay, so local water can differ by a few centimetres.</p>''',
            charts=[('pamax', '')], cap='Highest water each year at Portland, adjusted to today\'s sea level (above MLLW).', src='NOAA CO-OPS station 8418150')
    if 'events' in R and 'msl' in R:
        r = R['events']['records']; gap_m = (r['ft2024'] - r['ft1978']) * 0.3048; slr = R['msl']['slope'] * (r['y2024'] - r['y1978'])
        add(g='past', t='Same storm, higher sea: 1978 vs 2024', w='NOAA tide gauge, Portland · the two record storms', c=[ME, OC, GE],
            plain=f'For 46 years the Blizzard of \'78 held Portland\'s record: {r["ft1978"]} ft. On January 13, 2024 a storm reached {r["ft2024"]} ft. How much of that new record came from a bigger storm, and how much from a higher sea?',
            read='The bar is how much higher the 2024 record was than 1978. The blue part is how much the sea itself rose in between; the orange part is everything else (storm surge and tide).',
            found=[f'The 2024 record beat 1978 by {Lb(gap_m)}. The sea rose about {Lb(slr)} between the two storms.',
                   f'So roughly <b>{slr/gap_m*100:.0f}%</b> of the new record came from a higher starting sea, not a bigger storm.',
                   f'The Blizzard of \'78 happening at today\'s sea level would have reached about {Lb(r["ft1978"]*0.3048 + R["msl"]["slope"]*(2026 - r["y1978"]))}.'],
            v=OK, math=f'<p>Record values from NOAA via the National Weather Service ({r["ft1978"]} ft MLLW in Feb 1978; {r["ft2024"]} ft MLLW on Jan 13, 2024). Sea-level rise between them uses the long-term trend ({R["msl"]["slope"]*1000:.2f} mm/yr). Year-to-year swings in average sea level (a few centimetres) mean the split is approximate.</p>',
            charts=[('psame', 'xs')], cap='How much higher the 2024 record was than 1978, split into sea-level rise and the rest.', src='NOAA CO-OPS 8418150; NWS Gray')
    if 'surge' in R:
        s = R['surge']; top = s['top']
        add(g='past', t='Storm surge this year', w='NOAA tide gauge, Portland · measured water minus predicted tide', c=[OC, ME, GE],
            plain='Tide tables predict the water from the Moon and Sun alone. Storm surge is the extra water the weather adds on top: wind piling water against the coast and low air pressure letting the sea bulge up.',
            read='The line shows how far above or below the tide tables the water was, averaged over a day. Orange bands are storms at the Camp Ellis wave buoy. Peaks inside the bands are storm surge.',
            found=[f'The biggest surge in the past year peaked at {Lb(s["max"])} on <b>{s["tmax"]}</b> (hourly peak; the daily average in the chart is lower).']
                  + ([f'Other big storm surges: ' + ', '.join(f'{e[0]} ({Ls(e[1])})' for e in top[1:3]) + '.'] if len(top) > 2 else [])
                  + [f'The water also ran {Lb(s["off"])} above the tide tables on average, all year. That is sea-level rise: the tables are based on 1983–2001 sea level.'],
            v=OK, math='<p>Hourly measured water level minus NOAA\'s hourly prediction, with the year\'s average offset removed, then a 25-hour running average. Storm periods are those on the Camp Ellis wave buoy page.</p>',
            charts=[('psurge', '')], cap='Storm surge at Portland (daily average). Orange bands are Camp Ellis wave storms.', src='NOAA CO-OPS station 8418150')
    if 'sst' in R:
        s = R['sst']
        warm = ' and '.join(w[0] for w in s['warm'])
        add(g='past', t='Was the sea warmer than normal?', w='NOAA buoy 44007 (off Portland) · daily water temperature vs the 1991–2020 normal', c=[MS, OC, ME],
            plain='"Normal" here means the average for each date from 1991 to 2020, measured by a NOAA buoy off Portland. Comparing the past year with that shows whether the water was unusually warm or cold, which matters for lobsters, algae and fish.',
            read='Top: the grey band is the normal range for each date (the middle 80% of past years). Blue is the NOAA buoy over the past year; the dotted line is Camp Ellis, close to shore. Above the band means unusually warm. Bottom: one stripe per year, blue cooler and red warmer than the 1991–2020 average; gaps are years with too little data.',
            found=[f'Over the past year the sea off Portland averaged {dTb(abs(s["meanan"]))} <b>{"warmer" if s["meanan"] >= 0 else "cooler"}</b> than normal. Warmest compared with normal: {warm}.']
                  + ([f'{" and ".join(c[0] for c in s["cold"])} ran a little cooler than normal.'] if s['cold'] else [])
                  + [('It did <b>not</b> meet the standard definition of a marine heatwave (5+ days in a row above the warmest 10% for that date).' if s['mhw'] == 0
                      else f'It met the standard definition of a <b>marine heatwave</b> on {s["mhw"]} days (5+ days in a row above the warmest 10% for that date).'),
                     f'Since 1990 the yearly average has {"warmed" if s["slope"] > 0 else "cooled"} about {dTb(abs(s["slope"])*10)} <b>per decade</b>. The Gulf of Maine is one of the fastest-warming ocean areas.'],
            v=OK, math=f'''<p>Daily means of NOAA buoy 44007 water temperature (about 1 m deep). Normal: 1991–2020 values within ±5 days of each date, smoothed over 31 days; band = 10th to 90th percentile. Marine-heatwave test follows Hobday et al. (2016). Trend: least squares on yearly averages for the {s["nyears"]} years with at least 330 days of data (p = {pv(s["p"])}).</p>
<p>Camp Ellis is shown for comparison: its water is shallow and close to shore, so it heats up more in summer (about 0.5–1.3 °C warmer than the NOAA buoy) and cools more in winter (about 1–1.5 °C colder).</p>''',
            charts=[('psst', ''), ('psstyr', 'xs')], cap='Top: daily sea temperature vs normal. Bottom: "warming stripes", one per year at buoy 44007.', src='NOAA NDBC buoy 44007')
    if 'flow' in R:
        f = R['flow']
        add(g='past', t=f'The Saco River {"is running low" if f["med_rank"] < 40 else "compared with normal"}', w=f'USGS gauge, Saco River at Cornish · daily flow vs every year since {f["start"]}', c=[GE, MS, ME],
            plain='How much water is the Saco River carrying compared with normal for the date? A low river means less fresh water reaching the estuary, so the estuary gets saltier.',
            read='The line shows the river\'s flow as a percentage of normal for that date. The dashed line at 100% is normal; the shaded strip at the bottom is less than half of normal.',
            found=[f'On a typical day of the past year the river sat at the <b>{ordinal(f["med_rank"])} percentile</b> for the date ({"below" if f["med_rank"] < 50 else "above"} normal).',
                   f'On <b>{f["n_low"]} days</b> it was in the lowest 10% ever recorded for that date.',
                   f'Over the last two months it ran at about <b>{f["last60"]:.0f}%</b> of normal. The wettest month compared with normal was {f["wettest"][0]} ({f["wettest"][1]:.0f}%).'],
            v=OK, math=f'<p>USGS daily mean discharge, site 01066000, {f["start"]} to one year ago as the baseline. For each date, the median and percentiles of all flows within ±3 days. Recent values are provisional.</p>',
            charts=[('pflow', '')], cap='Daily flow at Cornish as a percentage of the median for the same date. Hover for the percentile.', src='USGS 01066000')
    if 'air' in R:
        a = R['air']
        add(g='past', t='Was the air warmer than normal?', w='NOAA, Portland Jetport normals · with the Ram Island station', c=[ME, GE],
            plain='Same idea for the air. Portland\'s airport has daily records, so each day can be compared with its 1991–2020 normal. Ram Island tracks Portland closely, which also shows our station is measuring well.',
            read='Each bar is one week: red bars were warmer than the 1991–2020 normal for those dates, blue bars colder. Taller bars mean a bigger difference.',
            found=[f'Coldest month compared with normal: <b>{a["cold"]}</b>, about {dTb(abs(a["coldv"]))} {"below" if a["coldv"] < 0 else "above"} normal.',
                   f'Warmest compared with normal: <b>{a["warm"]}</b>, about {dTb(abs(a["warmv"]))} {"above" if a["warmv"] > 0 else "below"} normal.',
                   f'Ram Island and Portland rise and fall almost identically (correlation {a["r"]:.2f}). Ram Island is milder: warmer in winter and cooler in summer, because it is surrounded by the sea, which changes temperature more slowly than land.'],
            v=OK, math='<p>Daily mean = (max + min) / 2 from GHCN-Daily station USW00014764. Normal = the 1991–2020 average within ±7 days of each date. Chart shows 7-day averages.</p>',
            charts=[('pair', '')], cap='Weekly difference from the 1991–2020 normal, Portland Jetport.', src='NOAA GHCN-Daily, Portland International Jetport')

    # ------------------------------------------------------------------ ONE STATION
    if 'marsh' in R:
        m = R['marsh']
        add(g='one', t='The marsh\'s tidal fingerprint', w='Biddeford Pool Marsh · water level · harmonic analysis', c=[OC, MA, GE],
            plain='Tides are made of a few regular "beats" set by the Moon and Sun. If you know how strong each beat is, you can predict the tide. Here we measure those beats for the marsh, then check how well they explain the water level.',
            read='Top: the solid line is the measured water; the dotted line is the tide predicted from the beats. Where they match, the tide is in control. Bottom: how strong each beat is.',
            found=[f'The tide explains <b>{m["r2"]*100:.0f}%</b> of the marsh\'s water-level changes over the last 30 days. The rest is weather.',
                   f'The water comes in faster than it goes out: about <b>{m["rise"]:.1f} hours rising</b> and <b>{m["fall"]:.1f} hours falling</b>, measured over {m["ntides"]} tides.',
                   ('A marsh that floods quickly and drains slowly tends to <b>trap sediment</b>, which helps it build up as the sea rises.' if m['rise'] < m['fall'] else 'The marsh drains faster than it floods, which tends to export sediment.')],
            v=OK, math='''<p>Least-squares fit of seven tidal constituents (M2, S2, N2, K1, O1, M4, M6) to the last 30 days of hourly water level. Thirty days separates M2 from N2, but not K1 from P1 (that needs 6 months), so K1 includes some P1.</p>
<div class="formula">h(t) = h₀ + Σ [aᵢ cos(ωᵢt) + bᵢ sin(ωᵢt)] · strength = √(aᵢ² + bᵢ²)</div>
<p>Rise and fall times come from 5-minute data, between successive highs and lows. The gauge sits on the creek bed and can't see the very lowest water, which slightly distorts the shallow-water beats (M4, M6).</p>''',
            charts=[('p1', ''), ('p1b', 'sm')], cap='Top: measured level vs tide-only prediction, last 8 days. Bottom: strength of each tidal beat.')
    if 'tideclock' in R:
        h = R['tideclock']
        add(g='one', t='Tide clock', w='Jordan Point · salinity · hour × day', c=[ME, GE, MS],
            plain='A calendar of saltiness. Each row is a day and each square is an hour. Dark blue is salty ocean water; light is fresher river water.',
            read='Follow a dark band down the page: it slides to the right, because high tide comes about 50 minutes later each day. Rows that are pale all day are when the river pushed the salt out.',
            found=['Two dark bands per day: the two high tides.', f'Over the last month saltiness ranged from about <b>{h["lo"]:.0f}</b> to <b>{h["hi"]:.0f}</b> PSU, sometimes within a single tide.'],
            v=OK, math='<p>Hourly mean salinity, last 31 days, no smoothing. Purely descriptive.</p>',
            charts=[('p3', 'tall')], cap='Hourly salinity at Jordan Point (PSU: about grams of salt per kilogram of water).')
    if 'strat' in R:
        s = R['strat']
        add(g='one', t='Layers in the sea', w='Camp Ellis mooring · temperature at three depths', c=[OC, MS],
            plain='In summer the sun warms the top of the sea, and that warm, light water floats on colder, heavier water below, like oil on vinegar. In fall, storms and cooling stir the layers back together.',
            read='The shaded area shows how much warmer the top of the sea is than the bottom. A big gap means the sea is layered; near zero means it is mixed from top to bottom.',
            found=([f'Fully mixed (all depths within a fraction of a degree) in: <b>{", ".join(s["mixed"])}</b>.'] if s['mixed'] else [])
                  + [f'Most layered in <b>{s["maxm"]}</b>: the upper sensor averaged {dTb(s["maxd"])} warmer than the deepest one.',
                     'Layering matters for oxygen near the bottom and for how storms move heat and sediment.'],
            v=CARE, math='<p>Daily means of the three temperature sensors on the Camp Ellis smart mooring (positions 1, 2 and 3, shallowest to deepest). Their exact depths aren\'t recorded in the data. Temperature sets most of the density here, but salinity also matters near the river plume.</p>',
            charts=[('pstrat', '')], cap='Daily temperature difference between the top and bottom mooring sensors, Camp Ellis.')
    if 'soil' in R:
        s = R['soil']
        hr = lambda h: f'{int(h) % 12 or 12} {"am" if int(h) % 24 < 12 else "pm"}'  # noqa: E731
        add(g='one', t='How fast heat sinks into the forest soil', w='363 Acre Woods · soil temperature at six depths · heat-equation fit', c=[MA, GE],
            plain='Every sunny day sends a pulse of warmth into the ground. The pulse gets weaker and later the deeper it goes, like a ripple fading in thick honey. How fast it fades tells us how easily heat moves through that soil.',
            read='Each row is a depth and time runs left to right. Red means warmer than that depth\'s daily average, blue cooler. Follow a red patch downward: it fades and shifts to the right, because the warmth arrives later and weaker deeper down.',
            found=[f'The daily swing shrinks from {dTb(2*s["amp"][0])} at 4 cm to almost nothing ({dTs(2*s["amp"][-1])}) at 45 cm.',
                   f'The daily peak arrives about <b>{s["lag10"]:.1f} hours later for every 10 cm</b> deeper: about {hr(s["peak"][0])} at 4 cm, {hr(s["peak"][2])} at 20 cm, {hr(s["peak"][-1])} at 45 cm.',
                   f'Two independent methods (shrinking and delay) give damping depths of {s["damp_a"]*100:.1f} and {s["damp_p"]*100:.1f} cm. Thermal diffusivity is about <b>{s["kappa"]*1e7:.1f} × 10⁻⁷ m²/s</b>, typical of moist forest soil.'],
            v=OK, math=f'''<p>The heat equation ∂T/∂t = κ ∂²T/∂z², driven by a daily sine wave at the surface, predicts amplitude A(z) = A₀e^(−z/d) and delay Δt = z/(ωd), with damping depth d = √(2κ/ω). Daily cycles were fitted at each depth for June 1 – September 15, {s["year"]}, after removing the 24-hour running mean.</p>
<div class="formula">κ = ω d² / 2</div><p>Assumes uniform soil and steady moisture, with no rain carrying heat downward. The deepest sensors' swings are below the 0.1 °C reporting step, so 40 and 45 cm are shown but not used in the fit.</p>''',
            charts=[('p5', '')], cap=f'One week in July {s["year"]}: each depth\'s temperature minus its own daily average.')
    if 'head' in R:
        h = R['head']
        lm = calendar.month_name[int(h['lob_month'])] if h.get('lob_month') else ''
        tiles = [('🏊 Swim days at Camp Ellis', f'{h["swim"]}', f'daily water ≥ <span data-temp="18.3"></span>' + (f', {h["swim_first"]} – {h["swim_last"]}' if h['swim'] else '')),
                 ('🦞 Lobster-stress hours', f'{h["lob"]}', f'water above <span data-temp="20"></span> at Camp Ellis' + (f', mostly {lm}' if lm else '')),
                 ('🌱 Growing degree-days', f'<span data-gdd="{h["gdd"]:.0f}"></span>', f'363 Acre Woods since April 1, {h["gdd_year"]}'),
                 ('🐟 Low-oxygen hours', pct(h['gp_low']), f'Great Pond below 2 mg/L in {h["gp_month"]}'),
                 ('🌊 Highest water this year', f'<span data-len="{h["hw"]:.3f}"></span>', f'Portland, {h["hw_t"]}' + ('' if h['hw_storm'] else ': mostly a "king tide" (one of the year\'s highest predicted tides), not a storm')),
                 ('🌪️ Biggest waves at Camp Ellis', f'<span data-len="{h["wave"]:.3f}"></span>', h['wave_t'])]
        add(g='one', t='Days that matter', w='Several stations · the past 12 months', c=[ME, MS], plain='The headline numbers from the past year.', read='', found=[], tiles=tiles,
            v=CARE, math='''<p>Swim days: daily mean at the Camp Ellis upper mooring sensor ≥ 18.3 °C (65 °F); that sensor is below the surface, so the true count is likely a bit higher. Lobster stress: hours above 20 °C, a commonly used threshold for American lobster. Growing degree-days: sum of max(0, (Tmax + Tmin)/2 − 10 °C) since April 1. Low oxygen: share of hours below 2 mg/L (hypoxic) in the worst month.</p>
<p>Great Pond's oxygen sensor has never read above ''' + f'{h["gp_max"]:.1f}' + ''' mg/L; if that seems low for the pond, the sensor's placement is worth checking.</p>''',
            charts=[], cap='')
    if 'wrose' in R:
        w = R['wrose']
        add(g='one', t='Where does the wind come from?', w='Ram Island weather station · wind rose', c=[ME, GE, OC],
            plain='A wind rose is a compass that shows how often the wind blows from each direction, and how strongly. Wind direction drives waves, surge and which way sand moves along the beach.',
            read='Each petal points to where the wind comes <b>from</b>. Longer petals mean that direction is more common. Darker colours are stronger winds.',
            found=[f'The most common winds come from the <b>{DIRS[w["top"][0]]}</b>, <b>{DIRS[w["top"][1]]}</b> and <b>{DIRS[w["top"][2]]}</b>.',
                   f'Winds from the northeast to east-southeast blow only {pct(w["east"])} of the time, but they bring the big storm waves and surge into Saco Bay.'],
            v=OK, math=f'<p>All hourly Ram Island readings since {w["start"]}, in 16 direction sectors and 4 speed classes, as a share of all hours.</p>',
            charts=[('pwrose', '')], cap='Share of hours the wind came from each direction, by speed.')
    if 'chl' in R:
        W, J = R['chl']['Wood Island'], R['chl']['Jordan Point']
        add(g='one', t='Chlorophyll: why it "dips" at noon', w='Wood Island and Jordan Point · chlorophyll by hour of day', c=[MS, OC, ME],
            plain='Chlorophyll tells us how much algae (phytoplankton) is in the water. The sensor shines blue light and measures the red glow the algae give back. In bright sun, algae protect themselves by glowing less, a bit like squinting, so the sensor reads low at midday even though the algae are still there.',
            read='Each line is the typical value for that hour of the day; the shaded band shows the usual range. Notice the dip around noon. The fair reading is the night-time level.',
            found=[f'At Wood Island the midday reading is about <b>{W["ratio"]*100:.0f}%</b> of the night-time reading; at Jordan Point about <b>{J["ratio"]*100:.0f}%</b>.',
                   'So daytime chlorophyll numbers <b>undercount</b> the algae. For trends and comparisons, use night-time values.',
                   'This is a well-known effect called non-photochemical quenching, not a sensor fault.'],
            v=OK, math=f'<p>Median and middle half (interquartile range) of hourly chlorophyll by hour of day, {J["start"]} – {J["end"]}. Night = 10 pm – 4 am; midday = 10 am – 2 pm. Values use the sonde\'s factory calibration, so comparisons within one sensor are more reliable than between sensors.</p>',
            charts=[('pchlday', '')], cap='Typical chlorophyll at each hour of the day (line = median, band = middle half of readings).')
        bins = [b for b in J['bins'] if b is not None]
        add(g='one', t='Chlorophyll: how much algae, and where does it come from?', w='Wood Island and Jordan Point · night-time chlorophyll · chlorophyll vs salinity', c=[MS, ME, GE],
            plain='Using only night-time readings, we can track algae day by day and rate it on the scale NOAA uses for estuaries. Plotting chlorophyll against saltiness at Jordan Point also shows whether the algae ride in with the ocean or come down the river.',
            read='Top: one dot per night; the coloured strips are NOAA\'s "low" (under 5 µg/L) and "medium" (5–20) levels. Bottom: each box shows Jordan Point\'s night-time chlorophyll for water of a given saltiness; boxes further right are saltier (more ocean water).',
            found=[f'Wood Island: low on {W["cls"][0]} of {W["nn"]} nights, medium on {W["cls"][1]}, high on {W["cls"][2]}. Jordan Point: low on {J["cls"][0]} of {J["nn"]}, medium on {J["cls"][1]}, high on {J["cls"][2]}.',
                   (f'At Jordan Point the <b>saltiest water carries the most algae</b> (median {bins[-1]:.1f} µg/L in the saltiest vs {bins[0]:.1f} in the freshest), so the algae are coming in with the tide from the bay.'
                    if len(bins) > 1 and bins[-1] > 1.5 * bins[0] else
                    (f'At Jordan Point the <b>freshest water carries the most algae</b> (median {bins[0]:.1f} µg/L vs {bins[-1]:.1f} in the saltiest), so the algae are coming down the river.'
                     if len(bins) > 1 and bins[0] > 1.5 * bins[-1] else 'At Jordan Point algae levels are similar in fresh and salty water.'))],
            v=CARE, math=f'<p>Nightly medians (10 pm – 4 am), last 60 days. NOAA ASSETS / National Estuarine Eutrophication Assessment levels: low ≤ 5, medium 5–20, high 20–60, very high > 60 µg/L. NOAA\'s ratings use the 90th percentile over a whole season, so this is an early look. Chlorophyll–salinity correlation (night) r = {J["r"]:.2f}.</p>',
            charts=[('pchlnight', ''), ('pchlsal', '')], cap='Top: night-time chlorophyll at each buoy. Bottom: night-time chlorophyll at Jordan Point, grouped by how salty the water was.')

    # ------------------------------------------------------------------ COMPARE
    if 'anova' in R:
        A = R['anova']
        def verdict(v, name):
            pr = A[v]['pairs']; sig = [p for p in pr if p[4] < 0.05]
            return f'<b>{name}:</b> ' + (f'{len(sig)} of {len(pr)} pairs of buoys clearly differ.' if sig else 'no pair of buoys reliably differs.')
        jp = [p for p in A['temp_c']['pairs'] if 'Jordan Point' in p[:2] and p[4] < 0.05]
        add(g='compare', t='Are the four water-quality buoys really different?', w='Wood Island, Jordan Point, Ferry Beach, Goose Rocks Beach · statistical tests', c=[MA, MS, OC],
            plain='We want to know whether places truly differ, or whether we are just seeing random wiggles. The catch: each day\'s reading is a lot like the day before, so the data hold less independent evidence than their count suggests. Ignoring that makes tiny differences look "highly significant." These tests account for it.',
            read='The map shows each buoy coloured by its average saltiness (darker = saltier). Below, each dot is how different two buoys are on average, and its line is the range we are confident in. If the line crosses the dark zero line, we cannot say those two differ; orange dots are clearly different. Use the buttons to switch measurement.',
            found=[verdict('sal_psu', 'Salinity'), verdict('temp_c', 'Temperature'), verdict('do_mgl', 'Oxygen'),
                   f'Why it matters: a naive test on hourly oxygen data gives p = {sci(A["do_mgl"]["pn"])}, a "highly significant" difference that mostly disappears once the day-to-day memory is counted.'],
            v=OK, math=f'''<p>Daily means over the {A["sal_psu"]["n"]} most recent days when all four buoys reported ({A["sal_psu"]["start"]} – {A["sal_psu"]["end"]}). For each pair, the daily <i>difference</i> is tested with a t-test whose sample size is cut to the effective number of independent days, n_eff = n(1 − r₁)/(1 + r₁), where r₁ is the day-to-day correlation of the difference. Because six pairs are tested for each measurement, p-values are adjusted for multiple comparisons (Holm method).</p>
<p>For reference, the classic tests on salinity, which treat days as independent: one-way ANOVA F = {A["sal_psu"]["F"]:.0f}, Kruskal–Wallis H = {A["sal_psu"]["K"]:.0f}, Friedman χ² = {A["sal_psu"]["Fr"]:.0f}; effect size η² = {A["sal_psu"]["eta2"]:.2f}. Their p-values are too small for the reason above, so the table uses the adjusted tests.</p>''',
            tabs=True, charts=[('pmap', 'map'), ('p8', '')], cap='Map: average salinity over the last 30 days (coastline © OpenStreetMap contributors). Chart: average difference between each pair of buoys, with ranges adjusted for making six comparisons.')
    if 'rain' in R:
        r = R['rain']
        add(g='compare', t='Rain, river and tide: what moves the estuary?', w='Ram Island rain · USGS Saco River flow · Jordan Point salinity', c=[MS, GE, ME],
            plain='Rain fills the river, the river pushes fresh water down to Jordan Point, and the tide pushes salt water back up twice a day. These charts line up the causes and the effect.',
            read='Top: rain each day. Middle: Saco River flow. Bottom: daily average salinity at Jordan Point. Look for the river rising as the salinity falls.',
            found=[f'The wettest week ({r["wet_start"]} – {r["wet_end"]}, {Rb(r["wet"])}) raised the river\'s flow about {r["qrise"]:.1f}×, and Jordan Point\'s daily salinity fell from {r["before"]:.1f} to <b>{r["low"]:.1f} PSU</b> ({r["low_t"]}).',
                   f'Day to day, salinity goes {"down" if r["r_q"] < 0 else "up"} with river flow (correlation {r["r_q"]:.2f}) and {"up" if r["r_tr"] > 0 else "down"} with tidal range ({r["r_tr"]:.2f}): bigger tides push more salt in. Both matter.'],
            v=CARE, math='<p>Descriptive: daily totals and means over the last 45 days. River flow and tidal range overlap in time, so their separate effects are estimated in the salinity-model card.</p>',
            charts=[('p10a', 'xs'), ('p10q', 'xs'), ('p10b', 'sm')], cap='Daily rain at Ram Island, Saco River flow at Cornish (USGS) and Jordan Point salinity.')
    if 'radar' in R:
        r = R['radar']
        add(g='compare', t='Does the radar agree with the weather station?', w='Ram Island Radar vs Ram Island wind sensor', c=[OC, MA],
            plain='The radar sees how rough the sea surface looks. The weather station on the same island measures wind. If the radar works as we think, rougher water should go with stronger wind.',
            read='Grey dots are single radar scans. The orange line is the typical roughness at each wind speed: flat at first, then climbing once the wind passes about 10 mph.',
            found=[f'Below about <b>10 mph</b> the sea barely shows up on radar. Above that, roughness climbs steadily with wind (correlation {r["r"]:.2f}).',
                   f'It matches the <b>waves</b> even better ({r["rw"]:.2f} with the Camp Ellis buoy\'s wave-based wind): the radar sees the waves the wind makes, and waves linger after the wind drops.',
                   f'Bonus: the radar sees about <b>{(r["weekend"]/r["weekday"]-1)*100:.0f}% more boats</b> per scan on weekends.'],
            v=OK, math=f'<p>{r["n"]} scans matched to hourly wind. Correlations are descriptive; no p-values are given because hourly values aren\'t independent. The relationship is curved (a threshold), so the rank correlation ({r["rs"]:.2f}) is also reported.</p>',
            charts=[('p11', '')], cap='Each grey dot is one radar scan matched to that hour\'s wind; the orange line is the median for each 1 m/s of wind.')

    # ------------------------------------------------------------------ PHYSICS
    if 'events' in R:
        E = R['events']
        add(g='phys', t='Camp Ellis through time', w='History of the beach, the jetty and the storms', c=[GE, ME, OC],
            plain='Camp Ellis is one of the best-studied eroding beaches in Maine. Its story explains why the sand-drift results matter: the jetty cut the beach off from its sand, and the waves keep carrying sand north.',
            read='', found=[], timeline=E['camp_ellis'],
            v=OK, math='<p>Compiled from: ' + '; '.join(f'<a href="{u}">{t}</a>' for t, u in E['camp_ellis_sources']) + '.</p>', charts=[], cap='')
    if 'drift' in R:
        d = R['drift']; nd, od = d['net_dir'], d['other_dir']
        away = 'north, away from Camp Ellis and the Saco River jetty, toward Old Orchard and Pine Point' if nd == 'north' else 'south, toward the Saco River jetty'
        add(g='phys', t='Littoral drift: which way does the sand go, and why?', w='Camp Ellis wave buoy · wave direction vs the beach', c=[OC, GE, ME],
            plain='When waves hit a beach at an angle, they push sand along the shore like a conveyor belt. Which way the belt runs depends on which side of "straight on" the waves come from. The compass shows where Camp Ellis\'s wave energy comes from, with the beach drawn in.',
            read='The thick yellow line is the beach. The dotted arrow points the way a wave would come if it hit the beach straight on. Dark petals show where the wave energy comes from. Petals in the blue half push sand north; petals in the orange half push it south.',
            found=[f'Most wave energy arrives from the <b>{DIRS[d["top_dirs"][0]]}</b> and <b>{DIRS[d["top_dirs"][1]]}</b>. The beach just north of the Camp Ellis jetty faces east-northeast, so these waves arrive from slightly south of straight on.' if nd == 'north'
                   else f'Most wave energy arrives from the <b>{DIRS[d["top_dirs"][0]]}</b> and <b>{DIRS[d["top_dirs"][1]]}</b>.',
                   f'Of the energy that reaches the beach at an angle, <b>{d["with_share"]:.0f}%</b> pushes sand <b>{away}</b>.',
                   'That matches decades of geological work in Saco Bay: sand moves north from the Saco River, Pine Point has grown, and Camp Ellis, cut off from the river\'s sand by the jetty, erodes.' if nd == 'north' else
                   'Note: geological studies of Saco Bay find net drift to the north overall; this single-buoy estimate is very sensitive to the beach angle (see the next card).'],
            v=CARE, math=f'''<p>Wave energy by direction: sum of H<sub>s</sub>²·T<sub>p</sub> (proportional to wave energy flux) in each 22.5° sector of the buoy's mean wave direction (where waves come from; energy-weighted mean {d["mean_dir"]:.0f}°). The beach from the jetty to Ferry Beach runs north-northwest, so a wave hitting it straight on comes from about {R["cfg"]["normal"]}° (estimated from map coordinates; a surveyed shoreline would sharpen it).</p>
<p>The answer depends on that angle: with these waves the drift flips direction if the beach faced {d["flip"]:.0f}° or more (see the next card). Farther north, where the shore turns to face east-southeast at Old Orchard, the same waves would push sand the other way, so this estimate applies to the Camp Ellis – Ferry Beach stretch only.</p>''',
            charts=[('pdrose', 'tall'), ('p13', 'sm')], cap=f'Top: share of wave energy from each direction, with the beach and the straight-on direction. Bottom: running total of sand pushed {nd} since {d["start"]}, thousand m³ (orange bands are storms).')
        top4 = d['ranking'][:4]; t4 = sum(r[1] for r in top4) / d['total'] * 100
        add(g='phys', t='Littoral drift: when, and how much?', w='Camp Ellis wave buoy · waves to the break point · CERC and Kamphuis formulas', c=[OC, GE, MA],
            plain='Now the amounts: how much sand the waves could move each month, and which storms did the most work. These are rough estimates, so think of them as "about this big" rather than exact numbers.',
            read=f'Top: each bar is a month; bars above the line are sand pushed {nd}, below are sand pushed {od}. Middle: storms ranked by how much sand they moved, with their share of the total on the bars. Bottom: how the yearly amount depends on which way the beach faces; above zero is northward.',
            found=[f'The busiest month was <b>{d["busiest"]}</b>. The single busiest storm, <b>{top4[0][0]}</b>, moved about {top4[0][1]/d["total"]*100:.0f}% of the total by itself.',
                   f'The top 4 storms moved about <b>{t4:.0f}%</b> of the sand; all {d["nstorms"]} storms together about {d["storm_share_k"]:.0f}%, though storms were only {d["storm_hours"]:.0f}% of the hours.',
                   f'Summer (June–August) moved {"less" if d["summer"] < d["feb"] else "more"} sand than February alone.',
                   f'Yearly amount at Camp Ellis: roughly <b>{abs(d["k_here"])/1000:.0f},000 m³ {nd}</b> by Kamphuis ({abs(d["c_here"])/1000:.0f},000 by CERC, which tends to overestimate). These are what the waves <i>could</i> move if sand were unlimited; with the jetty blocking the river\'s sand, the real amount is limited by supply.'],
            v=CARE, math='''<p>Each hour, waves are refracted and shoaled from the buoy (12 m) to breaking (H = 0.78·depth) with Snell's law over straight, parallel depth contours, then</p>
<div class="formula">CERC: Q = K√g·H_b^2.5·sin(2α_b) / [16√γ (s−1)(1−n)], K = 0.39</div>
<div class="formula">Kamphuis: Q_m = 2.27·H_b²·T_p^1.5·m_b^0.75·D50^−0.25·sin^0.6(2α_b)</div>
<p>Assumptions: beach slope 0.02, grain size 0.2 mm, porosity 0.4. Wood Island, Ram Island and the jetty bend waves in ways straight contours miss, and the shoreline curves through the bay, so a wave model (such as SWAN) run along a surveyed shoreline would sharpen both the amounts and where the drift changes direction. Storm periods are those on the Camp Ellis wave buoy page.</p>''',
            charts=[('pdmonth', ''), ('pdstorm', ''), ('p13b', 'sm')], cap='Top: monthly potential transport (Kamphuis). Middle: storms ranked by sand moved (Kamphuis). Bottom: net yearly rate (+ north) vs the direction the beach faces.')
    if 'shields' in R:
        s = R['shields']
        add(g='phys', t='When does the seabed move?', w='Camp Ellis buoy (about 12 m deep) · wave motion at the bed · Shields number', c=[OC, MA],
            plain='Waves move water back and forth all the way down to the seabed. If that motion is strong enough, it rolls sand grains along. The Shields number compares the push with the grain\'s weight: above the line, sand moves.',
            read='Each bar is a month: the share of hours when waves were strong enough to roll fine sand on the seabed 12 m down.',
            found=[f'At the buoy\'s depth, fine sand moves in about <b>{s["move"]:.0f}%</b> of hours: about {s["winter"]:.0f}% in winter (December–March) and {s["summer"]:.0f}% in summer. The most active months: {s["top"][0]} and {s["top"][1]}.',
                   ('The very strong "sheet flow", when the whole surface layer moves, never happened at this depth. It happens closer to shore, where waves break.' if s['sheet'] < 0.05
                    else f'"Sheet flow", when the whole surface layer moves, happened in {s["sheet"]:.1f}% of hours.')],
            v=OK, math='''<p>Bed orbital velocity U = πH<sub>s</sub>/(T·sinh kh) from linear wave theory (depth 12.7 m including mean tide); skin-friction factor f<sub>w</sub> = 1.39(A/z₀)^−0.52 with z₀ = 2.5·D50/30 (Soulsby 1997); θ = ½f<sub>w</sub>U² / [(s−1)g·D50]; threshold θ<sub>cr</sub> from Soulsby & Whitehouse. D50 = 0.2 mm (fine sand).</p>
<p>Waves only: adding the measured bottom current and local grain-size samples would sharpen it.</p>''',
            charts=[('p14', '')], cap='Share of each month\'s hours with enough wave motion at the bed to move fine (0.2 mm) sand.')
    if 'currents' in R:
        c = R['currents']
        add(g='phys', t='Where does the bottom water go?', w='Camp Ellis current meter · progressive vector diagram · current rose · wind check', c=[OC, MS],
            plain='Imagine a drop of dye released at the buoy and carried by the measured current every hour. The tides mostly slosh it back and forth, but a small steady drift adds up. That drift shows where fine sediment near the bottom tends to go.',
            read='Top: the path the dye would follow (km). Middle: how often the current flows toward each direction. Bottom: each dot is a day, comparing the along-shore wind with the along-shore bottom current.',
            found=[f'Net drift is slow and toward the <b>{compass(c["dir"])}</b>: about <b>{c["speed"]*100:.1f} cm/s</b>, roughly {c["speed"]*86.4:.1f} km a day, adding up to {c["km"]:.0f} km over {c["days"]} days.',
                   f'Tidal currents run mostly <b>{compass(c["axis"])}–{compass(c["axis"]+180)}</b>, at about {c["mean_speed"]*100:.0f} cm/s.',
                   (f'Near the bottom, on days when wind blows north along the shore, the current tends to flow south (correlation {c["r_wind"]:.2f}). That is typical of a bay: wind pushes surface water one way and deeper water returns the other way. It is also why this offshore bottom drift can run opposite to the sand moving along the beach.'
                    if c['r_wind'] < -0.3 else f'Along-shore bottom current and along-shore wind correlate at {c["r_wind"]:.2f}.')],
            v=CARE, math='''<p>Hourly speed and direction (rotated from magnetic to true north, declination −14.6°) are converted to east/north components and summed: x(t) = Σ u·Δt, y(t) = Σ v·Δt. This assumes the current at the buoy represents a wider area, a standard caveat for these diagrams. Direction is the direction the current flows toward, as labelled in the NERACOOS data catalogue for this buoy (CF standard name direction_of_sea_water_velocity).</p>''',
            charts=[('p15', ''), ('p15b', ''), ('p15c', 'sm')], cap='Top: path of a bottom water parcel. Middle: share of hours the current flowed toward each direction. Bottom: daily along-shore wind vs along-shore current (+ = toward north-northeast).')
    if 'ode' in R:
        o = R['ode']; p = o['par']; se = p['se']
        weak = any(abs(v) < 2 * e for v, e in [(p['bq'], se[2]), (p['bt'], se[3]), (p['tau'], se[0])])
        add(g='phys', t='A salinity model for Jordan Point', w='Jordan Point salinity · USGS Saco River flow · tides · fitted differential equation', c=[MA, OC, MS],
            plain='A simple equation that says salinity is always drifting toward a "target" level. More river water lowers the target; bigger tides raise it. Fitting the equation to the data gives numbers for a differential-equation model.',
            read='Top: the faint line is hourly salinity, the solid line is salinity with the tides averaged out, and the dotted line is the model. The two smaller charts are what drives the model: river flow and tidal range.',
            found=[f'The model follows the main ups and downs: it explains about <b>{p["R2"]*100:.0f}%</b> of the variation over the last {o["days"]} days.',
                   f'Best-fit numbers: salinity adjusts within about <b>{p["tau"]:.1f} days</b>; each extra m³/s of river flow changes it by <b>{p["bq"]:+.2f} PSU</b>; each extra metre of tidal range by <b>{p["bt"]:+.1f} PSU</b>.',
                   ('<b>But</b> the honest error bars are still about as large as the numbers themselves, so treat them as starting guesses. More months, especially a spring freshet, will pin them down.' if weak
                    else 'The error bars are now small enough that these numbers are reasonably well determined.')],
            v=CARE, odelist=True, math=f'''<div class="formula">dS/dt = [S_eq + b_Q(Q − Q̄) + b_T(TR − T̄R) − S] / τ</div>
<p>Fitted by non-linear least squares to tide-filtered salinity (Godin 24-24-25 filter, sampled every 6 hours, up to the last 120 days). Q = USGS Cornish daily flow; TR = 25-hour tidal range at Camp Ellis.</p>
<p>The model's errors are strongly related from one step to the next (lag-1 correlation {p["r1"]:.2f}), so the error bars are widened by √((1 + r)/(1 − r)) ≈ {p["infl"]:.1f}. River flow and tidal range are correlated over this period (r = {o["corr_qtr"]:.2f}), so their effects are only partly separable.</p>''',
            charts=[('p17', ''), ('p17b', 'xs'), ('p17c', 'xs')], cap='Top: hourly salinity, tide-averaged salinity and the model. Middle: Saco River flow (USGS, provisional). Bottom: daily tidal range.')
        add(g='phys', t='Bigger tides, bigger salinity swings', w='Jordan Point · salinity range per tide vs tidal range', c=[MA, OC],
            plain='During one tide the water at the sensor slides back and forth. If the estuary gets saltier toward the sea, a bigger tide slides saltier water past the sensor, so the salinity swing grows. The steepness of this line shows how quickly salinity changes along the estuary.',
            read='Each dot is a day. Further right means a bigger tide; higher means a bigger salinity swing. The dashed line is the trend.',
            found=[f'Each extra metre of tidal range adds about <b>{o["slope"]:.0f} PSU</b> of salinity swing (correlation {o["r_sc"]:.2f}).', f'A typical tide swings salinity by <b>{o["med_swing"]:.0f} PSU</b>.'],
            v=OK, math='<p>Daily averages of the 13-hour maximum-minus-minimum of salinity and of water level. Neighbouring days overlap slightly, so the correlation is a little optimistic, but the relationship is strong and expected from physics: ΔS ≈ (∂S/∂x) × tidal excursion, and the excursion grows with tidal range.</p>',
            charts=[('p18', '')], cap='One dot per day. Line: least-squares fit.')
        add(g='phys', t='Estuary mixing calculator', w='Jordan Point · horizontal mixing and mixing regime', c=[MA, OC],
            plain='Two numbers describe how an estuary mixes. <b>K<sub>x</sub></b> says how fast salt spreads along the estuary. <b>Ri<sub>E</sub></b> says whether fresh water floats on top of salt water (layered) or the two are stirred together. Change the boxes to try other channel sizes.',
            read='Green tags are measured values (filled in from the latest data); orange tags are guesses until the channel is surveyed. Results update as you type.',
            found=[], calc=dict(q=o['Q30'] * 1.3, s=o['S_mean'], ds=o['med_swing'], so=o['S_ocean']),
            v=CARE, math='''<ul><li>Tidal excursion L = 2U/ω (how far water travels on one flood), ω = M2 frequency</li>
<li>Salinity gradient along the estuary ∂S/∂x ≈ ΔS_tide / L</li><li>Steady salt balance: K_x = Q·S / (A·∂S/∂x), A = width × depth</li>
<li>Estuarine Richardson number Ri_E = (g·Δρ/ρ)·Q / (W·U³), Δρ/ρ ≈ 7.7×10⁻⁴ × ΔS. Below 0.08 well mixed; 0.08–0.8 partially mixed; above 0.8 layered.</li></ul>
<p>Default river flow is the Cornish gauge (last 30 days) × 1.3, a rough allowance for the watershed below Cornish. Vertical mixing can't be measured with one sensor depth.</p>''',
            charts=[], cap='')
    return arrange(C)
