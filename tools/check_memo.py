"""One-off diagnostic: the newest rows in the UNE observations layer behind the weather-station pages."""
import json, urllib.parse, urllib.request
from datetime import datetime, timezone
URL = 'https://services7.arcgis.com/0vd30ZJwMECKNLFu/arcgis/rest/services/UNE_observations_data_layer_view/FeatureServer/0/query'
out = open('ext/memo_check.txt', 'w')
def q(**kw):
    body = urllib.parse.urlencode(dict(f='json', **kw)).encode()
    return json.load(urllib.request.urlopen(urllib.request.Request(URL, data=body, headers={'User-Agent': 'UNE-Marine-Monitoring-Network/1.0'}), timeout=90))
try:
    meta = json.load(urllib.request.urlopen(URL[:-6] + '?f=json', timeout=60))
    out.write('editingInfo: ' + json.dumps(meta.get('editingInfo')) + '\n')
    out.write('timeField fields: ' + ', '.join(f['name'] for f in meta.get('fields', []) if f.get('type') == 'esriFieldTypeDate') + '\n')
    js = q(where='1=1', outFields='*', orderByFields='timestamp DESC', resultRecordCount=8, returnGeometry='false')
    for f in js.get('features', []):
        a = f['attributes']; t = a.get('timestamp')
        nn = [k for k, v in a.items() if v is not None and k != 'timestamp']
        out.write(f"{datetime.fromtimestamp(t / 1000, timezone.utc).isoformat() if t else t}  non-null: {len(nn)} e.g. {nn[:6]}\n")
    js = q(where="timestamp > timestamp '2026-11-01 04:00:00'", returnCountOnly='true')
    out.write('rows after 2026-11-01 04:00 UTC: ' + json.dumps(js) + '\n')
    js = q(where="ram_wind_speed IS NOT NULL", outFields='timestamp,ram_wind_speed', orderByFields='timestamp DESC', resultRecordCount=3, returnGeometry='false')
    for f in js.get('features', []):
        a = f['attributes']; out.write(f"ram wind: {datetime.fromtimestamp(a['timestamp'] / 1000, timezone.utc).isoformat()} {a['ram_wind_speed']}\n")
except Exception as e:
    out.write('ERROR ' + repr(e) + '\n')
out.close(); print(open('ext/memo_check.txt').read())
