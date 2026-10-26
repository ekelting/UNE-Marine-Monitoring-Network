"""One-off: Gulf of Maine coastline from Kennebunk to Boothbay (OpenStreetMap natural=coastline), simplified, for the UNE trip-check map.
Fetched in tiles; progress and errors go to ext/coast_log.txt so a failure can be read from the branch."""
import json, math, time, traceback, urllib.request, urllib.parse
LOG = open('ext/coast_log.txt', 'w')
def log(*a):
    print(*a); LOG.write(' '.join(map(str, a)) + '\n'); LOG.flush()
def rdp(p, eps):                       # iterative Ramer-Douglas-Peucker
    keep = [False] * len(p); keep[0] = keep[-1] = True; st = [(0, len(p) - 1)]
    while st:
        i, j = st.pop(); a, b = p[i], p[j]; dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy); best, k = 0, -1
        for m in range(i + 1, j):
            q = p[m]
            dd = abs(dy * q[0] - dx * q[1] + b[0] * a[1] - b[1] * a[0]) / L if L > 1e-12 else math.hypot(q[0] - a[0], q[1] - a[1])
            if dd > best: best, k = dd, m
        if k > 0 and best > eps:
            keep[k] = True; st += [(i, k), (k, j)]
    return [x for x, f in zip(p, keep) if f]
def simp(p, eps):
    if len(p) > 3 and p[0] == p[-1]:
        h = len(p) // 2; return rdp(p[:h + 1], eps)[:-1] + rdp(p[h:], eps)
    return rdp(p, eps)
ways = {}
tiles = [(la, lo) for la in (42.95, 43.375, 43.8) for lo in (-70.9, -70.3, -69.75)]
for la, lo in tiles:
    bb = (la, lo, min(la + 0.425, 44.2), min(lo + 0.6, -69.2))
    q = f'[out:json][timeout:180];way["natural"="coastline"]({bb[0]},{bb[1]},{bb[2]},{bb[3]});out geom;'
    for url in ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter', 'https://overpass.private.coffee/api/interpreter']:
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, data=urllib.parse.urlencode({'data': q}).encode(), headers={'User-Agent': 'UNE-Marine-Monitoring-Network/1.0'}), timeout=240)
            d = json.load(r)
            for w in d['elements']:
                if w['type'] == 'way' and 'geometry' in w:
                    ways[w['id']] = [[round(x['lon'], 5), round(x['lat'], 5)] for x in w['geometry']]
            log('tile', bb, 'ok from', url, len(d['elements']), 'ways; total', len(ways)); break
        except Exception as e:
            log('tile', bb, url, repr(e)); time.sleep(5)
try:
    W = list(ways.values())
    out = {'source': 'OpenStreetMap contributors (ODbL), natural=coastline', 'bbox': [42.95, -70.9, 44.2, -69.2],
           'fine': [s for s in (simp(w, 0.00012) for w in W) if len(s) > 1],
           'coarse': [s for s in (simp(w, 0.0008) for w in W) if len(s) > 2 or math.dist(s[0], s[-1]) > 0.004]}
    json.dump(out, open('ext/gom_coast.json', 'w'), separators=(',', ':'))
    log(len(W), 'ways;', sum(map(len, out['fine'])), 'fine pts;', sum(map(len, out['coarse'])), 'coarse pts')
except Exception:
    log(traceback.format_exc())
