"""One-off diagnostic: where are the UNE observations going after Nov 1? Newest rows by object id, rows without a time,
and every service the UNE organisation publishes, with each layer's newest edit."""
import json, urllib.parse, urllib.request
from datetime import datetime, timezone
BASE = 'https://services7.arcgis.com/0vd30ZJwMECKNLFu/arcgis/rest/services'
out = open('ext/memo_check.txt', 'w')
def W(*a): out.write(' '.join(map(str, a)) + '\n'); out.flush()
def get(url, **kw):
    if kw:
        return json.load(urllib.request.urlopen(urllib.request.Request(url, data=urllib.parse.urlencode(dict(f='json', **kw)).encode(), headers={'User-Agent': 'UNE-Marine-Monitoring-Network/1.0'}), timeout=90))
    return json.load(urllib.request.urlopen(url + ('&' if '?' in url else '?') + 'f=json', timeout=90))
ts = lambda ms: datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat() if ms else ms
try:
    view = BASE + '/UNE_observations_data_layer_view/FeatureServer/0'
    js = get(view + '/query', where='1=1', outFields='OBJECTID,timestamp', orderByFields='OBJECTID DESC', resultRecordCount=6, returnGeometry='false')
    W('newest by OBJECTID in the view:'); [W('  ', f['attributes']['OBJECTID'], ts(f['attributes']['timestamp'])) for f in js.get('features', [])]
    W('rows with no timestamp:', get(view + '/query', where='timestamp IS NULL', returnCountOnly='true'))
    meta = get(view); W('view definitionQuery:', meta.get('viewDefinitionQuery'), '| definitionExpression:', meta.get('definitionExpression'))
    svcs = get(BASE)
    W('\nservices in this ArcGIS organisation:')
    for s in svcs.get('services', []):
        name = s['name']; W(' *', name, s['type'])
        if s['type'] != 'FeatureServer' or not any(k in name.lower() for k in ('une', 'obs', 'memo', 'licor', 'station', 'weather', 'ram')):
            continue
        try:
            fs = get(f"{BASE}/{name}/FeatureServer")
            for lyr in fs.get('layers', []) + fs.get('tables', []):
                lm = get(f"{BASE}/{name}/FeatureServer/{lyr['id']}")
                ei = lm.get('editingInfo') or {}
                dates = [f['name'] for f in lm.get('fields', []) if f.get('type') == 'esriFieldTypeDate']
                newest = None
                if dates:
                    q = get(f"{BASE}/{name}/FeatureServer/{lyr['id']}/query", where='1=1', outFields=dates[0], orderByFields=f'{dates[0]} DESC', resultRecordCount=1, returnGeometry='false')
                    fe = q.get('features') or []
                    newest = ts(fe[0]['attributes'][dates[0]]) if fe else None
                W(f"     layer {lyr['id']} {lyr['name']}: last data edit {ts(ei.get('dataLastEditDate'))}; date fields {dates}; newest {newest}")
        except Exception as e:
            W('     error', repr(e))
except Exception as e:
    W('ERROR', repr(e))
out.close(); print(open('ext/memo_check.txt').read())
