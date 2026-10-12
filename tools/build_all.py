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
    shutil.copy(os.path.join(ROOT, 'web', 'index.html'), os.path.join(a.out, 'index.html'))
    shutil.copy(os.path.join(ROOT, 'buoys.json'), os.path.join(a.out, 'buoys.json'))
    open(os.path.join(a.out, '.nojekyll'), 'w').close()
    print(f'\n✅ built {len(buoys) - len(failed)} of {len(buoys)} buoy pages' + (f' — failed: {", ".join(failed)}' if failed else ''))
    if len(failed) == len(buoys):
        sys.exit(1)


if __name__ == '__main__':
    main()
