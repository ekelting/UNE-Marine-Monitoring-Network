"""
Offline stand-in for CUMULUS + S3, producing images in the same formats the real site serves
(1024² RGBA sweep frames in the 15-colour magma ramp; indexed zones/variability PNGs; tracks GeoJSON).
Used by tests/run_offline.py to exercise fetch.py and build.py end to end without network.
"""
import io
import json
import math

import numpy as np
from PIL import Image

import core

G = 1024
LAT, LON = 43.467048, -70.356464
N_COLLECTS = 30
T0 = np.datetime64('2026-10-11T08:07:55')
_cache = {}


def collect_list():
    out = []
    for i in range(N_COLLECTS):
        t = T0 + np.timedelta64(i, 'h')
        out.append((f'{i:08d}-0000-4000-8000-{i:012d}', str(t) + '+00:00'))
    return out[::-1]


def wind(i):
    return 2 + 9 * max(0.0, math.sin(i / N_COLLECTS * math.pi * 1.6))  # m/s


def _geom():
    if 'geom' in _cache:
        return _cache['geom']
    y, x = np.mgrid[0:G, 0:G]
    r = np.hypot(x - 511.5, y - 511.5)
    disk = r <= 512
    coast = 160 + 60 * np.sin(y / 140.0)
    land = disk & (x < coast)
    isl = disk & (np.hypot(x - 700, y - 760) < 25)
    land |= isl
    active = disk & ~land & (x < coast + 18) & (x >= coast)
    sea = disk & ~land & ~active
    _cache['geom'] = (x, y, r, disk, land, active, sea)
    return _cache['geom']


def png_indexed(idx, pal):
    im = Image.fromarray(idx.astype(np.uint8), 'P')
    p = list(pal) + [0] * (768 - len(pal))
    im.putpalette(p)
    im.info['transparency'] = 0
    b = io.BytesIO()
    im.save(b, 'PNG', transparency=0)
    return b.getvalue()


def zones_png():
    x, y, r, disk, land, active, sea = _geom()
    Z = np.zeros((G, G), np.uint8)
    Z[land] = 1
    Z[active] = 2
    Z[sea] = 3
    pal = [0, 0, 0, 249, 115, 22, 253, 224, 71, 125, 211, 252, 14, 165, 233, 168, 85, 247]
    return png_indexed(Z, pal)


def var_png(i):
    x, y, r, disk, land, active, sea = _geom()
    V = np.zeros((G, G), np.uint8)
    rng = np.random.default_rng(i)
    V[sea] = np.clip(rng.normal(30 + 8 * wind(i), 20, sea.sum()), 1, 255)
    V[land] = 3
    V[active] = 200
    ramp = np.linspace(0, 1, 256)
    cm = np.stack([68 + 185 * ramp, 1 + 230 * ramp, 84 - 50 * ramp], 1)   # rough viridis stand-in
    return png_indexed(V, cm.astype(int).flatten().tolist())


def frame_png(i, k):
    x, y, r, disk, land, active, sea = _geom()
    rng = np.random.default_rng(i * 1000 + k)
    w = wind(i)
    t = k * 1.3
    period, wl = 8.0, 100.0
    phase = 2 * math.pi * ((x * 5.27) / wl - t / period)          # waves rolling toward the coast (west)
    p = (0.004 + 0.02 * max(w - 3, 0)) * (1 + 0.9 * np.sin(phase)) * np.exp(-r / 600)
    lit = sea & (rng.random((G, G)) < p)
    L = np.zeros((G, G), np.uint8)
    L[lit] = rng.integers(1, 6, lit.sum())
    L[land] = 15
    L[active] = rng.integers(6, 15, active.sum())
    rgba = np.zeros((G, G, 4), np.uint8)
    m = L > 0
    rgba[m, :3] = np.array(core.FRAME_PALETTE, np.uint8)[L[m] - 1]
    rgba[m, 3] = 255
    b = io.BytesIO()
    Image.fromarray(rgba, 'RGBA').save(b, 'PNG', compress_level=1)
    return b.getvalue()


def composite_png(i):
    return frame_png(i, 0)


def tracks(i):
    rng = np.random.default_rng(i)
    feats = []
    for k in range(int(rng.integers(1, 9))):
        lon0, lat0 = LON + rng.uniform(-0.02, 0.02), LAT + rng.uniform(-0.015, 0.015)
        hd = rng.uniform(0, 2 * math.pi)
        sp = float(rng.uniform(1, 28))
        pts = [[lon0 + j * 0.0004 * math.sin(hd), lat0 + j * 0.0003 * math.cos(hd)] for j in range(30)]
        feats.append({'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': pts},
                      'properties': {'track_id': k, 'speed_kn': round(sp, 2), 'heading_deg': math.degrees(hd) % 360,
                                     'duration_s': 60.0, 'path_m': 400.0, 'straightness': 0.9}})
    return {'type': 'FeatureCollection', 'features': feats}


def viewer(cid):
    i = int(cid[:8])
    t = str(T0 + np.timedelta64(i, 'h')) + '+00:00'
    n = 229
    return {'available': True, 'selected_id': cid, 'selected_at': t,
            'georef': {'lat': LAT, 'lon': LON, 'range_m': 2700, 'mpp': 5.2734, 'heading': 0, 'grid': G},
            'times': {'rel': [round(k * 1.302, 3) for k in range(n)]}, 'frame_count': n,
            'composite': f'fake://comp/{i}', 'frames': [f'fake://frame/{i}/{k}' for k in range(n)],
            'layers': {'items': [
                {'key': 'variability', 'kind': 'raster', 'url': f'fake://var/{i}', 'empty': False, 'stats': {'scale_max': 6}},
                {'key': 'zones', 'kind': 'raster', 'url': f'fake://zones/{i}', 'empty': False},
                {'key': 'tracks', 'kind': 'vector', 'url': f'fake://tracks/{i}', 'empty': False}]}}


class Resp:
    def __init__(self, content=b'', text=''):
        self.content, self.text, self.status_code = content, text, 200

    def json(self):
        return json.loads(self.text)


class FakeHttp:
    def __init__(self):
        self.errors = []

    def get(self, url, *, accept=None, params=None, **kw):
        params = params or {}
        if url == core.PAGE:
            rows = collect_list()
            pg = int(params.get('page', 1))
            chunk = rows[(pg - 1) * 50: pg * 50]
            html = ''.join(f'<a data-collect="{c}" href="?collect={c}"><div data-utc="{t}"></div></a>' for c, t in chunk)
            html += ''.join(f'<a href="?all=1&page={p}">' for p in range(1, (len(rows) - 1) // 50 + 2))
            return Resp(text=html)
        if url == core.VIEWER:
            return Resp(text=json.dumps(viewer(params['collect'])))
        kind, *rest = url.replace('fake://', '').split('/')
        i = int(rest[0])
        if kind == 'comp':
            return Resp(composite_png(i))
        if kind == 'frame':
            return Resp(frame_png(i, int(rest[1])))
        if kind == 'zones':
            return Resp(zones_png())
        if kind == 'var':
            return Resp(var_png(i))
        if kind == 'tracks':
            return Resp(text=json.dumps(tracks(i)))
        raise RuntimeError(url)

    def json(self, url, **kw):
        return self.get(url, **kw).json()

    def content(self, url, **kw):
        return self.get(url, **kw).content
