"""
core.py — data engine for UNE weather / environmental station pages (settings: <station>/site.json).
Every measurement is described in site.json → "vars" (ArcGIS field, our key, label, unit, how to convert
for US units, how to summarise), so one code base serves the weather stations, the marsh and the pond.
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
SITE_SHORT = CFG['short_name']
SITE_NAME = CFG.get('site_name', SITE_SHORT)
SITE_PHRASE = CFG.get('site_phrase', f'at {SITE_NAME}')
GITHUB_USER, GITHUB_REPO = CFG['github_user'], CFG['github_repo']
SITE_URL = CFG.get('site_url') or f'https://{GITHUB_USER}.github.io/{GITHUB_REPO}/'
REPO_URL = CFG.get('repo_url') or f'https://github.com/{GITHUB_USER}/{GITHUB_REPO}'
LOCAL_TZ = CFG.get('timezone', 'America/New_York')
SISTER_SITES = CFG.get('sister_sites', [])
FILE_STEM = CFG.get('file_stem') or re.sub(r'[^A-Za-z0-9]+', '_', SITE_SHORT).strip('_') + '_Station'
VARS = CFG['vars']
VBY = {v['key']: v for v in VARS}
DO_STRESS, DO_HYPOXIC = 5.0, 2.0


def local(idx):
    return pd.DatetimeIndex(idx).tz_convert(LOCAL_TZ)


def c2f(c):
    return c * 9 / 5 + 32


def load(data_dir):
    fs = sorted(glob.glob(os.path.join(data_dir, 'obs', 'obs_*.csv')))
    if not fs:
        return pd.DataFrame(), {}
    raw = pd.concat([pd.read_csv(f, index_col=0) for f in fs])
    raw.index = pd.to_datetime(raw.index, utc=True)
    raw = raw[~raw.index.duplicated(keep='last')].sort_index()
    df = pd.DataFrame(index=raw.index)
    removed = {}
    for v in VARS:
        if v['field'] not in raw:
            continue
        s = pd.to_numeric(raw[v['field']], errors='coerce') * v.get('scale', 1)
        lo, hi = v.get('range', [-1e9, 1e9])
        bad = (s < lo) | (s > hi)
        removed[v['key']] = int(bad.sum())
        df[v['key']] = s.where(~bad)
    return df.dropna(how='all'), removed


def circ_mean(deg, w=None):
    d = np.radians(np.asarray(deg, float))
    ok = np.isfinite(d)
    if not ok.any():
        return np.nan
    w = np.ones_like(d) if w is None else np.asarray(w, float)
    return float(np.degrees(np.arctan2((np.sin(d) * w)[ok].sum(), (np.cos(d) * w)[ok].sum())) % 360)


def resample(df, rule):
    out = {}
    for v in VARS:
        k = v['key']
        if k not in df:
            continue
        g = df[k].resample(rule)
        if v.get('agg') == 'sum':
            out[k] = g.sum(min_count=1)
        elif v.get('agg') == 'dir':
            out[k] = g.apply(lambda x: circ_mean(x.values) if len(x.dropna()) else np.nan)
        else:
            out[k] = g.mean()
    return pd.DataFrame(out).dropna(how='all')


def daily(df):
    L = df.copy()
    L.index = local(L.index)
    rows = {}
    g = L.resample('1D')
    for v in VARS:
        k = v['key']
        if k not in L or v.get('agg') == 'dir':
            continue
        if v.get('agg') == 'sum':
            rows[f'{k}_total'] = g[k].sum(min_count=1)
        else:
            rows[f'{k}_mean'], rows[f'{k}_min'], rows[f'{k}_max'] = g[k].mean(), g[k].min(), g[k].max()
    out = pd.DataFrame(rows)
    out['n_readings'] = g.size()
    out.index = out.index.date
    out.index.name = 'date'
    return out[out['n_readings'] > 0]


def monthly(df):
    L = df.copy()
    L.index = local(L.index).tz_localize(None)
    rows = []
    for p, g in L.groupby(L.index.to_period('M')):
        r = {'month': str(p), 'label': p.strftime('%b %Y'), 'days_with_data': g.index.normalize().nunique(), 'days_in_month': p.days_in_month}
        for v in VARS:
            k = v['key']
            if k not in g or v.get('agg') == 'dir' or g[k].notna().sum() == 0:
                continue
            if v.get('agg') == 'sum':
                r[f'{k}_total'] = g[k].sum()
            else:
                r[f'{k}_mean'], r[f'{k}_min'], r[f'{k}_max'] = g[k].mean(), g[k].min(), g[k].max()
        rows.append(r)
    return pd.DataFrame(rows)


def summary(df, removed):
    S = {'df': df, 'removed': removed, 'hourly': resample(df, '1h'), 'daily': daily(df), 'monthly': monthly(df)}
    latest = {}
    for c in df.columns:
        s = df[c].dropna()
        if len(s):
            latest[c] = (float(s.iloc[-1]), s.index[-1])
    st = {'first': local([df.index.min()])[0], 'last': local([df.index.max()])[0], 'n': len(df), 'latest': latest,
          'days': (df.index.max() - df.index.min()) / pd.Timedelta(days=1)}
    now = pd.Timestamp.now(tz=LOCAL_TZ)
    L = df.copy()
    L.index = local(L.index)
    today = L[L.index >= now.normalize()]
    last24 = df[df.index > df.index.max() - pd.Timedelta(hours=24)]
    st['today'], st['last24'] = {}, {}
    for v in VARS:
        k = v['key']
        if k not in df:
            continue
        s = df[k].dropna()
        if not len(s):
            continue
        if v.get('agg') == 'sum':
            st[k] = {'total': s.sum()}
            st['today'][k] = {'total': today[k].sum() if k in today else np.nan}
            st['last24'][k] = {'total': last24[k].sum()}
            dsum = S['daily'].get(f'{k}_total')
            if dsum is not None and dsum.notna().any():
                st[k].update(wettest=dsum.max(), wettest_day=dsum.idxmax())
        elif v.get('agg') != 'dir':
            st[k] = {'mean': s.mean(), 'min': s.min(), 'max': s.max(), 'median': s.median(),
                     'tmin': local([s.idxmin()])[0], 'tmax': local([s.idxmax()])[0]}
            t = today[k].dropna() if k in today else pd.Series(dtype=float)
            st['today'][k] = {'min': t.min(), 'max': t.max()} if len(t) else {}
    S['stats'] = st
    return S


# ---------- formatting helpers (Python side; the page converts units on the fly) ----------
def fmt(v, key, us=True, dec=None):
    """Plain text value in the default (US) units, used in the written findings."""
    if v is None or not np.isfinite(v):
        return '—'
    conv = VBY.get(key, {}).get('conv')
    if conv == 'temp':
        return f'{c2f(v):.0f} °F ({v:.1f} °C)'
    if conv == 'speed':
        return f'{v * 2.23694:.0f} mph ({v:.1f} m/s)'
    if conv == 'rain':
        return f'{v / 25.4:.2f} in ({v:.1f} mm)'
    if conv == 'len':
        return f'{v * 3.28084:.1f} ft ({v:.2f} m)'
    u = VBY.get(key, {}).get('unit', '')
    d = dec if dec is not None else VBY.get(key, {}).get('dec', 1)
    return f'{v:.{d}f}{"" if u == "%" else " "}{u}'.strip()


def when(t):
    return f'{t:%b %d} at {t:%I:%M %p}'.replace(' 0', ' ')


def insights(S):
    st, df = S['stats'], S['df']
    out = []
    if 'air_temp_c' in st:
        a = st['air_temp_c']
        out.append(('🌡️', f'Temperature range so far: {fmt(a["min"], "air_temp_c").split(" (")[0]} to {fmt(a["max"], "air_temp_c").split(" (")[0]}',
                    f'Warmest {fmt(a["max"], "air_temp_c")} on {when(a["tmax"])}; coldest {fmt(a["min"], "air_temp_c")} on {when(a["tmin"])}.'))
    for k in ['rain_mm']:
        if k in st and 'wettest' in st[k]:
            r = st[k]
            out.append(('🌧️', f'Wettest day: {fmt(r["wettest"], k).split(" (")[0]}',
                        f'{pd.Timestamp(r["wettest_day"]):%A, %b %d, %Y}. Total since records began here: {fmt(r["total"], k)}. '
                        f'Last 24 hours: {fmt(st["last24"][k]["total"], k)}.'))
    if 'gust_ms' in st:
        g = st['gust_ms']
        out.append(('💨', f'Strongest gust: {fmt(g["max"], "gust_ms").split(" (")[0]}',
                    f'Recorded {when(g["tmax"])}. Typical wind here: {fmt(st.get("wind_ms", {}).get("median", np.nan), "wind_ms")}.'))
    if 'do_mgl' in df:
        v = df['do_mgl'].dropna()
        if len(v):
            hyp, low = 100 * (v < DO_HYPOXIC).mean(), 100 * (v < DO_STRESS).mean()
            head = ('Oxygen is often very low (hypoxic)' if hyp > 10 else
                    'Oxygen sometimes dips to stressful levels' if low > 5 else 'Oxygen is healthy')
            out.append(('🫧', head,
                        f'Dissolved oxygen averaged {v.mean():.1f} mg/L. It was below 2 mg/L (hypoxic — too little for most fish) '
                        f'{hyp:.0f}% of the time and below 5 mg/L (stressful) {low:.0f}% of the time. '
                        'Still, warm, shallow ponds and marshes naturally run low on oxygen, especially at night and in late summer.'))
    if 'sal_psu' in st:
        s = st['sal_psu']
        out.append(('💧', f'Salinity {s["min"]:.1f}–{s["max"]:.1f} PSU (typical {s["median"]:.1f})',
                    'For comparison, ocean water is about 32–35 PSU and drinking water is about 0. '
                    'Values in between mean a mix of fresh water (rain, streams, groundwater) and seawater.'))
    if 'water_level_m' in st:
        w = st['water_level_m']
        out.append(('🌊', f'Water level range: {(w["max"] - w["min"]) * 3.28084:.1f} ft',
                    f'From {fmt(w["min"], "water_level_m")} to {fmt(w["max"], "water_level_m")} relative to the sensor’s reference level. '
                    'Highest on ' + f'{w["tmax"]:%b %d, %Y}.'))
    if 'soil_moist_15' in st:
        s = st['soil_moist_15']
        out.append(('🌱', f'Topsoil moisture: {s["median"]:.0f}% water by volume (typical)',
                    f'Ranged {s["min"]:.0f}–{s["max"]:.0f}%. It jumps after rain and slowly dries out as plants pull water up '
                    'and it drains deeper.'))
    if 'water_temp_c' in st:
        w = st['water_temp_c']
        out.append(('🌡️', f'Water temperature {fmt(w["min"], "water_temp_c").split(" (")[0]} to {fmt(w["max"], "water_temp_c").split(" (")[0]}',
                    f'Warmest {when(w["tmax"])}; coldest {when(w["tmin"])}.'))
    return out[:6]
