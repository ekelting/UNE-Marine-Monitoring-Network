"""
build_all.py — builds the whole website into site/:
  site/index.html              the network overview (web/index.html, reads each buoy's data/latest.json live)
  site/<slug>/index.html       each buoy's full dashboard, plus its spreadsheet and CSV downloads
One buoy failing to build never stops the others.     Usage:  python tools/build_all.py [--out site] [--only slug]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = {'wave': 'wave', 'wq': 'sonde', 'station': 'station', 'radar': 'radar'}


def fetch_ndbc(path, station='44007'):
    """Latest wave and wind reading from NOAA buoy 44007 (off Portland) for the trip check. Skipped quietly if NDBC is unreachable."""
    import json, urllib.request
    from datetime import datetime, timezone
    try:
        txt = urllib.request.urlopen(urllib.request.Request(f'https://www.ndbc.noaa.gov/data/realtime2/{station}.txt',
                                     headers={'User-Agent': 'UNE-Marine-Monitoring-Network/1.0'}), timeout=30).read().decode()
        head = txt.splitlines()[0].lstrip('#').split()
        num = lambda v: None if v in ('MM', '') else float(v)
        out = {}
        for line in txt.splitlines()[2:50]:                  # newest first; take the newest value of each field
            r = dict(zip(head, line.split()))
            t = datetime(int(r['YY']), int(r['MM']), int(r['DD']), int(r['hh']), int(r['mm']), tzinfo=timezone.utc)
            for k, key in (('WVHT', 'wvht_m'), ('DPD', 'dpd_s'), ('MWD', 'mwd_deg'), ('WSPD', 'wspd_ms'), ('GST', 'gst_ms'), ('WDIR', 'wdir_deg'), ('WTMP', 'wtmp_c')):
                if key not in out and num(r.get(k, 'MM')) is not None:
                    out[key] = num(r[k])
                    if key == 'wvht_m':
                        out['time'] = t.isoformat()
        out.setdefault('time', None); out['station'] = station
        json.dump(out, open(path, 'w'))
        print(f'NOAA buoy {station}: {out}')
    except Exception as e:
        print(f'::warning::NOAA buoy {station} unavailable ({e}); the trip check falls back to the local buoy')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, 'site'))
    ap.add_argument('--only', default=None)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    buoys = json.load(open(os.path.join(ROOT, 'buoys.json')))
    failed = []
    for b in buoys:
        if a.only and b['slug'] != a.only:
            continue
        bdir = os.path.join(ROOT, 'buoys', b['slug'])
        if not os.path.exists(os.path.join(bdir, 'data')):
            print(f'::warning::{b["name"]}: no data folder yet — skipped')
            failed.append(b['name'])
            continue
        print(f'\n===== {b["name"]} ({b["slug"]}) =====', flush=True)
        r = subprocess.run([sys.executable, os.path.join(ROOT, CODE[b['kind']], 'build.py'),
                            '--data', os.path.join(bdir, 'data'), '--out', os.path.join(a.out, b['slug'])],
                           env=dict(os.environ, BUOY_DIR=bdir))
        if r.returncode:
            print(f'::error::{b["name"]} failed to build (exit {r.returncode}); its previous page is not updated this hour')
            failed.append(b['name'])
    for b in buoys:                       # old addresses of renamed buoys forward to the current page
        for old in b.get('aliases') or []:
            os.makedirs(os.path.join(a.out, old), exist_ok=True)
            page = (f'<!doctype html><meta charset="utf-8"><title>Moved to {b["name"]}</title>'
                    f'<meta http-equiv="refresh" content="0; url=../{b["slug"]}/"><link rel="canonical" href="../{b["slug"]}/">'
                    f'<p>This buoy is now called <b>{b["name"]}</b>: <a href="../{b["slug"]}/">go to its page</a>.</p>')
            open(os.path.join(a.out, old, 'index.html'), 'w').write(page)
    if not a.only and os.path.exists(os.path.join(ROOT, 'analysis', 'build.py')):   # the network-wide Analysis page
        print('\n===== Analysis page =====', flush=True)
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'analysis', 'build.py'), '--site', a.out])
        if r.returncode:
            print('::warning::the Analysis page failed to build; its previous version is not updated this hour')
    shutil.copy(os.path.join(ROOT, 'web', 'index.html'), os.path.join(a.out, 'index.html'))
    for f in ('tripcheck.js', 'river.json', 'bands.json'):                     # the "On the water today" panel and the trip-check page
        shutil.copy(os.path.join(ROOT, 'web', f), os.path.join(a.out, f))
    os.makedirs(os.path.join(a.out, 'trip-check'), exist_ok=True)
    shutil.copy(os.path.join(ROOT, 'web', 'trip-check', 'index.html'), os.path.join(a.out, 'trip-check', 'index.html'))
    fetch_ndbc(os.path.join(a.out, 'ndbc-44007.json'))
    shutil.copy(os.path.join(ROOT, 'buoys.json'), os.path.join(a.out, 'buoys.json'))
    open(os.path.join(a.out, '.nojekyll'), 'w').close()
    print(f'\n✅ built {len(buoys) - len(failed)} of {len(buoys)} buoy pages' + (f' — failed: {", ".join(failed)}' if failed else ''))
    if len(failed) == len(buoys):
        sys.exit(1)


if __name__ == '__main__':
    main()
