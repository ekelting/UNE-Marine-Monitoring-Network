"""
fetch.py — pulls the newest readings for the BlueSonde buoy from the public CUMULUS
(Coastal Measures) sensor page and adds them to the CSV files under data/.

  data/sonde/<device>_YYYY-MM.csv   one row per sonde reading (UTC), one column per measurement
  data/tide/tide_YYYY-MM.csv        hourly water level that CUMULUS shows alongside the sonde
  data/state.json                   when we last ran, and any problems

The public feed gives the last 7 days at full resolution (~every 15 min) and the last
30 days as averages (~43-min buckets). Each run saves the full-resolution week; the
30-day averages are only kept to fill time that has no full-resolution readings
(e.g. the first run, or if updates stopped for more than a week).

No account or API key is needed.   Usage:  python buoy/fetch.py
"""
import glob
import json
import os
import re
import sys
import time
import urllib.request

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.environ.get('BUOY_DIR') or os.path.dirname(HERE))
CFG = json.load(open(os.path.join(ROOT, 'site.json'), encoding='utf-8'))
DEV = CFG['device_name']
SERIES_URL = f"https://cumulus.coastalmeasures.com/bluesonde/{CFG['device_uuid']}/series"
UA = f"UNE-BlueSonde-dashboard/1.0 (+https://github.com/{CFG['github_user']}/{CFG['github_repo']})"

# CUMULUS label → our column name. Unknown labels are kept too (slugified), so a new sensor never gets lost.
COLS = {
    'Water Temperature': 'temp_c', 'Salinity': 'sal_psu', 'Dissolved Oxygen': 'do_mgl',
    'Dissolved Oxygen Saturation': 'do_pct', 'Chlorophyll': 'chl_ugl', 'Turbidity': 'turb_ntu',
    'Specific Conductivity': 'spcond_uscm', 'Actual Conductivity': 'cond_uscm', 'Total Dissolved Solids': 'tds_ppt',
    'Buoy Battery Diagnostic Voltage': 'batt_mv', 'Buoy Battery Diagnostic Current': 'batt_ma',
    'Buoy Hull Diagnostic Humidity': 'hull_rh', 'Buoy Hull Diagnostic Temperature': 'hull_c',
    'C-Fluor CHL ADC Voltage': 'chl_adc_v', 'C-Fluor TUR ADC Voltage': 'fluor_adc_v', 'C-Fluor TRY ADC Voltage': 'fluor_adc_v',
    'Buoy Solar Diagnostic Voltage': 'solar_mv', 'Buoy Pyramid Diagnostic Humidity': 'hull_rh', 'Tryptophan': 'trp_ppb',
}


def colname(label):
    lab = re.sub(r'^' + re.escape(DEV) + r'\s+', '', label).strip()
    return COLS.get(lab) or re.sub(r'[^a-z0-9]+', '_', lab.lower()).strip('_')


def get(rng):
    req = urllib.request.Request(f'{SERIES_URL}?range={rng}', headers={'Accept': 'application/json', 'User-Agent': UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                raise
            print(f'  retrying {rng} after error: {e}')
            time.sleep(10 * (attempt + 1))


def to_frames(js, res):
    """Split the CUMULUS payload into (sonde wide table, tide series)."""
    tide_lbl = js.get('tideLabel') or 'Tide (water level)'
    sonde, tide = {}, None
    for label, pts in (js.get('series') or {}).items():
        if not pts:
            continue
        s = pd.Series([p.get('v') for p in pts], index=pd.to_datetime([p['t'] for p in pts], unit='ms', utc=True), dtype='float64')
        s = s[~s.index.duplicated(keep='last')]
        if label == tide_lbl:
            tide = s.rename('water_level_m')
        else:
            sonde[colname(label)] = s
    df = pd.DataFrame(sonde).sort_index()
    df.index.name = 'time_utc'
    df['res'] = res
    if tide is not None:
        tide = tide.to_frame()
        tide.index.name = 'time_utc'
    return df, tide


def read_dir(pattern):
    fs = sorted(glob.glob(pattern))
    if not fs:
        return pd.DataFrame()
    df = pd.concat([pd.read_csv(f, index_col=0, parse_dates=[0]) for f in fs])
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def write_months(df, folder, stem):
    os.makedirs(folder, exist_ok=True)
    df = df.sort_index()
    for p, g in df.groupby(df.index.tz_convert(None).to_period('M')):
        path = os.path.join(folder, f'{stem}_{p}.csv')
        out = g.copy()
        out.index = out.index.strftime('%Y-%m-%dT%H:%M:%SZ')
        out.index.name = 'time_utc'
        out.round(5).to_csv(path)


def merge_sonde(old, full, avg):
    allf = pd.concat([x for x in [old, full] if len(x)])
    allf = allf[~allf.index.duplicated(keep='last')].sort_index()
    hi = allf[allf['res'] == 'full'] if len(allf) else allf
    lo = allf[allf['res'] != 'full'] if len(allf) else allf
    if len(avg):
        lo = pd.concat([x for x in [lo, avg] if len(x)])
        lo = lo[~lo.index.duplicated(keep='last')]
    if len(lo) and len(hi):
        # keep an averaged point only if no full-resolution reading lies within 45 minutes of it
        h = hi.index.sort_values()
        pos = h.searchsorted(lo.index)
        before = h[(pos - 1).clip(0, len(h) - 1)]
        after = h[pos.clip(0, len(h) - 1)]
        gap = pd.Series([min(abs(a - t), abs(b - t)) for t, a, b in zip(lo.index, before, after)], index=lo.index)
        lo = lo[gap > pd.Timedelta(minutes=45)]
    out = pd.concat([x for x in [hi, lo] if len(x)]).sort_index()
    return out[~out.index.duplicated(keep='first')]


def main():
    data = os.path.join(ROOT, 'data')
    state_path = os.path.join(data, 'state.json')
    errors = []
    old = read_dir(os.path.join(data, 'sonde', f'{DEV}_*.csv'))
    old_tide = read_dir(os.path.join(data, 'tide', 'tide_*.csv'))
    full = avg = pd.DataFrame()
    tides = [old_tide] if len(old_tide) else []
    try:
        full, t7 = to_frames(get('7d'), 'full')
        print(f'🛰️  7-day feed: {len(full)} readings, {len(full.columns) - 1} channels, '
              f'{full.index.min():%Y-%m-%d %H:%M} → {full.index.max():%Y-%m-%d %H:%M} UTC')
        if t7 is not None:
            tides.append(t7)
    except Exception as e:  # noqa: BLE001
        errors.append(f'7-day feed: {e}')
    try:
        avg, t30 = to_frames(get('30d'), 'avg')
        print(f'🛰️  30-day feed: {len(avg)} averaged readings')
        if t30 is not None:
            tides.insert(1 if len(old_tide) else 0, t30)   # 7-day tide values win over 30-day ones
    except Exception as e:  # noqa: BLE001
        errors.append(f'30-day feed: {e}')

    if len(full) or len(avg):
        merged = merge_sonde(old, full, avg)
        write_months(merged, os.path.join(data, 'sonde'), DEV)
        print(f'💾 {len(merged) - len(old):+d} sonde readings → {len(merged)} stored '
              f'({(merged["res"] == "full").sum()} full-resolution)')
    if tides:
        t = pd.concat(tides)
        t = t[~t.index.duplicated(keep='last')].sort_index()
        write_months(t, os.path.join(data, 'tide'), 'tide')
    st = {'last_run': pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%dT%H:%M:%SZ'), 'last_errors': errors}
    if len(full):
        st['last_obs'] = full.index.max().strftime('%Y-%m-%dT%H:%M:%SZ')
    elif os.path.exists(state_path):
        try:
            st['last_obs'] = json.load(open(state_path)).get('last_obs')
        except ValueError:
            pass
    os.makedirs(data, exist_ok=True)
    with open(state_path, 'w') as fh:
        json.dump(st, fh, indent=2)
    for e in errors:
        print(f'::warning::{e}')
    if errors and not len(full) and not len(avg) and not len(old):
        sys.exit(1)


if __name__ == '__main__':
    main()
