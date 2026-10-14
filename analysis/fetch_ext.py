"""
fetch_ext.py — keeps the outside reference records used by the Analysis page up to date (run once a day).
All sources are public and keyless. Results are small CSVs in analysis/ext/:

  portland_monthly.csv   NOAA tide gauge 8418150 (Portland, ME): monthly mean/highest water since 1912
  portland_hourly.csv    the same gauge, hourly measured water and predicted tide, last ~400 days
  ndbc44007_daily.csv    NOAA buoy 44007 (off Portland): daily water temperature and wave height since 1990
  ndbc44007_hourly.csv   the same buoy, hourly, last ~400 days
  saco_daily.csv         USGS 01066000 Saco River at Cornish: daily mean flow since 1916
  portland_air.csv       NOAA GHCN-Daily, Portland Jetport: daily max/min temperature and rain since 1991

Usage:  python analysis/fetch_ext.py            (download / update)
        python analysis/fetch_ext.py --raw DIR  (rebuild from previously downloaded raw files, for testing)
Each source is independent: one failing never stops the others, and old files are kept.
"""
import argparse
import gzip
import io
import os
import sys
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'ext')
UA = {'User-Agent': 'UNE-marine-monitoring/1.0 (github.com/ekelting/UNE-Marine-Monitoring-Network)'}
TODAY = pd.Timestamp.now(tz='UTC').tz_localize(None).normalize()
problems = []


def get(url, tries=3):
    err = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(5 * (i + 1))
    raise err


def save(df, name):
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(os.path.join(OUT, name), index=False)
    print(f'  ✓ {name}: {len(df):,} rows')


def old(name):
    p = os.path.join(OUT, name)
    return pd.read_csv(p) if os.path.exists(p) else None


def step(name, fn):
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        problems.append(f'{name}: {e}')
        print(f'::warning::{name} not updated: {e}')


# ---------------------------------------------------------------- NOAA CO-OPS Portland
CO = 'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?'


def coops(product, begin, end, extra=''):
    q = dict(product=product, station='8418150', begin_date=begin, end_date=end, datum='MLLW', units='metric',
             time_zone='gmt', format='csv', application='UNE_MMN')
    return pd.read_csv(io.BytesIO(get(CO + urllib.parse.urlencode(q) + extra)), skipinitialspace=True)


def clean_cols(df):
    df.columns = [c.strip() for c in df.columns]
    return df


def monthly(raw=None):
    if raw:
        m = clean_cols(pd.read_csv(raw, skipinitialspace=True))
    else:
        parts = [coops('monthly_mean', a, b) for a, b in
                 [('19120101', '19611231'), ('19620101', '20111231'), ('20120101', TODAY.strftime('%Y%m%d'))]]
        m = clean_cols(pd.concat(parts))
    save(m[['Year', 'Month', 'Highest', 'MHHW', 'MSL']], 'portland_monthly.csv')


def hourly(raw_obs=None, raw_pred=None):
    if raw_obs:
        ob = clean_cols(pd.read_csv(raw_obs, skipinitialspace=True)); pr = clean_cols(pd.read_csv(raw_pred, skipinitialspace=True))
    else:
        start = TODAY - pd.Timedelta(days=400); mid = start + pd.Timedelta(days=200)
        rng = [(start, mid), (mid + pd.Timedelta(days=1), TODAY)]
        ob = clean_cols(pd.concat([coops('hourly_height', a.strftime('%Y%m%d'), b.strftime('%Y%m%d')) for a, b in rng]))
        pr = clean_cols(pd.concat([coops('predictions', a.strftime('%Y%m%d'), b.strftime('%Y%m%d'), '&interval=h') for a, b in rng]))
        # hourly_height lags a few weeks behind; top up with 6-minute data for the most recent month
        try:
            wl = clean_cols(coops('water_level', (TODAY - pd.Timedelta(days=30)).strftime('%Y%m%d'), TODAY.strftime('%Y%m%d')))
            wl['t'] = pd.to_datetime(wl['Date Time'])
            wl = wl[wl.t.dt.minute == 0][['Date Time', 'Water Level']]
            ob = pd.concat([ob[['Date Time', 'Water Level']], wl])
        except Exception as e:  # noqa: BLE001
            print(f'  (recent 6-minute top-up skipped: {e})')
    o = pd.Series(pd.to_numeric(ob['Water Level'], errors='coerce').values, index=pd.to_datetime(ob['Date Time']))
    p = pd.Series(pd.to_numeric(pr['Prediction'], errors='coerce').values, index=pd.to_datetime(pr['Date Time']))
    o = o[~o.index.duplicated(keep='first')]; p = p[~p.index.duplicated()]
    df = pd.concat([o.rename('obs_m'), p.rename('pred_m')], axis=1).sort_index()
    df.index.name = 'time_utc'
    save(df.reset_index().assign(time_utc=lambda d: d.time_utc.dt.strftime('%Y-%m-%dT%H:%MZ')), 'portland_hourly.csv')
    # keep the daily-highest-water record (since 1912) up to date for the flood-days chart
    loc = o.copy(); loc.index = loc.index.tz_localize('UTC').tz_convert('America/New_York').tz_localize(None)
    dm = loc.resample('D').agg(['max', 'count']); dm = dm[dm['count'] >= 20]['max'].round(3)
    p = os.path.join(OUT, 'portland_daymax.csv')
    if os.path.exists(p):
        old_dm = pd.read_csv(p, parse_dates=['date']).set_index('date').max_m
        dm = pd.concat([old_dm[old_dm.index < dm.index.min()], dm])
    dm.index.name = 'date'; dm.name = 'max_m'
    dm.reset_index().assign(date=lambda d: d.date.dt.strftime('%Y-%m-%d')).to_csv(p, index=False)
    print(f'  ✓ portland_daymax.csv: {len(dm):,} days')


# ---------------------------------------------------------------- NDBC 44007
NB = 'https://www.ndbc.noaa.gov/view_text_file.php?'


def parse_ndbc(text):
    lines = text.splitlines()
    hdr = lines[0].lstrip('#').split()
    rows = [l.split() for l in lines if l and not l.startswith('#') and not l.startswith('YY')]
    if not rows:
        return pd.DataFrame(columns=['wvht', 'wtmp'])
    n = len(rows[0]); rows = [r for r in rows if len(r) == n]
    if n == len(hdr) + 1:
        hdr = hdr[:4] + ['mm'] + hdr[4:]
    df = pd.DataFrame(rows, columns=hdr[:n])
    yy = df.iloc[:, 0].astype(int); yy = np.where(yy < 100, yy + 1900, yy)
    t = pd.to_datetime(dict(year=yy, month=df.iloc[:, 1].astype(int), day=df.iloc[:, 2].astype(int), hour=df.iloc[:, 3].astype(int)))
    g = pd.DataFrame({'wvht': pd.to_numeric(df['WVHT'], errors='coerce').values,
                      'wtmp': pd.to_numeric(df['WTMP'], errors='coerce').values}, index=pd.DatetimeIndex(t))
    g.loc[g.wvht >= 99, 'wvht'] = np.nan
    g.loc[(g.wtmp >= 99) | (g.wtmp < -3), 'wtmp'] = np.nan
    return g


def ndbc(raw=None):
    frames = []
    have = old('ndbc44007_daily.csv')
    have_years = set(pd.to_datetime(have.date).dt.year) if have is not None else set()
    if raw:
        import glob
        for f in sorted(glob.glob(os.path.join(raw, '44007_*.txt.gz'))):
            frames.append(parse_ndbc(gzip.open(f, 'rt').read()))
    else:
        for y in range(1990, TODAY.year):
            if y in have_years and y < TODAY.year - 1:
                continue
            try:
                frames.append(parse_ndbc(get(NB + f'filename=44007h{y}.txt.gz&dir=data/historical/stdmet/').decode()))
            except Exception as e:  # noqa: BLE001
                print(f'  44007 {y}: {e}')
        mons = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        for m in range(1, TODAY.month):
            code = '123456789abc'[m - 1]
            try:
                frames.append(parse_ndbc(get(NB + f'filename=44007{code}{TODAY.year}.txt.gz&dir=data/stdmet/{mons[m-1]}/').decode()))
            except Exception:  # noqa: BLE001
                pass                                    # recent months appear on NDBC with a delay
        frames.append(parse_ndbc(get('https://www.ndbc.noaa.gov/data/realtime2/44007.txt').decode()))
    h = pd.concat(frames)
    h = h[~h.index.duplicated(keep='last')].sort_index().resample('h').mean()
    d = h.resample('D').agg({'wtmp': 'mean', 'wvht': ['mean', 'max', 'count']})
    d.columns = ['wtmp_c', 'wvht_mean_m', 'wvht_max_m', 'wvht_n']
    d = d.dropna(how='all', subset=['wtmp_c', 'wvht_mean_m'])
    d.index.name = 'date'
    d = d.reset_index(); d['date'] = d.date.dt.strftime('%Y-%m-%d')
    if have is not None:
        d = pd.concat([have, d]).drop_duplicates('date', keep='last').sort_values('date')
    save(d.round(3), 'ndbc44007_daily.csv')
    rec = h[h.index >= TODAY - pd.Timedelta(days=400)].dropna(how='all')
    oldh = old('ndbc44007_hourly.csv')
    rec = rec.reset_index().rename(columns={'index': 'time_utc'})
    rec['time_utc'] = rec.time_utc.dt.strftime('%Y-%m-%dT%H:%MZ')
    if oldh is not None:
        rec = pd.concat([oldh, rec]).drop_duplicates('time_utc', keep='last').sort_values('time_utc')
        rec = rec[pd.to_datetime(rec.time_utc).dt.tz_localize(None) >= TODAY - pd.Timedelta(days=400)]
    save(rec.round(3), 'ndbc44007_hourly.csv')


# ---------------------------------------------------------------- USGS Saco River
def usgs(raw=None):
    txt = gzip.open(raw, 'rt').read() if raw else get(
        f'https://waterservices.usgs.gov/nwis/dv/?format=rdb&sites=01066000&parameterCd=00060&startDT=1916-01-01&endDT={TODAY:%Y-%m-%d}').decode()
    q = pd.read_csv(io.StringIO(txt), sep='\t', comment='#')
    q = q[q.agency_cd == 'USGS']
    df = pd.DataFrame({'date': q.datetime, 'q_cfs': pd.to_numeric(q.iloc[:, 3], errors='coerce')}).dropna()
    save(df, 'saco_daily.csv')


# ---------------------------------------------------------------- GHCN Portland Jetport
def ghcn(raw=None):
    txt = gzip.open(raw, 'rt').read() if raw else get(
        'https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=USW00014764'
        f'&dataTypes=TMAX,TMIN,PRCP&startDate=1991-01-01&endDate={TODAY:%Y-%m-%d}&units=metric&format=csv').decode()
    g = pd.read_csv(io.StringIO(txt))
    save(g[['DATE', 'TMAX', 'TMIN', 'PRCP']].rename(columns=str.lower), 'portland_air.csv')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', help='folder of previously downloaded raw files (testing only)')
    a = ap.parse_args()
    R = a.raw
    j = (lambda f: os.path.join(R, f)) if R else (lambda f: None)
    print('🌐 Updating outside reference records')
    step('NOAA monthly sea level', lambda: monthly(j('portland_monthly.csv.gz')))
    step('NOAA hourly water level', lambda: hourly(j('portland_hourly.csv.gz'), j('portland_pred.csv.gz')))
    step('NDBC buoy 44007', lambda: ndbc(R))
    step('USGS Saco River', lambda: usgs(j('saco_daily.rdb.gz')))
    step('NOAA Portland air', lambda: ghcn(j('portland_ghcn.csv.gz')))
    if len(problems) == 5:
        sys.exit(1)


if __name__ == '__main__':
    main()
