"""
core.py — the data engine behind the BlueSonde dashboard (site settings: site.json).
Reads data/sonde/*.csv and data/tide/*.csv, cleans them, and computes the tables,
statistics and plain-English findings used by the dashboard and spreadsheet.
"""
from __future__ import annotations

import glob
import json
import os
import re

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.environ.get('BUOY_DIR') or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFG = json.load(open(os.path.join(ROOT, 'site.json'), encoding='utf-8'))
DEV = CFG['device_name']
SITE_SHORT = CFG.get('short_name', DEV)
SITE_NAME = CFG.get('site_name', SITE_SHORT)
SITE_PHRASE = CFG.get('site_phrase', f'in {SITE_NAME}')
GITHUB_USER, GITHUB_REPO = CFG['github_user'], CFG['github_repo']
SITE_URL = CFG.get('site_url') or f'https://{GITHUB_USER}.github.io/{GITHUB_REPO}/'
REPO_URL = CFG.get('repo_url') or f'https://github.com/{GITHUB_USER}/{GITHUB_REPO}'
LOCAL_TZ = CFG.get('timezone', 'America/New_York')
SISTER_SITES = CFG.get('sister_sites', [])
FILE_STEM = CFG.get('file_stem') or (re.sub(r'[^A-Za-z0-9]+', '_', SITE_SHORT).strip('_') + '_BlueSonde')

DO_STRESS, DO_HYPOXIC = 5.0, 2.0      # mg/L
OUT_OF_WATER_SPCOND = float(CFG.get('out_of_water_spcond_uscm', 150))   # µS/cm; below this the sonde is in air
BLOOM_CHL = 10.0                      # µg/L — a common "elevated / bloom" screening level in coastal water

# name, units, plausible range (outside = sensor glitch), spike threshold (jump vs. neighbours)
PARAMS = {
    'temp_c':      ('Water temperature', '°C', (-2.5, 35), 2.0),
    'sal_psu':     ('Salinity', 'PSU', (0, 42), 6.0),
    'do_mgl':      ('Dissolved oxygen', 'mg/L', (0, 25), 3.0),
    'do_pct':      ('Oxygen saturation', '%', (0, 250), 30.0),
    'chl_ugl':     ('Chlorophyll', 'µg/L', (-0.5, 400), None),
    'turb_ntu':    ('Turbidity', 'NTU', (-1, 4000), None),
    'spcond_uscm': ('Specific conductivity', 'µS/cm', (0, 80000), 8000.0),
    'cond_uscm':   ('Conductivity', 'µS/cm', (0, 80000), 8000.0),
    'tds_ppt':     ('Total dissolved solids', 'ppt', (0, 60), 5.0),
    'batt_mv':     ('Battery diagnostic voltage (solar)', 'mV', (0, 20000), None),
    'batt_ma':     ('Battery current', 'mA', (-5000, 5000), None),
    'hull_rh':     ('Hull humidity', '%RH', (0, 100), None),
    'hull_c':      ('Hull temperature', '°C', (-30, 70), None),
    'chl_adc_v':   ('Chlorophyll sensor voltage', 'V', (-1, 10), None),
    'fluor_adc_v': ('Fluorometer voltage', 'V', (-1, 10), None),
    'solar_mv':    ('Solar diagnostic voltage', 'mV', (0, 20000), None),
    'trp_ppb':     ('Tryptophan (relative)', 'ppb', (-2000, 20000), None),
}
SCIENCE = ['temp_c', 'sal_psu', 'do_mgl', 'do_pct', 'chl_ugl', 'trp_ppb', 'turb_ntu', 'spcond_uscm', 'cond_uscm', 'tds_ppt']

# The "salinity vibe" — the Venice system for estuarine water, in plain words
FRESH_SRC = CFG.get('freshwater_source')   # e.g. 'the Saco River' — only where a river really reaches the buoy
SAL_VIBES = [(0.5, '🏞️', 'Fresh water', 'No sea salt — like rain, stream or pond water.'),
             (5, '🍃', 'Barely salty', 'Mostly fresh water with a hint of sea.'),
             (18, '🌫️', 'Brackish', 'A real mix of fresh water and seawater.'),
             (30, '🐚', 'Salty', 'Mostly seawater, slightly diluted by fresh water.'),
             (99, '🌊', 'Seawater', 'Full-strength ocean water.')]


def sal_vibe(s):
    for lim, e, n, d in SAL_VIBES:
        if s < lim:
            return e, n, d
    return SAL_VIBES[-1][1:]


def local(idx):
    return pd.DatetimeIndex(idx).tz_convert(LOCAL_TZ)


def c2f(c):
    return c * 9 / 5 + 32


def _read(pattern):
    fs = sorted(glob.glob(pattern))
    if not fs:
        return pd.DataFrame()
    df = pd.concat([pd.read_csv(f, index_col=0) for f in fs])
    df.index = pd.to_datetime(df.index, utc=True)
    df = df[~df.index.duplicated(keep='last')].sort_index()
    return df


def load(data_dir):
    raw = _read(os.path.join(data_dir, 'sonde', f'{DEV}_*.csv'))
    tide = _read(os.path.join(data_dir, 'tide', 'tide_*.csv'))
    if 'res' not in raw:
        raw['res'] = 'full'
    dep = CFG.get('deployed_utc')
    if dep and len(raw):
        raw = raw[raw.index >= pd.Timestamp(dep)]
    df, removed = clean(raw)
    tide_s = tide['water_level_m'] if 'water_level_m' in tide else pd.Series(dtype=float)
    return {'raw': raw, 'df': df, 'removed': removed, 'tide': tide_s}


def clean(raw):
    """Drop impossible values and isolated one-reading spikes. Returns (clean frame, {col: n removed})."""
    df = raw.copy()
    removed = {}
    # out of the water (maintenance, on deck): conductivity collapses to ~0. Drop every science reading then,
    # plus anything within 45 min either side (lifting out / putting back in).
    oow = pd.Series(False, index=df.index)
    if 'spcond_uscm' in df:
        sc = pd.to_numeric(df['spcond_uscm'], errors='coerce')
        air = (sc < OUT_OF_WATER_SPCOND).fillna(False)
        if air.any():
            t = df.index[air]
            pos = t.searchsorted(df.index)
            near = np.minimum(abs(df.index - t[(pos - 1).clip(0, len(t) - 1)]), abs(df.index - t[pos.clip(0, len(t) - 1)]))
            oow = pd.Series(near <= pd.Timedelta(minutes=45), index=df.index)
            df.loc[oow, [c for c in SCIENCE if c in df]] = np.nan
    removed['out_of_water'] = int(oow.sum())
    for c in df.columns:
        if c == 'res':
            continue
        df[c] = pd.to_numeric(df[c], errors='coerce')
        lo, hi = PARAMS.get(c, (None, None, (-np.inf, np.inf), None))[2]
        bad = (df[c] < lo) | (df[c] > hi)
        thr = PARAMS.get(c, (None, None, None, None))[3]
        if thr:
            s = df[c]
            prev, nxt = s.shift(1), s.shift(-1)
            # a spike: far from both neighbours, while the neighbours agree with each other
            spike = ((s - prev).abs() > thr) & ((s - nxt).abs() > thr) & ((prev - nxt).abs() < thr / 2)
            bad |= spike.fillna(False)
        removed[c] = int(bad.sum())
        df.loc[bad, c] = np.nan
    for c in ['chl_ugl', 'turb_ntu']:      # small negative readings are offset noise → treat as zero
        if c in df:
            df[c] = df[c].clip(lower=0)
    for c in ['solar_mv', 'batt_mv']:          # one "solar/battery diagnostic" voltage, whichever the sonde reports
        if c in df and df[c].notna().any():
            df['volt_v'] = df[c] / 1000
            break
    return df, removed


def hourly(df):
    num = df.drop(columns=['res'], errors='ignore')
    return num.resample('1h').mean().dropna(how='all')


def daily(df):
    num = df.drop(columns=['res'], errors='ignore')
    L = num.copy()
    L.index = local(L.index)
    g = L.resample('1D')
    out = pd.DataFrame(index=g.mean().index.date)
    for c in [c for c in SCIENCE if c in num]:
        out[f'{c}_mean'] = g[c].mean().values
        out[f'{c}_min'] = g[c].min().values
        out[f'{c}_max'] = g[c].max().values
    out['n_readings'] = g[num.columns[0]].count().values if len(num.columns) else 0
    out.index.name = 'date'
    return out[out['n_readings'] > 0]


def monthly(df):
    num = df.drop(columns=['res'], errors='ignore')
    L = num.copy()
    L.index = local(L.index).tz_localize(None)
    rows = []
    for p, g in L.groupby(L.index.to_period('M')):
        r = {'month': str(p), 'label': p.strftime('%b %Y'), 'readings': len(g),
             'days_with_data': g.index.normalize().nunique(), 'days_in_month': p.days_in_month}
        for c in [c for c in SCIENCE if c in g]:
            r[f'{c}_mean'], r[f'{c}_min'], r[f'{c}_max'] = g[c].mean(), g[c].min(), g[c].max()
        if 'do_mgl' in g:
            v = g['do_mgl'].dropna()
            r['pct_time_do_below_5'] = 100 * (v < DO_STRESS).mean() if len(v) else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def tide_highs(tide, hilo=None):
    """High-tide times (UTC). Prefer NOAA predictions; fall back to peaks in the hourly water level."""
    if hilo:
        hs = [pd.Timestamp(x['t']).tz_localize(LOCAL_TZ).tz_convert('UTC') for x in hilo if x.get('type') == 'H']
        if hs:
            return pd.DatetimeIndex(hs)
    t = tide.dropna()
    if len(t) < 30:
        return pd.DatetimeIndex([])
    sm = t.rolling(3, center=True).mean()
    pk = sm[(sm > sm.shift(1)) & (sm >= sm.shift(-1)) & (sm > sm.rolling(13, center=True, min_periods=5).median())]
    keep = []
    for ts in pk.index:                      # one high per ~12.4 h
        if not keep or ts - keep[-1] > pd.Timedelta(hours=8):
            keep.append(ts)
    return pd.DatetimeIndex(keep)


def tide_phase(df, highs):
    """Hours since the nearest high tide (−6.2 … +6.2) for every reading."""
    if not len(highs):
        return pd.Series(np.nan, index=df.index)
    h = highs.sort_values()
    pos = h.searchsorted(df.index)
    a = h[(pos - 1).clip(0, len(h) - 1)]
    b = h[pos.clip(0, len(h) - 1)]
    da = (df.index - a) / pd.Timedelta(hours=1)
    db = (df.index - b) / pd.Timedelta(hours=1)
    ph = np.where(np.abs(da) < np.abs(db), da, db)
    ph = pd.Series(ph, index=df.index)
    return ph.where(ph.abs() <= 6.5)


def phase_table(df, ph, bin_h=0.5):
    cols = [c for c in ['sal_psu', 'temp_c', 'do_pct', 'turb_ntu', 'chl_ugl'] if c in df]
    d = df[cols].copy()
    d['phase'] = (ph / bin_h).round() * bin_h
    d = d.dropna(subset=['phase'])
    q25 = lambda x: x.quantile(.25)
    q75 = lambda x: x.quantile(.75)
    q25.__name__, q75.__name__ = 'q25', 'q75'
    q50 = lambda x: x.quantile(.5)
    q50.__name__ = 'q50'
    return d.groupby('phase').agg(['mean', 'count', q25, q50, q75])


def summary(B, hilo=None):
    df, tide = B['df'], B['tide']
    S = {'df': df, 'tide': tide, 'removed': B['removed']}
    if not len(df):
        S['empty'] = True
        return S
    S['hourly'] = hourly(df)
    S['daily'] = daily(df)
    S['monthly'] = monthly(df)
    highs = tide_highs(tide, hilo)
    S['phase'] = tide_phase(df, highs)
    S['phase_tab'] = phase_table(df, S['phase'])
    L = df.copy()
    L.index = local(L.index)
    S['diel'] = L.groupby(L.index.hour)[[c for c in ['do_pct', 'temp_c', 'chl_ugl'] if c in L]].mean()
    S['diel_q25'] = L.groupby(L.index.hour)[list(S['diel'].columns)].quantile(.25)     # typical range for the rhythm chart
    S['diel_q50'] = L.groupby(L.index.hour)[list(S['diel'].columns)].quantile(.5)
    S['diel_q75'] = L.groupby(L.index.hour)[list(S['diel'].columns)].quantile(.75)
    latest = {}
    for c in df.columns:
        if c == 'res':
            continue
        s = df[c].dropna()
        if len(s):
            latest[c] = (float(s.iloc[-1]), s.index[-1])
    first, last = df.index.min(), df.index.max()
    st = {'first': local([first])[0], 'last': local([last])[0], 'days': (last - first) / pd.Timedelta(days=1),
          'n': len(df), 'n_full': int((B['raw']['res'] == 'full').sum()) if 'res' in B['raw'] else len(df),
          'latest': latest}
    for c in [c for c in SCIENCE + ['volt_v', 'hull_rh'] if c in df]:
        s = df[c].dropna()
        if len(s):
            st[c] = {'mean': s.mean(), 'min': s.min(), 'max': s.max(), 'tmin': local([s.idxmin()])[0],
                     'tmax': local([s.idxmax()])[0], 'median': s.median(), 'n': len(s)}
    hrs = pd.date_range(first.floor('h'), last.floor('h'), freq='1h')
    st['coverage_pct'] = 100 * len(S['hourly'].index.intersection(hrs)) / max(len(hrs), 1)
    S['stats'] = st
    return S


def fmt_t(t):
    return f'{t:%b %d} at {t:%I:%M %p}'.replace(' 0', ' ')


def insights(S):
    st, df = S['stats'], S['df']
    out = []
    pt = S.get('phase_tab')
    # 1) tide
    if pt is not None and len(pt) and ('sal_psu', 'mean') in pt:
        sal = pt[('sal_psu', 'mean')][pt[('sal_psu', 'count')] >= 8]
        if len(sal) >= 8:
            lo_ph, hi_ph = sal.idxmin(), sal.idxmax()
            rng = sal.max() - sal.min()
            if rng >= 1:
                out.append(('🌙', f'The tide sets the salt: {rng:.1f} PSU swing',
                            f'On average the water is saltiest about {abs(hi_ph):.1f} h {"after" if hi_ph >= 0 else "before"} high tide '
                            f'({sal.max():.1f} PSU) and freshest about {abs(lo_ph):.1f} h {"after" if lo_ph >= 0 else "before"} high tide '
                            f'({sal.min():.1f} PSU), when the falling tide carries fresher water ' + (f'from {FRESH_SRC} ' if FRESH_SRC else 'from closer to shore ') + 'past the buoy.'))
            else:
                out.append(('🌙', 'Seawater rules here — the tide barely changes the salt',
                            f'Averaged over each tide cycle, salinity only shifts by {rng:.1f} PSU between high and low water. '
                            'Fresh water mostly reaches the buoy after heavy rain — watch for the dips in the salinity chart.'))
    # 2) freshest moment
    if 'sal_psu' in st:
        s = st['sal_psu']
        e, n, _ = sal_vibe(s['min'])
        out.append(('💧', f'Freshest moment: {s["min"]:.1f} PSU ({n.lower()})',
                    f'Recorded {fmt_t(s["tmin"])}. Typical salinity is {s["median"]:.1f} PSU '
                    f'(full seawater is about 32–35). Sharp dips usually follow heavy rain, when ' + (f'{FRESH_SRC} and runoff carry' if FRESH_SRC else 'streams and runoff carry') + ' fresh water out to the buoy.'))
    # 3) temperature trend
    if 'temp_c' in df:
        T = df['temp_c'].dropna()
        end = T.index.max()
        a = T[T.index > end - pd.Timedelta(days=7)].mean()
        b = T[(T.index <= end - pd.Timedelta(days=7)) & (T.index > end - pd.Timedelta(days=14))]
        if len(b) > 50:
            d = a - b.mean()
            word = 'warming' if d > 0.3 else ('cooling' if d < -0.3 else 'holding steady')
            out.append(('🌡️', f'Water is {word}: {d:+.1f} °C ({d * 9 / 5:+.1f} °F) in a week',
                        f'Average water temperature this past week was {a:.1f} °C ({c2f(a):.0f} °F), versus {b.mean():.1f} °C '
                        f'({c2f(b.mean()):.0f} °F) the week before. Warmest so far: {st["temp_c"]["max"]:.1f} °C on '
                        f'{st["temp_c"]["tmax"]:%b %d}; coldest {st["temp_c"]["min"]:.1f} °C on {st["temp_c"]["tmin"]:%b %d}.'))
    # 4) oxygen
    if 'do_mgl' in df:
        v = df['do_mgl'].dropna()
        if len(v):
            low = 100 * (v < DO_STRESS).mean()
            out.append(('🫧', 'Oxygen is healthy for fish' if low < 1 else f'Oxygen dipped below 5 mg/L {low:.0f}% of the time',
                        f'Dissolved oxygen averaged {v.mean():.1f} mg/L and never went below {v.min():.1f} mg/L '
                        f'(lowest {fmt_t(local([v.idxmin()])[0])}). Below 5 mg/L many fish start to feel stressed; '
                        'below 2 mg/L (hypoxia) most can\'t stay.'))
    # 5) daily rhythm
    if 'do_pct' in df:
        L = df['do_pct'].copy()
        L.index = local(L.index)
        dd = L.resample('1D').agg(['max', 'min', 'count'])
        dd = dd[dd['count'] >= 40]
        if len(dd) >= 3:
            swing = (dd['max'] - dd['min']).median()
            di = S['diel'].get('do_pct')
            peak = int(di.idxmax()) if di is not None and di.notna().any() else None
            out.append(('☀️', f'The water breathes every day: ~{swing:.0f}% oxygen swing',
                        'Algae add oxygen in daylight and everything uses it up at night. On a typical day oxygen saturation '
                        f'swings by about {swing:.0f} percentage points' +
                        (f', peaking around {(peak % 12) or 12} {"AM" if peak < 12 else "PM"}.' if peak is not None else '.')))
    # 6) chlorophyll
    if 'chl_ugl' in st:
        c = st['chl_ugl']
        hi = c['max'] >= BLOOM_CHL
        out.append(('🌿', f'Chlorophyll peaked at {c["max"]:.1f} µg/L' + (' — a bloom-level reading' if hi else ''),
                    f'Chlorophyll is a stand-in for how much floating algae (phytoplankton) is in the water. Typical here: '
                    f'{c["median"]:.1f} µg/L; highest {fmt_t(c["tmax"])}. Readings above ~{BLOOM_CHL:g} µg/L in coastal water '
                    'usually mean a bloom.'))
    # 6b) tryptophan
    if 'trp_ppb' in df:
        v = df['trp_ppb'].dropna()
        if len(v) > 50:
            L = v.copy()
            L.index = local(L.index)
            base = v.median()
            q = v.quantile([0.05, 0.95])
            out.append(('🔬', f'Tryptophan signal: typical {base:.0f}, range {q.iloc[0]:.0f} to {q.iloc[1]:.0f} ppb',
                        'Tryptophan-like fluorescence glows brighter when there is more fresh organic matter in the water, '
                        'including wastewater and runoff, so it is used as an early warning for contamination. '
                        + ('This sensor reads below zero, so treat the numbers as relative: what matters is a rise above its usual level. '
                           if base < 0 else '')
                        + f'Highest reading: {v.max():.0f} ppb on {fmt_t(local([v.idxmax()])[0])}.'))
    # 7) turbidity
    if 'turb_ntu' in st:
        t = st['turb_ntu']
        out.append(('🟤', f'Clearest vs. muddiest: {t["median"]:.1f} NTU typical, {t["max"]:.0f} NTU max',
                    f'Turbidity measures how cloudy the water is. Under ~5 NTU is clear coastal water; spikes (highest '
                    f'{fmt_t(t["tmax"])}) come from storms stirring up sediment, runoff after rain, or now and then something '
                    'drifting past the sensor.'))
    return out


def qc_notes(S):
    rm = {k: v for k, v in S['removed'].items() if v and k != 'out_of_water'}
    oow = S['removed'].get('out_of_water', 0)
    notes = [f'Removed as sensor glitches (impossible values, or single-reading spikes far from both neighbours): '
             + (', '.join(f'{PARAMS.get(k, (k,))[0].lower()} {v:,}' for k, v in rm.items()) if rm else 'none so far') + '.',
             f'Out of the water: {oow:,} readings were dropped because conductivity fell below {OUT_OF_WATER_SPCOND:g} µS/cm — '
             'the sonde reading air (maintenance or recovery), not real water. Readings within 45 minutes either side are dropped too.',
             'Small negative chlorophyll and turbidity readings (sensor offset in very clear water) are shown as zero.',
             'CUMULUS publishes the last 7 days at full resolution (about every 15 minutes) and 30 days as ~45-minute averages. '
             'This site saves the full-resolution readings every hour; averages are only used to fill time before the site started.',
             'Optical sensors (chlorophyll, turbidity) can drift upward as marine growth builds up between cleanings — '
             'a slow steady climb followed by a sudden drop is usually a cleaning, not the water changing.',
             'Tryptophan readings are shown as reported by CUMULUS. Values below zero mean the sensor is not calibrated to an '
             'absolute scale, so compare readings with each other rather than with published thresholds.',
             'The "battery/solar diagnostic voltage" reads 0 V every night and rises with the sun, so it appears to track the solar '
             'charger rather than the battery itself.',
             'The water-level line comes from CUMULUS (the nearest NOAA tide gauge), not from the buoy itself.']
    if 'trp_ppb' not in S['df']:
        notes = [n for n in notes if not n.startswith('Tryptophan')]
    if S['stats'].get('n_full', 0) < S['stats']['n']:
        notes.append(f"{S['stats']['n'] - S['stats']['n_full']:,} of the readings are CUMULUS ~45-minute averages (before full-resolution "
                     'saving started).')
    return notes
