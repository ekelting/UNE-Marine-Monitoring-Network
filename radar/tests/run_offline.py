"""End-to-end offline test: fake CUMULUS → fetch.py → build.py → site/ (in a temp copy of the repo)."""
import os
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd

# Run from the network repo:  python radar/tests/run_offline.py [workdir]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
work = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp()
shutil.rmtree(work, ignore_errors=True)
os.makedirs(work)
shutil.copy(os.path.join(REPO, 'buoys', 'ram-island-radar', 'site.json'), os.path.join(work, 'site.json'))
os.environ['BUOY_DIR'] = work
sys.path.insert(0, os.path.join(REPO, 'radar'))
sys.path.insert(0, os.path.join(REPO, 'radar', 'tests'))
import core  # noqa: E402
import fake_cumulus as fk  # noqa: E402

core.Http = fk.FakeHttp
# fake buoy CSV (local file instead of the live Camp Ellis site)
rows = []
for i in range(fk.N_COLLECTS + 4):
    t = (pd.Timestamp(str(fk.T0), tz='UTC') + pd.Timedelta(hours=i)).tz_convert('America/New_York').tz_localize(None)
    w = fk.wind(i)
    rows.append({'time_local': t.strftime('%Y-%m-%d %H:00:00'), 'hs': 0.2 + 0.08 * w, 'tp': 8.0, 'tm': 5, 'te': 6,
                 'power_kw_m': 1, 'wspd': w, 'dm': 110, 'pres': 1010})
bcsv = os.path.join(work, 'buoy.csv')
pd.DataFrame(rows).to_csv(bcsv, index=False)
core.CFG['buoy']['hourly_csv'] = bcsv
core.CFG['max_new_per_run'] = 40
core.CFG['full_burst_newest'] = 2

import fetch  # noqa: E402
import build  # noqa: E402

pd.Timestamp.now  # noqa: B018
_real_now = pd.Timestamp.now
pd.Timestamp.now = staticmethod(lambda tz=None: pd.Timestamp('2026-10-12T14:30:00', tz='UTC').tz_convert(tz) if tz else _real_now())

sys.argv = ['fetch.py', '--max-minutes', '30']
fetch.main()
sys.argv = ['fetch.py']
fetch.main()      # second run: nothing new
sys.argv = ['build.py', '--out', os.path.join(work, 'site')]
# tides offline: stub
build.load_tides = lambda offline: ([{'t': (pd.Timestamp(str(fk.T0), tz='UTC') + pd.Timedelta(hours=h)).isoformat().replace('+00:00', 'Z'),
                                      'v': round(4.5 + 4.3 * np.sin(h / 12.42 * 2 * np.pi), 2)} for h in range(-24, 60)], [])
build.main()
print('WORK', work)
