"""One-off: jetties, breakwaters and piers around the Saco River mouth from OpenStreetMap (Overpass API)."""
import json, urllib.request, urllib.parse
q = '[out:json][timeout:60];(way["man_made"~"breakwater|groyne|pier"](43.43,-70.42,43.52,-70.29););out geom;'
for url in ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']:
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, data=urllib.parse.urlencode({'data': q}).encode(), headers={'User-Agent': 'UNE-Marine-Monitoring-Network/1.0'}), timeout=90)
        d = json.load(r); break
    except Exception as e:
        print(url, e)
out = [{'id': w['id'], 'tags': w.get('tags', {}), 'geom': [[round(p['lon'], 6), round(p['lat'], 6)] for p in w['geometry']]} for w in d['elements'] if w['type'] == 'way']
json.dump(out, open('ext/saco_jetty.json', 'w'))
print(len(out), [w['tags'].get('name') for w in out])
