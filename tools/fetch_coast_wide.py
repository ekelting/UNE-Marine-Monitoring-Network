"""One-off: Gulf of Maine coastline from Kennebunk to Boothbay (OpenStreetMap natural=coastline), simplified, for the UNE trip-check map."""
import json, math, urllib.request, urllib.parse
q = '[out:json][timeout:180][maxsize:1073741824];way["natural"="coastline"](42.95,-70.9,44.2,-69.2);out geom;'
d = None
for url in ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter', 'https://maps.mail.ru/osm/tools/overpass/api/interpreter']:
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, data=urllib.parse.urlencode({'data': q}).encode(), headers={'User-Agent': 'UNE-Marine-Monitoring-Network/1.0'}), timeout=300)
        d = json.load(r); break
    except Exception as e:
        print(url, e)
def rdp(p, eps):
    if len(p) < 3: return p
    a, b = p[0], p[-1]; dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy)
    best, i0 = 0, 0
    for i in range(1, len(p) - 1):
        q_ = p[i]
        dd = abs(dy * q_[0] - dx * q_[1] + b[0] * a[1] - b[1] * a[0]) / L if L > 1e-12 else math.hypot(q_[0] - a[0], q_[1] - a[1])
        if dd > best: best, i0 = dd, i
    return rdp(p[:i0 + 1], eps)[:-1] + rdp(p[i0:], eps) if best > eps else [a, b]
def simp(p, eps):
    if len(p) > 3 and p[0] == p[-1]:
        h = len(p) // 2; return rdp(p[:h + 1], eps)[:-1] + rdp(p[h:], eps)
    return rdp(p, eps)
ways = [[[round(x['lon'], 5), round(x['lat'], 5)] for x in w['geometry']] for w in d['elements'] if w['type'] == 'way']
out = {'source': 'OpenStreetMap contributors (ODbL), natural=coastline', 'bbox': [42.95, -70.9, 44.2, -69.2],
       'fine': [s for s in (simp(w, 0.00012) for w in ways) if len(s) > 1],
       'coarse': [s for s in (simp(w, 0.0008) for w in ways) if len(s) > 1 and (len(s) > 2 or math.dist(s[0], s[-1]) > 0.004)]}
json.dump(out, open('ext/gom_coast.json', 'w'), separators=(',', ':'))
print(len(ways), 'ways;', sum(map(len, out['fine'])), 'fine pts;', sum(map(len, out['coarse'])), 'coarse pts')
