"""One-off download of outside reference data for the analysis menu (not part of the hourly site build)."""
import gzip, io, json, os, time, urllib.request, urllib.parse
OUT = 'ext'; os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'UNE-marine-monitoring-analysis/1.0 (ekelting/UNE-Marine-Monitoring-Network)'}
log = []
def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.read()
        except Exception as e:
            err = e; time.sleep(5 * (i + 1))
    raise err
def save(name, data):
    open(os.path.join(OUT, name), 'wb').write(data); log.append(f'ok {name} {len(data)} bytes')
def tryit(name, fn):
    try: fn()
    except Exception as e: log.append(f'FAIL {name}: {e}')

CO = 'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?'
def coops(product, begin, end, extra=''):
    q = dict(product=product, station='8418150', begin_date=begin, end_date=end, datum='MLLW', units='metric', time_zone='gmt', format='csv', application='UNE_MMN')
    return get(CO + urllib.parse.urlencode(q) + extra)
# Portland ME tide gauge: hourly observed + predicted, monthly means since 1912
tryit('portland_hourly', lambda: save('portland_hourly.csv', coops('hourly_height', '20251101', '20260430') + b'\n' + coops('hourly_height', '20260501', '20261013').split(b'\n', 1)[1]))
tryit('portland_pred', lambda: save('portland_pred.csv', coops('predictions', '20251101', '20260430', '&interval=h') + b'\n' + coops('predictions', '20260501', '20261013', '&interval=h').split(b'\n', 1)[1]))
def mm():
    parts = []
    for a, b in [('19120101', '19611231'), ('19620101', '20111231'), ('20120101', '20261013')]:
        t = coops('monthly_mean', a, b); parts.append(t if not parts else t.split(b'\n', 1)[1])
    save('portland_monthly.csv', b'\n'.join(p.strip() for p in parts))
tryit('portland_monthly', mm)

# NDBC 44007 (Portland buoy): yearly standard met files + 2026 months + last 45 days
NB = 'https://www.ndbc.noaa.gov/view_text_file.php?'
def ndbc():
    for y in range(1990, 2026):
        try: save(f'44007_{y}.txt', get(NB + f'filename=44007h{y}.txt.gz&dir=data/historical/stdmet/'))
        except Exception as e: log.append(f'FAIL 44007 {y}: {e}')
    for m, mon in enumerate(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep'], 1):
        try: save(f'44007_2026_{m:02d}.txt', get(NB + f'filename=44007{m}2026.txt.gz&dir=data/stdmet/{mon}/'))
        except Exception as e: log.append(f'FAIL 44007 2026-{m}: {e}')
    save('44007_recent.txt', get('https://www.ndbc.noaa.gov/data/realtime2/44007.txt'))
tryit('ndbc', ndbc)

# USGS Saco River at Cornish, daily mean flow, full record
tryit('usgs', lambda: save('saco_daily.rdb', get('https://waterservices.usgs.gov/nwis/dv/?format=rdb&sites=01066000&parameterCd=00060&startDT=1916-01-01&endDT=2026-10-13')))

# NOAA GHCN-Daily, Portland International Jetport: daily max/min temperature and precipitation
tryit('ghcn', lambda: save('portland_ghcn.csv', get('https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=USW00014764&dataTypes=TMAX,TMIN,PRCP&startDate=1991-01-01&endDate=2026-10-12&units=metric&format=csv')))

open(os.path.join(OUT, 'LOG.txt'), 'w').write('\n'.join(log)); print('\n'.join(log))
