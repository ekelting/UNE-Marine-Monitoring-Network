"""One-off: Saco Bay coastline from OpenStreetMap (Overpass API) for the Analysis map."""
import json, os, urllib.parse, urllib.request
q = '[out:json][timeout:120];(way["natural"="coastline"](43.37,-70.47,43.57,-70.27););out geom;'
req = urllib.request.Request('https://overpass-api.de/api/interpreter', data=urllib.parse.urlencode({'data': q}).encode(),
                             headers={'User-Agent': 'UNE-marine-monitoring/1.0'})
js = json.load(urllib.request.urlopen(req, timeout=180))
lines = [[[round(p['lon'], 5), round(p['lat'], 5)] for p in el['geometry']] for el in js['elements'] if el.get('geometry')]
os.makedirs('ext', exist_ok=True)
json.dump({'source': 'OpenStreetMap contributors (ODbL), natural=coastline', 'lines': lines}, open('ext/saco_coast.json', 'w'), separators=(',', ':'))
print(len(lines), 'ways', sum(map(len, lines)), 'points')
