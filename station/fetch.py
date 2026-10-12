"""
fetch.py — pulls new readings for one UNE weather / environmental station from the public ArcGIS
feature service behind the UNE monitoring dashboards ("UNE MEMO data", one row every 5 minutes,
one column per station measurement), and adds them to the station's CSV files:

  <station>/data/obs/obs_YYYY-MM.csv   one row per 5-minute reading (UTC), one column per measurement
  <station>/data/state.json            last run, newest reading, any problems

The first run backfills everything since the station's start_utc (paged, 1000 rows per request).
No account or API key is needed.      Usage:  BUOY_DIR=buoys/<slug> python station/fetch.py
"""
import glob
import json
import os
import sys
import time
import urllib.parse
import urllib.request

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.environ.get('BUOY_DIR') or os.path.dirname(HERE))
CFG = json.load(open(os.path.join(ROOT, 'site.json'), encoding='utf-8'))
URL = CFG['arcgis_url'].rstrip('/') + '/query'
FIELDS = [v['field'] for v in CFG['vars']]
UA = f"UNE-monitoring-dashboard/1.0 (+https://github.com/{CFG['github_user']}/{CFG['github_repo']})"
PAGE = 1000


def query(where, offset):
    body = urllib.parse.urlencode(dict(f='json', where=where, outFields='timestamp,' + ','.join(FIELDS),
                                       orderByFields='timestamp ASC', resultOffset=offset, resultRecordCount=PAGE,
                                       returnGeometry='false')).encode()
    req = urllib.request.Request(URL, data=body, headers={'User-Agent': UA, 'Content-Type': 'application/x-www-form-urlencoded'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                js = json.load(r)
            if 'error' in js:
                raise RuntimeError(js['error'].get('message', js['error']))
            return js
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                raise
            print(f'  retrying after error: {e}')
            time.sleep(10 * (attempt + 1))


def read_all(folder):
    fs = sorted(glob.glob(os.path.join(folder, 'obs_*.csv')))
    if not fs:
        return pd.DataFrame()
    df = pd.concat([pd.read_csv(f, index_col=0) for f in fs])
    df.index = pd.to_datetime(df.index, utc=True)
    return df[~df.index.duplicated(keep='last')].sort_index()


def write_months(df, folder):
    os.makedirs(folder, exist_ok=True)
    for p, g in df.groupby(df.index.tz_convert(None).to_period('M')):
        out = g.copy()
        out.index = out.index.strftime('%Y-%m-%dT%H:%M:%SZ')
        out.index.name = 'time_utc'
        out.round(5).to_csv(os.path.join(folder, f'obs_{p}.csv'))


def main(max_minutes=40):
    t0 = time.time()
    data = os.path.join(ROOT, 'data')
    obs_dir = os.path.join(data, 'obs')
    old = read_all(obs_dir)
    since = old.index.max() if len(old) else pd.Timestamp(CFG.get('start_utc', '2025-12-01T00:00:00Z'))
    since = since - pd.Timedelta(hours=2)          # small overlap: late-arriving rows replace earlier copies
    where = (f"timestamp > timestamp '{since.tz_convert('UTC'):%Y-%m-%d %H:%M:%S}' AND ("
             + ' OR '.join(f'{f} IS NOT NULL' for f in FIELDS) + ')')
    rows, offset, errors = [], 0, []
    try:
        while True:
            js = query(where, offset)
            feats = js.get('features') or []
            rows += [f['attributes'] for f in feats]
            offset += len(feats)
            if not feats or not js.get('exceededTransferLimit') and len(feats) < PAGE:
                break
            if time.time() - t0 > max_minutes * 60:
                print('::warning::time limit reached — the rest is fetched next hour')
                break
            if offset % 10000 == 0:
                print(f'   … {offset:,} rows')
    except Exception as e:  # noqa: BLE001
        errors.append(f'ArcGIS query: {e}')
    if rows:
        new = pd.DataFrame(rows)
        new.index = pd.to_datetime(new.pop('timestamp'), unit='ms', utc=True)
        new.index.name = 'time_utc'
        new = new.dropna(how='all')
        both = pd.concat([x for x in [old, new] if len(x)])
        both = both[~both.index.duplicated(keep='last')].sort_index()
        touched = new.index.tz_convert(None).to_period('M').unique()
        write_months(both[both.index.tz_convert(None).to_period('M').isin(touched)], obs_dir)
        print(f'🛰️  {len(new):,} readings fetched ({new.index.min():%Y-%m-%d %H:%M} → {new.index.max():%Y-%m-%d %H:%M} UTC); '
              f'{len(both):,} stored')
        last = both.index.max()
    else:
        print('No new readings.')
        last = old.index.max() if len(old) else None
    os.makedirs(data, exist_ok=True)
    st = {'last_run': pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%dT%H:%M:%SZ'), 'last_errors': errors}
    if last is not None:
        st['last_obs'] = last.strftime('%Y-%m-%dT%H:%M:%SZ')
    json.dump(st, open(os.path.join(data, 'state.json'), 'w'), indent=2)
    for e in errors:
        print(f'::warning::{e}')
    if errors and not rows and not len(old):
        sys.exit(1)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--max-minutes', type=float, default=40)
    main(ap.parse_args().max_minutes)
