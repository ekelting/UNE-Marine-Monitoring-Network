"""sandmap.py: map geometry for the "Where does the sand go?" drawing on Saco Bay, explained.

Real shoreline from OpenStreetMap (ext/saco_coast.json: natural=coastline; ext/saco_jetty.json: the Camp Ellis jetties and
the Old Orchard Beach pier), projected to a 320 x 282 px map, north up (about 34 px per km), and simplified.
OSM closes the coastline across the Saco River mouth, so the river channel inside the jetties is hand-traced.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LON0, LON1, LAT0, LAT1 = -70.42, -70.29, 43.435, 43.518
CL = math.cos(math.radians(43.48))
K = 320 / ((LON1 - LON0) * CL)


def P(lon, lat):
    return ((lon - LON0) * CL * K, (LAT1 - lat) * K)


def rdp(pts, eps):
    """Douglas-Peucker line simplification."""
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    n = math.hypot(dx, dy) or 1e-9
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        x, y = pts[i]
        d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / n
        if d > dmax:
            dmax, idx = d, i
    return rdp(pts[:idx + 1], eps)[:-1] + rdp(pts[idx:], eps) if dmax > eps else [pts[0], pts[-1]]


def path(pts, close=True):
    return 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in pts) + (' Z' if close else '')


def chains():
    """Join the OSM coastline ways end to start (OSM keeps the land on the left of the drawing direction)."""
    ways = [list(map(list, l)) for l in json.load(open(os.path.join(HERE, 'ext', 'saco_coast.json')))['lines']]
    out = []
    while ways:
        c = ways.pop(0)
        changed = True
        while changed:
            changed = False
            for i, w in enumerate(ways):
                if w[0] == c[-1]:
                    c = c + w[1:]; ways.pop(i); changed = True; break
                if w[-1] == c[0]:
                    c = w + c[1:]; ways.pop(i); changed = True; break
        out.append(c)
    return out


def nearest(main, lon, lat):
    return min(range(len(main)), key=lambda i: (main[i][0] - lon) ** 2 + (main[i][1] - lat) ** 2)


def build():
    ch = chains()
    jet = json.load(open(os.path.join(HERE, 'ext', 'saco_jetty.json')))
    main = max(ch, key=len)
    ext = main + [[-70.197, 43.62], [-70.48, 43.62], [-70.48, 43.34], [-70.442, 43.34]]   # close the mainland to the west
    out = {'K': K, 'land': path(rdp([P(*p) for p in ext], .45)), 'islands': []}
    for c in ch:
        if c is main or c[0] != c[-1]:
            continue
        pts = [P(*p) for p in c]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        if max(xs) < -5 or min(xs) > 325 or max(ys) < -5 or min(ys) > 287 or (max(xs) - min(xs)) * (max(ys) - min(ys)) < 1.5:
            continue
        m = len(pts) // 2
        out['islands'].append(path(rdp(pts[:m + 1], .35)[:-1] + rdp(pts[m:], .35)))
    i0, i1, i2 = nearest(main, -70.3784, 43.4631), nearest(main, -70.3606, 43.5300), nearest(main, -70.3870, 43.5010)
    beach = [P(*p) for p in main[i0:i1]]                       # Saco Bay beach from the Camp Ellis jetty north
    out['beach'] = path(rdp(beach, .4), False)
    out['grains'] = path(rdp([P(*p) for p in main[i0:i2]], .4), False)   # sand grains travel ~4.5 km north
    N = [(-70.3784, 43.4629), (-70.3835, 43.4652), (-70.3900, 43.4668), (-70.3975, 43.4680), (-70.4045, 43.4712), (-70.4125, 43.4760), (-70.4230, 43.4800)]
    S = [(-70.4230, 43.4745), (-70.4105, 43.4703), (-70.4000, 43.4652), (-70.3930, 43.4612), (-70.3892, 43.4594), (-70.3840, 43.4595), (-70.3784, 43.4602)]
    out['river'] = path([P(*p) for p in N + S])
    out['buoy'] = P(-70.389337, 43.460297)                     # the UNE buoy in the cove west of Jordan Point
    out['jetties'] = [path([P(*p) for p in w['geom']]) for w in jet if w['tags'].get('man_made') == 'breakwater']
    out['pier'] = [path([P(*p) for p in w['geom']]) for w in jet if w['tags'].get('name') == 'Old Orchard Beach Pier']
    out['coast_x'] = {y: round(min(beach, key=lambda p: abs(p[1] - y))[0], 1) for y in range(0, 290, 10)}
    out['pts'] = {k: [round(v, 1) for v in P(*ll)] for k, ll in {
        'campellis': (-70.3784, 43.4631), 'oob': (-70.3730, 43.5150), 'wibuoy': (-70.317699, 43.455593)}.items()}
    return out
