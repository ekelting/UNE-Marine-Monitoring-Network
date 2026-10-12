"""
fetch.py — checks the public CUMULUS page for new radar scans and turns each one into numbers.

Runs every hour on GitHub Actions. For every scan ("collect") it hasn't seen yet it:
  1. asks CUMULUS for that scan's viewer JSON (fresh image links + map position),
  2. downloads the zones map, the motion (variability) map, the vessel tracks and some sweep frames,
  3. measures them (see core.scan_stats) and appends a row to data/collects.csv,
  4. appends every tracked boat to data/tracks/tracks_YYYY-MM.csv.

Images are NOT stored in the repository (they'd fill it up fast); build.py downloads the latest
ones fresh each hour for the website. The first runs back-fill the history, a chunk per run.

Usage:  python radar/fetch.py [--max-minutes 35]
"""
import argparse
import json
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402

COLLECTS = os.path.join(core.DATA, 'collects.csv')
TRACKS = os.path.join(core.DATA, 'tracks')
STATE = os.path.join(core.DATA, 'state.json')


def load_state():
    try:
        with open(STATE) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def known_ids():
    if not os.path.exists(COLLECTS):
        return set()
    return set(pd.read_csv(COLLECTS, usecols=['collect_id'])['collect_id'])


def append_csv(path, rows):
    if not rows:
        return
    df = pd.DataFrame(rows)
    if os.path.exists(path):
        old = pd.read_csv(path)
        df = pd.concat([old, df], ignore_index=True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


def even_pick(n, k):
    if n <= k:
        return list(range(n))
    return sorted({round(i * (n - 1) / (k - 1)) for i in range(k)})


def process(http, cid, full):
    v = core.viewer(http, cid)
    if not v.get('available'):
        return {'collect_id': cid, 'status': 'no imagery'}, []
    zl, vl, tl = core.layer(v, 'zones'), core.layer(v, 'variability'), core.layer(v, 'tracks')
    zones = http.content(zl['url']) if zl else None
    var = http.content(vl['url']) if vl else None
    geo = http.json(tl['url']) if tl else None
    urls = v.get('frames') or []
    pick = list(range(len(urls))) if full else even_pick(len(urls), core.CFG.get('light_frames', 24))
    frames = [(i, http.content(urls[i])) for i in pick]
    vmax = float(((vl or {}).get('stats') or {}).get('scale_max') or 6)
    st = core.scan_stats(v, zones, var, frames, geo, var_scale_max=vmax, full=full)
    st['status'] = 'ok'
    return st, core.track_rows(v, geo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--max-minutes', type=float, default=35)
    a = ap.parse_args()
    t0 = time.time()
    http = core.Http()
    state = load_state()
    have = known_ids()

    # 1) what scans exist? newest pages first; walk the full archive until the back-fill is done
    listed = {}
    page, last = 1, 1
    while page <= last:
        rows, last = core.list_page(http, page, all_=True)
        new_here = [r for r in rows if r[0] not in have]
        for cid, t in rows:
            listed[cid] = t
        if state.get('backfill_done') and not new_here:
            break          # everything older is already in the CSV
        page += 1
        if page > 60:
            break
    fails = state.get('failed', {})
    todo = sorted([(t, cid) for cid, t in listed.items() if cid not in have and fails.get(cid, 0) < 3], reverse=True)
    print(f'📡 {len(listed)} scans listed on CUMULUS, {len(have)} already measured, {len(todo)} to do')

    # 2) measure them, newest first
    stats, tracks, errors = [], [], []
    cap = core.CFG.get('max_new_per_run', 60)
    nfull = core.CFG.get('full_burst_newest', 3)
    for i, (t, cid) in enumerate(todo[:cap]):
        if time.time() - t0 > a.max_minutes * 60:
            print('⏱️ out of time for this run — the rest will be picked up next hour')
            break
        full = i < nfull and (pd.Timestamp.now(tz='UTC') - pd.Timestamp(t)) < pd.Timedelta(days=2)
        try:
            st, tr = process(http, cid, full)
            st.setdefault('time_utc', t)
            stats.append(st)
            tracks.extend(tr)
            print(f"   ✓ {t}  sparkle {st.get('sparkle_ring_pct', '—')}%  boats {st.get('n_tracks', '—')}"
                  + (f"  rhythm {st.get('radar_period_s')} s (q {st.get('radar_period_q')})" if 'radar_period_s' in st else ''))
        except Exception as e:  # noqa: BLE001 — one bad scan must not stop the rest
            errors.append(f'{t}: {e}')
            fails[cid] = fails.get(cid, 0) + 1
            print(f'   ✗ {t}: {e}')

    append_csv(COLLECTS, stats)
    if os.path.exists(COLLECTS):
        df = pd.read_csv(COLLECTS).drop_duplicates('collect_id', keep='last').sort_values('time_utc')
        df.to_csv(COLLECTS, index=False)
    if tracks:
        tdf = pd.DataFrame(tracks)
        tdf['month'] = pd.to_datetime(tdf['time_utc'], utc=True).dt.strftime('%Y-%m')
        for m, g in tdf.groupby('month'):
            append_csv(os.path.join(TRACKS, f'tracks_{m}.csv'), g.drop(columns='month').to_dict('records'))

    remaining = len(todo) - len(stats) - len(errors)
    state.update(last_run_utc=pd.Timestamp.now(tz='UTC').isoformat(timespec='seconds'),
                 backfill_done=remaining <= 0 and not errors, failed=fails,
                 last_errors=errors[:5], scans_listed=len(listed))
    os.makedirs(core.DATA, exist_ok=True)
    with open(STATE, 'w') as fh:
        json.dump(state, fh, indent=1)
    print(f'✅ measured {len(stats)} scans ({len(errors)} errors, {max(remaining, 0)} left) in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
