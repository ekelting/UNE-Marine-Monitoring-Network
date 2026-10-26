"""One-off: the UNE trip-check distance bands (rings around the boat launch), trimmed to water.
Land comes from the OpenStreetMap coastline (natural=coastline, land on the left of each way), fetched once on the
analysis-sources branch (ext/gom_coast.json). Writes web/bands.json: one water-only MultiPolygon per band, [lat, lon].
Usage: python tools/make_trip_bands.py path/to/gom_coast.json"""
import json, math, os, sys
from shapely.geometry import LineString, Polygon, box, mapping
from shapely.ops import polygonize, unary_union
from shapely.strtree import STRtree

LAUNCH = (43.460385, -70.386006)
RINGS = [0, 1, 3, 6, 9, 12, 15, 18, 21, 24]
KX = math.cos(math.radians(LAUNCH[0]))
BBOX = box(-70.90, 43.05, -69.80, 43.79)        # the 24 nm circle, cut at the north edge of the area the coastline download covers fully

def pt(nmi, brg):
    return (LAUNCH[1] + nmi * math.sin(math.radians(brg)) / (60 * KX), LAUNCH[0] + nmi * math.cos(math.radians(brg)) / 60)

def disc(r):
    return Polygon([pt(r, b / 2) for b in range(0, 720)])

coast = json.load(open(sys.argv[1]))['fine']
lines = [LineString(l) for l in coast if len(l) > 1]
lines = [l.intersection(BBOX.buffer(0.05)) for l in lines]
segs = []                                         # coastline segments, to tell which side is land
for l in coast:
    for a, b in zip(l, l[1:]):
        segs.append((a, b))
seg_geom = [LineString(s) for s in segs]
tree = STRtree(seg_geom)
faces = list(polygonize(unary_union([g for g in lines if not g.is_empty] + [BBOX.exterior])))
land = []
for f in faces:
    if not f.intersects(BBOX) or f.area < 1e-9:
        continue
    p = f.representative_point()
    i = tree.nearest(p)
    (ax, ay), (bx, by) = segs[i]
    if (bx - ax) * (p.y - ay) - (by - ay) * (p.x - ax) > 0:       # left of the coastline = land
        land.append(f)
land = unary_union(land).intersection(BBOX)
print('land area (deg²):', round(land.area, 4), 'faces:', len(faces))
out = []
for r0, r1 in zip(RINGS, RINGS[1:]):
    band = disc(r1) if r0 == 0 else disc(r1).difference(disc(r0))
    water = band.intersection(BBOX).difference(land).simplify(0.0002)
    polys = [water] if water.geom_type == 'Polygon' else [g for g in getattr(water, 'geoms', []) if g.geom_type == 'Polygon']
    polys = [p for p in polys if p.area > 2e-6]
    out.append([[[[round(y, 5), round(x, 5)] for x, y in ring.coords] for ring in [p.exterior, *p.interiors]] for p in polys])
    print(f'{r0}-{r1} nm: {len(polys)} pieces, {sum(len(p.exterior.coords) for p in polys)} points')
# the dashed ring lines, over water only, and a label spot on each (open water, roughly east-southeast)
ring_lines, labels = [], []
for r in RINGS[1:]:
    circle = LineString([pt(r, b / 2) for b in range(0, 721)])
    wl = circle.intersection(BBOX).difference(land)
    parts = [wl] if wl.geom_type == 'LineString' else list(getattr(wl, 'geoms', []))
    parts = [g for g in parts if g.geom_type == 'LineString' and g.length > 0.002]
    ring_lines.append([[[round(y, 5), round(x, 5)] for x, y in g.simplify(0.0001).coords] for g in parts])
    best = None
    for b in list(range(60, 130, 5)) + list(range(130, 200, 5)) + list(range(0, 60, 5)):
        x, y = pt(r, b)
        if not land.contains(LineString([pt(r, b - 1), pt(r, b + 1)]).centroid) and BBOX.contains(LineString([pt(r, b - 1), pt(r, b + 1)]).centroid):
            best = (round(y, 5), round(x, 5)); break
    labels.append(best)
json.dump({'rings': RINGS, 'launch': LAUNCH, 'bands': out, 'lines': ring_lines, 'labels': labels, 'source': 'OpenStreetMap contributors (coastline)'},
          open(os.path.join(os.path.dirname(__file__), '..', 'web', 'bands.json'), 'w'), separators=(',', ':'))
