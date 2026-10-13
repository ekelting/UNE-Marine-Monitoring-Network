"""
build.py — turns data/ (+ the latest images from CUMULUS) into the website in site/:

  site/index.html                 the dashboard
  site/img/latest/*               newest scan: snapshot, motion map, zones, boat tracks, 5-minute animation
  site/img/recent/*               small snapshots of the last ~24 scans (the filmstrip)
  site/data/collects.csv          one row per radar scan (the numbers behind every chart)
  site/data/tracks.csv            one row per boat / moving target the radar tracked
  site/data/latest.json           tiny file the open page checks to know when to refresh itself

Usage:  python radar/build.py [--out site] [--offline]
"""
import argparse
import glob
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402

CFG = core.CFG
TZ = CFG.get('timezone', 'America/New_York')


# ------------------------------------------------------------ inputs --
def load_collects():
    p = os.path.join(core.DATA, 'collects.csv')
    if not os.path.exists(p):
        return pd.DataFrame(columns=['collect_id', 'time_utc', 'status'])
    df = pd.read_csv(p)
    df['t'] = pd.to_datetime(df['time_utc'], utc=True, format='ISO8601')
    return df.sort_values('t').reset_index(drop=True)


def load_tracks():
    fs = sorted(glob.glob(os.path.join(core.DATA, 'tracks', 'tracks_*.csv')))
    if not fs:
        return pd.DataFrame(columns=['time_utc', 'speed_kn', 'path'])
    df = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
    df['t'] = pd.to_datetime(df['time_utc'], utc=True, format='ISO8601')
    return df.sort_values('t')


def load_buoy(offline):
    b = CFG.get('buoy') or {}
    if offline or not b.get('hourly_csv'):
        return pd.DataFrame()
    try:
        df = pd.read_csv(b['hourly_csv'])
        df['t'] = pd.to_datetime(df['time_local']).dt.tz_localize(TZ, ambiguous='NaT', nonexistent='NaT').dt.tz_convert('UTC')
        print(f"🌊 {len(df)} hourly rows from the {b.get('label')}")
        return df.dropna(subset=['t']).sort_values('t')
    except Exception as e:  # noqa: BLE001
        print(f'::warning::Could not read buoy data ({e}); the buoy comparison is skipped this hour.')
        return pd.DataFrame()


def load_tides(offline):
    st = CFG.get('tide_station')
    if offline or not st:
        return [], []
    import urllib.request
    base = ('https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=predictions&application=UNE_radar'
            f'&datum=MLLW&station={st}&time_zone=gmt&units=english&format=json')
    now = pd.Timestamp.now(tz='UTC')
    out = []
    for interval, d0, rng in (('h', now - pd.Timedelta(days=15), 17 * 24), ('hilo', now - pd.Timedelta(days=1), 72)):
        url = f"{base}&interval={interval}&begin_date={d0:%Y%m%d}&range={rng}"
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                pr = json.load(r).get('predictions') or []
            out.append([{'t': x['t'].replace(' ', 'T') + 'Z', 'v': round(float(x['v']), 2), **({'type': x['type']} if 'type' in x else {})}
                        for x in pr])
        except Exception as e:  # noqa: BLE001
            print(f'::warning::NOAA tides unavailable ({e})')
            out.append([])
    return out[0], out[1]


# ---------------------------------------------------------- imagery --
def webp(img, path, **kw):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, 'WEBP', **kw)


def fetch_imagery(http, df, out):
    """Download the newest scan's pictures and the recent filmstrip. Returns metadata for the page."""
    ok = df[df.get('status', pd.Series(dtype=str)) == 'ok'] if 'status' in df else df
    if ok.empty:
        return {}
    meta = {}
    newest = ok.iloc[-1]
    v = core.viewer(http, newest['collect_id'])
    if not v.get('available'):
        return {}
    g = v['georef']
    meta['latest'] = {'collect_id': v['selected_id'], 'time_utc': v['selected_at'], 'bounds': core.bounds(g),
                      'range_m': g.get('range_m'), 'layers': {}}
    d = os.path.join(out, 'img', 'latest')
    comp = core.open_png(http.content(v['composite'])).convert('RGBA')
    webp(comp, os.path.join(d, 'composite.webp'), quality=88)
    meta['latest']['layers']['composite'] = 'img/latest/composite.webp'
    for key in ('variability', 'zones'):
        lyr = core.layer(v, key)
        if lyr:
            im = core.open_png(http.content(lyr['url'])).convert('RGBA')
            webp(im, os.path.join(d, f'{key}.webp'), lossless=(key == 'zones'), quality=85)
            meta['latest']['layers'][key] = f'img/latest/{key}.webp'
    tl = core.layer(v, 'tracks')
    if tl:
        geo = http.json(tl['url'])
        with open(os.path.join(d, 'tracks.geojson'), 'w') as fh:
            json.dump(geo, fh)
        meta['latest']['layers']['tracks'] = 'img/latest/tracks.geojson'
    # the 5-minute burst as one looping animation (~20× real speed); shrink until it's phone-friendly (< 4 MB)
    urls = v.get('frames') or []
    if urls:
        raw = {}
        for step, size, q in ((2, 640, 55), (2, 512, 45), (3, 512, 40)):
            frames = []
            for i in range(0, len(urls), step):
                try:
                    if i not in raw:
                        raw[i] = core.open_png(http.content(urls[i])).convert('RGBA')
                    frames.append(raw[i].resize((size, size), Image.LANCZOS))
                except Exception:  # noqa: BLE001
                    continue
            if len(frames) <= 5:
                break
            p = os.path.join(d, 'anim.webp')
            webp(frames[0], p, save_all=True, append_images=frames[1:], duration=int(55 * step), loop=0, quality=q, method=4)
            if os.path.getsize(p) < 4e6:
                break
        if os.path.exists(os.path.join(d, 'anim.webp')):
            rel = (v.get('times') or {}).get('rel') or []
            secs = (rel[-1] - rel[0]) if len(rel) > 1 else len(urls) * 1.3
            meta['latest']['layers']['anim'] = 'img/latest/anim.webp'
            meta['latest']['anim_real_seconds'] = round(secs)
            meta['latest']['anim_play_seconds'] = round(len(frames) * 55 * step / 1000)
            print(f'🎞️ animation: {len(frames)} frames, {size}px, {os.path.getsize(os.path.join(d, "anim.webp")) / 1e6:.1f} MB')
    # filmstrip of recent scans
    strip = []
    rd = os.path.join(out, 'img', 'recent')
    for i, row in enumerate(ok.iloc[::-1].head(CFG.get('recent_strip', 24)).itertuples()):
        try:
            vv = v if row.collect_id == v['selected_id'] else core.viewer(http, row.collect_id)
            im = core.open_png(http.content(vv['composite'])).convert('RGBA')
            th = Image.new('RGBA', im.size, (14, 22, 38, 255))
            th.alpha_composite(im)
            th = th.convert('RGB').resize((360, 360), Image.LANCZOS)
            webp(th, os.path.join(rd, f'{i:02d}.webp'), quality=70)
            strip.append({'src': f'img/recent/{i:02d}.webp', 'full': None, 'time_utc': row.time_utc,
                          'bounds': core.bounds(vv['georef'])})
            if i < 12:  # full-size copies of the newest dozen so they can be shown on the map
                webp(im, os.path.join(rd, f'{i:02d}_full.webp'), quality=80)
                strip[-1]['full'] = f'img/recent/{i:02d}_full.webp'
        except Exception as e:  # noqa: BLE001
            print(f'   (skipped one filmstrip image: {e})')
    meta['strip'] = strip
    return meta


# ---------------------------------------------------------- analysis --
def attach_buoy(df, buoy):
    if buoy.empty or df.empty:
        return df
    cols = [c for c in ['hs', 'tp', 'dm', 'wspd'] if c in buoy]
    m = pd.merge_asof(df.sort_values('t'), buoy[['t'] + cols].rename(columns={c: 'buoy_' + c for c in cols}),
                      on='t', direction='nearest', tolerance=pd.Timedelta(minutes=75))
    return m


def area_txt(m2):
    """'12,300 ft² (1,140 m²)' — big areas in millions."""
    f = lambda v, u: (f'{v / 1e6:.1f} million {u}' if v >= 1e6 else f'{v:,.0f} {u}')  # noqa: E731
    return f'{f(m2 * 10.7639, "ft²")} ({f(m2, "m²")})'


def pct_rank(series, x):
    s = series.dropna()
    if len(s) < 10 or x is None or pd.isna(x):
        return None
    return round(float((s < x).mean() * 100))


def corr(df, a, b):
    d = df[[a, b]].dropna() if a in df and b in df else pd.DataFrame()
    if len(d) < 20 or d[a].std() == 0 or d[b].std() == 0:
        return None, len(d)
    return round(float(d[a].corr(d[b])), 2), len(d)


def describe_r(r):
    if r is None:
        return None
    a = abs(r)
    word = 'strongly' if a >= 0.7 else 'moderately' if a >= 0.45 else 'weakly' if a >= 0.25 else 'hardly at all'
    return word


def insights(df, tracks, buoy_ok):
    ok = df[df['status'] == 'ok'] if 'status' in df else df
    cards = []
    if ok.empty:
        return cards
    first = ok['t'].min().tz_convert(TZ)
    cards.append(('📸', f'{len(ok):,} radar scans and counting',
                  f'The radar has been photographing the sea every hour since {first:%B %-d, %Y}. '
                  f'Each scan is 5 minutes of sweeps, one every 1.3 seconds — roughly {len(ok) * 229:,} sweeps in total.'))
    if 'n_tracks' in ok and ok['n_tracks'].notna().any():
        last24 = ok[ok['t'] > ok['t'].max() - pd.Timedelta(hours=24)]
        busiest = ok.assign(h=ok['t'].dt.tz_convert(TZ).dt.hour).groupby('h')['n_tracks'].mean()
        if len(busiest) >= 6:
            hb = int(busiest.idxmax())
            hq = int(busiest.idxmin())
            fmt = lambda h: datetime(2000, 1, 1, h).strftime('%-I %p')
            cards.append(('🚤', f'Busiest on the water around {fmt(hb)}',
                          f'On average the radar tracks {busiest.max():.1f} moving targets per scan at {fmt(hb)}, '
                          f'versus {busiest.min():.1f} around {fmt(hq)}. In the last 24 hours it picked up '
                          f'{int(last24["n_tracks"].sum())} tracks.'))
        if not tracks.empty and tracks['speed_kn'].notna().any():
            wk = tracks[tracks['t'] > tracks['t'].max() - pd.Timedelta(days=7)]
            if not wk.empty:
                f = wk.loc[wk['speed_kn'].idxmax()]
                cards.append(('🏎️', f'Speed demon: {f["speed_kn"]:.0f} knots',
                              f'The fastest thing the radar tracked this week was moving at about {f["speed_kn"]:.0f} knots '
                              f'({f["speed_kn"] * 1.15078:.0f} mph) on {f["t"].tz_convert(TZ):%a %b %-d at %-I:%M %p}. '
                              'Probably a fast boat — though the tracker is automatic, so the odd seabird flock or wave crest sneaks in.'))
    if buoy_ok:
        r, n = corr(ok, 'sparkle_ring_pct', 'buoy_wspd')
        r2, n2 = corr(ok, 'sparkle_ring_pct', 'buoy_hs')
        if r is not None or r2 is not None:
            parts = []
            if r is not None:
                parts.append(f'wind (r = {r:+.2f}, {describe_r(r)} linked)')
            if r2 is not None:
                parts.append(f'wave height (r = {r2:+.2f}, {describe_r(r2)} linked)')
            cards.append(('🤝', 'Does the radar agree with the buoy?',
                          'We compared the radar\'s surface roughness (how much of the water bounces the radar back) with the Camp Ellis buoy, 700 m away, using '
                          f'{max(n, n2):,} matching hours. Roughness vs ' + ' and '.join(parts) + '. '
                          'Radar sees wind ripples best, so wind usually wins.'))
    if 'whitewater_m2' in ok and ok['whitewater_m2'].notna().any():
        top = ok.loc[ok['whitewater_m2'].idxmax()]
        cards.append(('💥', 'Biggest whitewater day so far',
                      f'{top["t"].tz_convert(TZ):%B %-d at %-I %p}: about {area_txt(top["whitewater_m2"])} of churning, breaking water along the shore.'))
    if 'radar_period_q' in ok:
        good = ok[ok['radar_period_q'] >= 2.2]
        if len(good):
            cards.append(('🎵', f'The radar heard the waves {len(good)} times',
                          'Experimental: when the sea is rough enough the echo flickers in time with passing waves, so the radar can '
                          f'"hear" the wave rhythm. Latest confident reading: {good.iloc[-1]["radar_period_s"]:.1f} seconds between crests.'))
        else:
            cards.append(('🎵', 'Listening for the wave rhythm…',
                          'Experimental: in rough seas the radar echo flickers in time with passing waves, which lets us measure '
                          'the wave rhythm from radar alone. So far the sea has been too calm for a confident reading — check back after a blow.'))
    return cards


def series(df, cols, days=None):
    d = df if days is None else df[df['t'] > df['t'].max() - pd.Timedelta(days=days)]
    out = {'t': [x.isoformat().replace('+00:00', 'Z') for x in d['t']]}
    for c in cols:
        if c in d:
            out[c] = [None if pd.isna(x) else (round(float(x), 3) if isinstance(x, (float, np.floating)) else x) for x in d[c]]
    return out


# ------------------------------------------------------------- main --
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(core.ROOT, 'site'))
    ap.add_argument('--offline', action='store_true', help='skip all downloads (layout testing)')
    ap.add_argument('--data', default=None, help='(ignored — data is read from the radar folder)')
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(os.path.join(a.out, 'data'), exist_ok=True)

    df = load_collects()
    tracks = load_tracks()
    buoy = load_buoy(a.offline)
    df = attach_buoy(df, buoy)
    ok = df[df['status'] == 'ok'] if 'status' in df else df
    tide_h, tide_hilo = load_tides(a.offline)

    meta = {}
    if not a.offline:
        try:
            meta = fetch_imagery(core.Http(), df, a.out)
            print(f"🖼️ imagery for {meta.get('latest', {}).get('time_utc')} + {len(meta.get('strip', []))} filmstrip scans")
        except Exception as e:  # noqa: BLE001 — the page still works with numbers only
            print(f'::warning::Could not download radar imagery ({e})')

    # tidy exports
    keep = [c for c in df.columns if c != 't']
    df[keep].to_csv(os.path.join(a.out, 'data', 'collects.csv'), index=False)
    if not tracks.empty:
        tracks.drop(columns='t').to_csv(os.path.join(a.out, 'data', 'tracks.csv'), index=False)

    latest = ok.iloc[-1].to_dict() if len(ok) else {}
    latest = {k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in latest.items()}
    latest.pop('t', None)
    D = {
        'cfg': {k: CFG.get(k) for k in ('short_name', 'site_name', 'radar_model', 'cumulus_url', 'radar_lat', 'radar_lon',
                                         'buoy', 'sister_sites', 'tide_station_name', 'github_user', 'github_repo', 'site_url')},
        'generated_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'latest': latest,
        'img': meta,
        'pct': {'sparkle': pct_rank(ok.get('sparkle_ring_pct', pd.Series(dtype=float)), latest.get('sparkle_ring_pct')),
                'whitewater': pct_rank(ok.get('whitewater_m2', pd.Series(dtype=float)), latest.get('whitewater_m2'))},
        'ts': series(ok, ['sparkle_ring_pct', 'motion_mean', 'whitewater_m2', 'n_tracks', 'max_speed_kn', 'buoy_hs', 'buoy_tp',
                          'buoy_wspd', 'buoy_dm', 'radar_period_s', 'radar_period_q'], days=60),
        'daily': [],
        'hour': [],
        'tracks7': [],
        'tide': tide_h, 'tide_hilo': tide_hilo,
        'cards': insights(df, tracks, not buoy.empty),
        'corr': {},
        'n_scans': int(len(ok)),
        'first_utc': ok['t'].min().isoformat() if len(ok) else None,
        'state': {},
    }
    if len(ok):
        loc = ok.assign(day=ok['t'].dt.tz_convert(TZ).dt.strftime('%Y-%m-%d'), h=ok['t'].dt.tz_convert(TZ).dt.hour)
        agg = {'scans': ('collect_id', 'count')}
        for c in ('sparkle_ring_pct', 'whitewater_m2', 'buoy_hs'):
            if c in loc:
                agg[c] = (c, 'mean')
        if 'n_tracks' in loc:
            agg['n_tracks'] = ('n_tracks', 'sum')
        dd = loc.groupby('day').agg(**agg).reset_index()
        D['daily'] = json.loads(dd.round(3).to_json(orient='records'))
        if 'n_tracks' in loc:
            hh = loc.groupby('h')['n_tracks'].agg(['mean', 'count']).reset_index()
            D['hour'] = json.loads(hh.round(2).to_json(orient='records'))
        for a_, b_ in (('sparkle_ring_pct', 'buoy_wspd'), ('sparkle_ring_pct', 'buoy_hs')):
            r, n = corr(ok, a_, b_)
            D['corr'][b_] = {'r': r, 'n': n, 'word': describe_r(r)}
        D['scatter'] = series(ok, ['sparkle_ring_pct', 'buoy_wspd', 'buoy_hs'])
    if not tracks.empty:
        wk = tracks[tracks['t'] > tracks['t'].max() - pd.Timedelta(days=7)]
        D['tracks7'] = [{'s': None if pd.isna(r.speed_kn) else round(float(r.speed_kn), 1),
                         'p': [[float(y), float(x)] for x, y in (pt.split(',') for pt in str(r.path).split(';') if ',' in pt)]}
                        for r in wk.itertuples()][:4000]
    try:
        with open(os.path.join(core.DATA, 'state.json')) as fh:
            D['state'] = json.load(fh)
    except (OSError, ValueError):
        pass

    with open(os.path.join(core.HERE, 'template.html'), encoding='utf-8') as fh:
        page = fh.read()
    blob = json.dumps(D, separators=(',', ':'), default=str).replace('</', '<\\/')
    sys.path.insert(0, os.path.join(core.HERE, '..', 'shared'))
    import mapjs
    import explain
    here = {}
    if len(ok):
        n_days = max(1, (ok['t'].max() - ok['t'].min()).days)
        here['radar_scan'] = f'{len(ok):,} scans measured so far, over {n_days} day{"s" if n_days != 1 else ""}.'
        if 'sparkle_ring_pct' in ok and ok['sparkle_ring_pct'].notna().any():
            q = ok['sparkle_ring_pct'].quantile([0.15, 0.5, 0.9])
            here['radar_rough'] = (f'a typical scan echoes from {q.iloc[1]:.1f}% of the nearby open water; the calmest 15% of scans are under '
                                   f'{q.iloc[0]:.1f}% and the roughest 10% are over {q.iloc[2]:.1f}%.')
        if 'whitewater_m2' in ok and ok['whitewater_m2'].notna().any():
            here['radar_white'] = f'typically {area_txt(ok["whitewater_m2"].median())}; the most so far was {area_txt(ok["whitewater_m2"].max())}.'
        if 'n_tracks' in ok and ok['n_tracks'].notna().any():
            here['radar_boats'] = f'about {ok["n_tracks"].mean():.0f} moving targets per scan on average; fastest so far {ok["max_speed_kn"].max():.0f} knots.' \
                if 'max_speed_kn' in ok else f'about {ok["n_tracks"].mean():.0f} moving targets per scan on average.'
        c = D.get('corr', {}).get('buoy_wspd') or {}
        if c.get('r') is not None:
            here['radar_vs_buoy'] = f'roughness vs. wind at the buoy: r = {c["r"]:.2f} ({c.get("word", "")} linked), from {c.get("n", 0):,} matching hours.'
    keys = ['radar_scan', 'radar_rough', 'radar_motion', 'radar_zones', 'radar_white', 'radar_boats', 'radar_rhythm', 'radar_vs_buoy']
    page = page.replace('%%EXCSS%%', explain.CSS).replace('%%EXPLAIN%%', explain.SECTION.format(cards=explain.cards(keys, here)))
    page = page.replace('%%NAV%%', mapjs.nav_buttons(CFG.get('sister_sites', [])))
    page = page.replace('%%DATA%%', blob).replace('%%SHORT%%', CFG.get('title_name') or CFG.get('short_name', 'Radar'))
    with open(os.path.join(a.out, 'index.html'), 'w', encoding='utf-8') as fh:
        fh.write(page)
    # summary for the network home page (same shape as the buoy/station latest.json files)
    rec = ok[ok['t'] > ok['t'].max() - pd.Timedelta(days=14)] if len(ok) else ok
    num = lambda v: None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), 3)  # noqa: E731
    lj = {'id': CFG.get('github_repo'), 'kind': 'radar', 'name': CFG.get('short_name'), 'device': CFG.get('radar_model'),
          'lat': CFG.get('radar_lat'), 'lon': CFG.get('radar_lon'), 'url': CFG.get('site_url'),
          'last_obs': latest.get('time_utc'), 'generated': D['generated_utc'],
          'now': {k: num(latest.get(k)) for k in ('sparkle_ring_pct', 'n_tracks', 'whitewater_m2', 'max_speed_kn', 'radar_period_s', 'motion_mean')},
          'pct': D['pct'],
          'recent': {'t': [t.strftime('%Y-%m-%dT%H:%MZ') for t in rec['t']] if len(rec) else [],
                     'sparkle_ring_pct': [num(v) for v in rec['sparkle_ring_pct']] if 'sparkle_ring_pct' in rec else [],
                     'n_tracks': [num(v) for v in rec['n_tracks']] if 'n_tracks' in rec else []},
          'img': ((meta.get('latest') or {}).get('layers') or {}).get('composite'),
          'insights': [[c[0], c[1]] for c in (D['cards'] or [])][:4]}
    with open(os.path.join(a.out, 'data', 'latest.json'), 'w') as fh:
        json.dump(lj, fh, default=str, separators=(',', ':'))
    open(os.path.join(a.out, '.nojekyll'), 'w').close()
    print(f'✅ site built in {time.time() - t0:.0f}s — {len(ok)} scans, latest {latest.get("time_utc")}')


if __name__ == '__main__':
    main()
