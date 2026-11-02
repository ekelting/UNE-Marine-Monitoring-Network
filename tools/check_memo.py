"""One-off diagnostic: newest rows in the UNE observations layer (after the ArcGIS script was restarted)."""
import json, urllib.parse, urllib.request
from datetime import datetime, timezone
URL = 'https://services7.arcgis.com/0vd30ZJwMECKNLFu/arcgis/rest/services/UNE_observations_data_layer_view/FeatureServer/0'
out = open('ext/memo_check.txt', 'w')
def q(**kw):
    return json.load(urllib.request.urlopen(urllib.request.Request(URL + '/query', data=urllib.parse.urlencode(dict(f='json', **kw)).encode(), headers={'User-Agent': 'UNE-Marine-Monitoring-Network/1.0'}), timeout=90))
ts = lambda ms: datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()
meta = json.load(urllib.request.urlopen(URL + '?f=json', timeout=60))
out.write('last data edit: ' + ts((meta.get('editingInfo') or {}).get('dataLastEditDate', 0)) + '\n')
for field in ['ram_wind_speed', 'une363_wind_speed', 'greatpond_water_level', 'marsh_temperature']:
    js = q(where=f'{field} IS NOT NULL', outFields='timestamp', orderByFields='timestamp DESC', resultRecordCount=1, returnGeometry='false')
    fe = js.get('features') or []
    out.write(f"{field}: newest {ts(fe[0]['attributes']['timestamp']) if fe else None}\n")
out.write('rows after 2026-11-01 05:00 UTC: ' + json.dumps(q(where="timestamp > timestamp '2026-11-01 05:00:00'", returnCountOnly='true')) + '\n')
out.close(); print(open('ext/memo_check.txt').read())
