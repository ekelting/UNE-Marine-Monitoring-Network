"""
core.py — shared helpers for the Ram Island radar site.

  * reading site.json
  * talking to CUMULUS (the public sensor page + its "viewer" JSON)
  * turning the radar's PNG images into numbers
  * the per-scan statistics that end up in data/collects.csv
"""
import io
import json
import math
import os
import re
import time

import numpy as np
import requests
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.environ.get('BUOY_DIR') or os.path.dirname(HERE))   # the radar's folder (site.json + data/)
DATA = os.path.join(ROOT, 'data')

with open(os.path.join(ROOT, 'site.json'), encoding='utf-8') as _fh:
    CFG = json.load(_fh)

PAGE = CFG['cumulus_url'].rstrip('/')
VIEWER = PAGE + '/viewer'
UA = (f"UNE-radar-dashboard/1.0 (+https://github.com/{CFG.get('github_user', '')}/{CFG.get('github_repo', '')}; "
      "hourly public-page poll)")

# The 15 colours SeaSignals uses for radar echo strength in the sweep frames ("magma" ramp),
# weakest → strongest. Transparent = no echo (level 0). Measured from the published PNGs.
FRAME_PALETTE = [(47, 15, 62), (93, 23, 87), (132, 29, 97), (165, 40, 96), (191, 55, 90),
                 (211, 74, 85), (225, 96, 83), (233, 119, 89), (239, 139, 98), (243, 158, 109),
                 (246, 176, 122), (248, 192, 136), (250, 208, 149), (252, 223, 163), (254, 237, 176)]
_PAL = np.array(FRAME_PALETTE, dtype=np.int32)
_PAL_KEYS = (_PAL[:, 0] << 16) | (_PAL[:, 1] << 8) | _PAL[:, 2]

ZONE_LAND, ZONE_ACTIVE, ZONE_SEA, ZONE_SEA_RETURN, ZONE_SHADOW = 1, 2, 3, 4, 5


# ------------------------------------------------------------------ HTTP --
class Http:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers['User-Agent'] = UA
        self.errors = []

    def get(self, url, *, accept=None, params=None, tries=4, timeout=60):
        headers = {'Accept': accept} if accept else {}
        last = None
        for i in range(tries):
            try:
                r = self.s.get(url, params=params, headers=headers, timeout=timeout)
                if r.status_code == 200:
                    return r
                last = f'HTTP {r.status_code}'
                if r.status_code in (401, 403, 404):
                    break
            except requests.RequestException as e:
                last = e.__class__.__name__
            time.sleep(3 * (i + 1))
        raise RuntimeError(f'{last} for {url.split("?")[0]}')

    def json(self, url, **kw):
        return self.get(url, accept='application/json', **kw).json()

    def content(self, url, **kw):
        return self.get(url, **kw).content


# ------------------------------------------------------- CUMULUS parsing --
_ROW = re.compile(r'data-collect="([0-9a-f-]{36})".*?data-utc="([^"]+)"', re.S)


def list_page(http, page=1, all_=False):
    """[(collect_id, utc_iso), ...] from one page of the public collect list (50 per page, newest first)."""
    params = {'page': page}
    if all_:
        params['all'] = 1
    html = http.get(PAGE, params=params).text
    seen, out = set(), []
    for cid, t in _ROW.findall(html):
        if cid not in seen:
            seen.add(cid)
            out.append((cid, t))
    m = re.findall(r'[?&;]page=(\d+)', html)
    last_page = max([int(x) for x in m] + [page])
    return out, last_page


def viewer(http, collect_id):
    """The viewer JSON for one collect: georef, burst timing, freshly signed image URLs, derived layers."""
    return http.json(VIEWER, params={'collect': collect_id})


def layer(v, key):
    for it in ((v.get('layers') or {}).get('items') or []):
        if it.get('key') == key and not it.get('empty'):
            return it
    return None


def bounds(georef):
    """[[south, west], [north, east]] of the 1024² image (north-up)."""
    half = georef['grid'] / 2 * georef['mpp']
    lat, lon = georef['lat'], georef['lon']
    dlat = half / 111320.0
    dlon = half / (111320.0 * math.cos(math.radians(lat)))
    return [[lat - dlat, lon - dlon], [lat + dlat, lon + dlon]]


# --------------------------------------------------------- image decoding --
def open_png(b):
    return Image.open(io.BytesIO(b))


def palette_index(b):
    """Indexed PNG (zones, variability) → array of palette indices."""
    im = open_png(b)
    if im.mode != 'P':
        im = im.convert('P')
    return np.asarray(im, dtype=np.uint8)


def frame_levels(b):
    """RGBA sweep frame → echo level 0..15 per pixel (0 = no echo)."""
    a = np.asarray(open_png(b).convert('RGBA'), dtype=np.int32)
    alpha = a[..., 3] > 0
    key = (a[..., 0] << 16) | (a[..., 1] << 8) | a[..., 2]
    lv = np.zeros(key.shape, dtype=np.uint8)
    if not alpha.any():
        return lv
    order = np.argsort(_PAL_KEYS)
    sk = _PAL_KEYS[order]
    k = key[alpha]
    pos = np.clip(np.searchsorted(sk, k), 0, len(sk) - 1)
    hit = sk[pos] == k
    out = np.where(hit, order[pos] + 1, 0)
    if (~hit).any():                       # colours not exactly on the ramp (resampling etc.): nearest colour
        miss_keys, inv = np.unique(k[~hit], return_inverse=True)
        rgb = np.stack([(miss_keys >> 16) & 255, (miss_keys >> 8) & 255, miss_keys & 255], 1)
        d = ((rgb[:, None, :] - _PAL[None, :, :]) ** 2).sum(-1)
        out[~hit] = d.argmin(1)[inv] + 1
    lv[alpha] = out.astype(np.uint8)
    return lv


# ------------------------------------------------------------- statistics --
def radius_m(grid, mpp):
    y, x = np.mgrid[0:grid, 0:grid]
    c = (grid - 1) / 2
    return np.hypot(x - c, y - c) * mpp


def dilate(mask, r_px):
    """Grow a boolean mask by r_px pixels (square neighbourhood)."""
    from scipy import ndimage
    return ndimage.binary_dilation(mask, iterations=max(1, int(r_px)))


def scan_stats(v, zones_b, var_b, frames, tracks_geo, *, var_scale_max=6.0, full=False):
    """Numbers describing one 5-minute radar burst. `frames` = list of (index, png bytes)."""
    g = v['georef']
    mpp, grid = float(g['mpp']), int(g['grid'])
    px_m2 = mpp * mpp
    st = {'collect_id': v['selected_id'], 'time_utc': v['selected_at'],
          'range_m': g.get('range_m'), 'mpp': round(mpp, 4), 'frames_total': v.get('frame_count')}
    R = radius_m(grid, mpp)
    lo, hi = CFG.get('index_ring_m', [300, 1500])
    ring = (R >= lo) & (R <= hi)

    Z = palette_index(zones_b) if zones_b else None
    if Z is not None and Z.shape == (grid, grid):
        disk = Z > 0
        sea = (Z == ZONE_SEA) | (Z == ZONE_SEA_RETURN)
        land = Z == ZONE_LAND
        active = Z == ZONE_ACTIVE
        nd = max(int(disk.sum()), 1)
        st.update(land_pct=round(100 * land.sum() / nd, 2), sea_pct=round(100 * sea.sum() / nd, 2),
                  active_pct=round(100 * active.sum() / nd, 3),
                  active_m2=round(float(active.sum()) * px_m2),
                  whitewater_m2=round(float((active & dilate(land, 150 / mpp)).sum()) * px_m2))
    else:
        sea = R <= (g.get('range_m') or grid * mpp / 2)

    if var_b:
        Vv = palette_index(var_b).astype(np.float32)
        m = sea & (Vv > 0)
        if m.any():
            vals = Vv[m] / 255.0 * var_scale_max
            st.update(motion_mean=round(float(vals.mean()), 3), motion_p90=round(float(np.percentile(vals, 90)), 3))

    # echo "sparkle": how much of the open water lights up on each sweep
    sea_ring = sea & ring
    n_sea, n_ring = max(int(sea.sum()), 1), max(int(sea_ring.sum()), 1)
    pct_all, pct_ring, lvl = [], [], []
    stack = []
    for _, b in frames:
        L = frame_levels(b)
        if L.shape != (grid, grid):
            continue
        lit = L > 0
        pct_all.append(100 * (lit & sea).sum() / n_sea)
        pct_ring.append(100 * (lit & sea_ring).sum() / n_ring)
        if (lit & sea).any():
            lvl.append(float(L[lit & sea].mean()))
        if full:
            stack.append(L[sea_ring])
    st['frames_used'] = len(pct_all)
    if pct_all:
        st.update(sparkle_pct=round(float(np.mean(pct_all)), 3), sparkle_ring_pct=round(float(np.mean(pct_ring)), 3),
                  echo_level=round(float(np.mean(lvl)), 2) if lvl else None)
    if full and len(stack) >= 64:
        st.update(wave_rhythm(stack, v))

    st.update(track_stats(tracks_geo))
    return st


def wave_rhythm(stack, v):
    """Experimental: the dominant wave period seen by the radar.
    Waves passing a patch of sea make its echo flicker at the wave period; average that flicker
    spectrum over every patch that lights up often enough and look for a clear peak (4–16 s)."""
    A = np.stack(stack, 1).astype(np.float32)          # pixels × time
    N = A.shape[1]
    keep = (A > 0).mean(1) >= 0.10
    A = A[keep]
    out = {'rhythm_px': int(A.shape[0])}
    if A.shape[0] < 500:
        return out
    if A.shape[0] > 40000:
        A = A[np.random.default_rng(0).choice(A.shape[0], 40000, replace=False)]
    rel = (v.get('times') or {}).get('rel') or []
    dt = (rel[-1] - rel[0]) / (len(rel) - 1) if len(rel) > 2 else 1.3
    A -= A.mean(1, keepdims=True)
    P = (np.abs(np.fft.rfft(A * np.hanning(N), axis=1)) ** 2).mean(0)
    f = np.fft.rfftfreq(N, dt)
    band = (f >= 1 / 16) & (f <= 1 / 4)
    if band.sum() < 5:
        return out
    pb, fb = P[band], f[band]
    # smooth a little so one lucky bin doesn't win; compare against the flat "noise floor"
    # (median power over every frequency above 1/30 Hz) so calm, featureless spectra score ~1
    sm = np.convolve(pb, np.ones(3) / 3, mode='same')
    k = int(sm.argmax())
    floor = float(np.median(P[f >= 1 / 30]))
    out.update(radar_period_s=round(float(1 / fb[k]), 2), radar_period_q=round(float(sm[k] / floor), 2) if floor > 0 else None)
    return out


def track_stats(geo):
    feats = (geo or {}).get('features') or []
    sp = [float(f['properties'].get('speed_kn')) for f in feats
          if f.get('properties') and f['properties'].get('speed_kn') is not None]
    return {'n_tracks': len(feats), 'max_speed_kn': round(max(sp), 1) if sp else None,
            'mean_speed_kn': round(float(np.mean(sp)), 1) if sp else None}


def track_rows(v, geo):
    """One tidy row per tracked contact (with a thinned-out path for the map)."""
    rows = []
    for f in (geo or {}).get('features') or []:
        p = f.get('properties') or {}
        c = (f.get('geometry') or {}).get('coordinates') or []
        if len(c) < 2:
            continue
        step = max(1, len(c) // 8)
        pts = c[::step]
        if pts[-1] != c[-1]:
            pts.append(c[-1])
        rows.append({'collect_id': v['selected_id'], 'time_utc': v['selected_at'], 'track_id': p.get('track_id'),
                     'speed_kn': p.get('speed_kn'), 'heading_deg': p.get('heading_deg'),
                     'duration_s': p.get('duration_s'), 'path_m': p.get('path_m'),
                     'straightness': p.get('straightness'),
                     'path': ';'.join(f'{x:.5f},{y:.5f}' for x, y in pts)})
    return rows
