"""One-off: the tidal Saco River (water area and centreline) from the mouth up to the Biddeford/Saco dams, from OpenStreetMap."""
import json, time, urllib.request, urllib.parse
bb = '43.452,-70.46,43.502,-70.365'
q = (f'[out:json][timeout:120];(way["natural"="water"]({bb});relation["natural"="water"]({bb});way["waterway"="riverbank"]({bb});'
     f'way["waterway"="river"]({bb});way["waterway"="dam"]({bb});way["waterway"="weir"]({bb}););out geom;')
LOG = open('ext/river_log.txt', 'w')
for url in ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter', 'https://overpass.private.coffee/api/interpreter']:
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, data=urllib.parse.urlencode({'data': q}).encode(), headers={'User-Agent': 'UNE-Marine-Monitoring-Network/1.0'}), timeout=180)
        d = json.load(r); LOG.write(f'ok {url} {len(d["elements"])}\n'); break
    except Exception as e:
        LOG.write(f'{url} {e!r}\n'); time.sleep(5)
out = []
for e in d['elements']:
    g = lambda gm: [[round(p['lon'], 6), round(p['lat'], 6)] for p in gm]
    if e['type'] == 'way' and 'geometry' in e:
        out.append({'id': e['id'], 'type': 'way', 'tags': e.get('tags', {}), 'geom': g(e['geometry'])})
    elif e['type'] == 'relation':
        out.append({'id': e['id'], 'type': 'relation', 'tags': e.get('tags', {}),
                    'members': [{'role': m.get('role'), 'geom': g(m['geometry'])} for m in e.get('members', []) if m.get('type') == 'way' and 'geometry' in m]})
json.dump(out, open('ext/saco_river.json', 'w'), separators=(',', ':'))
LOG.write(f'{len(out)} features: ' + '; '.join(f"{o['type']} {o['tags'].get('name', '')} {o['tags'].get('natural', o['tags'].get('waterway', ''))}" for o in out) + '\n')
