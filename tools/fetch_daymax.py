"""One-off: Portland (8418150) daily highest water from NOAA hourly heights, 1912 to now."""
import io, os, time, urllib.parse, urllib.request
import pandas as pd
CO = 'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?'
out = []
for y in range(1912, 2027):
    q = dict(product='hourly_height', station='8418150', begin_date=f'{y}0101', end_date=f'{y}1231', datum='MLLW', units='metric', time_zone='lst_ldt', format='csv', application='UNE_MMN')
    for k in range(3):
        try:
            d = pd.read_csv(io.BytesIO(urllib.request.urlopen(urllib.request.Request(CO + urllib.parse.urlencode(q), headers={'User-Agent': 'UNE-MMN'}), timeout=120).read()), skipinitialspace=True)
            d.columns = [c.strip() for c in d.columns]
            if 'Water Level' in d:
                s = pd.Series(pd.to_numeric(d['Water Level'], errors='coerce').values, index=pd.to_datetime(d['Date Time']))
                dm = s.resample('D').agg(['max', 'count']); dm = dm[dm['count'] >= 20]
                out.append(dm['max'].round(3)); print(y, len(dm))
            else:
                print(y, 'no data', d.columns.tolist()[:3])
            break
        except Exception as e:
            print(y, 'retry', e); time.sleep(5)
os.makedirs('ext', exist_ok=True)
s = pd.concat(out); s.index.name = 'date'; s.name = 'max_m'
s.to_csv('ext/portland_daymax.csv')
print('rows', len(s))
