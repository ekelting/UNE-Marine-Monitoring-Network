"""
compute.py — runs every analysis on the Analysis page and returns one dict of results + chart data.
Inputs: the built station pages' hourly CSVs (site/<slug>/data), raw station files in buoys/, and the
outside records in analysis/ext/ (see fetch_ext.py). Each analysis is independent: if one fails, its
card is left out and the rest still build.
"""
import glob
import json
import os
import traceback

import numpy as np
import pandas as pd
from scipy import optimize, signal, stats
from scipy.integrate import solve_ivp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXT = os.path.join(HERE, 'ext')
TZ = 'America/New_York'
g = 9.81
SONDES = {'wood-island': 'Wood Island', 'jordan-point': 'Jordan Point', 'ferry-beach': 'Ferry Beach', 'goose-rocks-beach': 'Goose Rocks Beach'}
SHORE_NORMAL = 65           # degrees: direction a wave comes from when it hits the beach straight on. The shore from the Camp Ellis
                            # jetty to Ferry Beach runs north-northwest, so it faces east-northeast (estimated from map coordinates).
DECLINATION = -14.6         # magnetic declination at Saco Bay (degrees, west negative)


class Ctx:
    def __init__(self, site):
        self.site = site

    def H(self, slug, f='hourly.csv'):
        p = os.path.join(self.site, slug, 'data', f)
        return pd.read_csv(p, parse_dates=['time_local'], index_col='time_local')

    @staticmethod
    def ext(name):
        return pd.read_csv(os.path.join(EXT, name))


def utc_to_local(idx):
    idx = pd.DatetimeIndex(pd.to_datetime(idx, utc=True))
    if idx.tz is None:
        idx = idx.tz_localize('UTC')
    return idx.tz_convert(TZ).tz_localize(None)


def lst(s, nd=3):
    return [None if (v is None or (isinstance(v, float) and not np.isfinite(v))) else round(float(v), nd) for v in s]


def ar1_infl(res):
    res = np.asarray(res); r = np.corrcoef(res[:-1], res[1:])[0, 1]
    return r, float(np.sqrt((1 + r) / (1 - r))) if r < 0.999 else 30.0


def kvec(T, h):
    w = 2 * np.pi / T; k = w ** 2 / g
    for _ in range(60):
        k = w ** 2 / (g * np.tanh(k * h))
    return k


# =========================================================================== outside records
def a_msl(C):
    m = C.ext('portland_monthly.csv')
    yr = m.groupby('Year').MSL.agg(['mean', 'count']); yr = yr[yr['count'] >= 11]['mean']
    x = yr.index.values.astype(float); r = stats.linregress(x, yr.values)
    _, infl = ar1_infl(yr.values - (r.intercept + r.slope * x))
    r30 = stats.linregress(x[-30:], yr.values[-30:])
    return dict(yr=yr.index.tolist(), v=lst(yr.values, 4), slope=r.slope, inter=r.intercept, ci=1.96 * r.stderr * infl,
                slope30=r30.slope, ci30=1.96 * r30.stderr, first=int(x[0]), last=int(x[-1]), rise=r.slope * (x[-1] - x[0]))


def a_amax(C, msl):
    m = C.ext('portland_monthly.csv').dropna(subset=['Highest'])
    a = m.groupby('Year').Highest.agg(['max', 'count']); a = a[a['count'] >= 11]['max']
    now = pd.Timestamp.now().year
    adj = a + msl['slope'] * (now - a.index.values)
    c, loc, sc = stats.genextreme.fit(adj.values)
    rl = {str(T): float(stats.genextreme.ppf(1 - 1 / T, c, loc, sc)) for T in [2, 10, 50, 100]}
    rng = np.random.default_rng(0); bs = []
    for _ in range(300):
        s = rng.choice(adj.values, len(adj)); cc, ll, ss = stats.genextreme.fit(s); bs.append(stats.genextreme.ppf(0.99, cc, ll, ss))
    mhhw = float(m.MHHW.dropna().iloc[-228:].mean())
    top = a.sort_values(ascending=False).head(5)
    return dict(yr=a.index.tolist(), v=lst(adj.values), raw=lst(a.values), rl=rl, ci100=lst(np.percentile(bs, [5, 95])),
                top=[[int(y), float(v)] for y, v in top.items()], mhhw=mhhw, year=now)


def storms_ce(C):
    st = pd.read_csv(os.path.join(C.site, 'camp-ellis', 'data', 'storms.csv'), parse_dates=['start', 'end', 'peak_time'])
    return st


def a_surge(C):
    h = C.ext('portland_hourly.csv'); h.index = utc_to_local(h.time_utc)
    h = h[h.index >= h.index.max() - pd.Timedelta(days=365)]
    res = (h.obs_m - h.pred_m).dropna(); off = float(res.mean()); s = res - off
    sd = s.rolling(25, center=True, min_periods=18).mean().resample('3h').mean()
    st = storms_ce(C); st = st[st.end >= res.index.min()]
    ev = []
    for _, r in st.iterrows():
        seg = s[r.start - pd.Timedelta(hours=6):r.end + pd.Timedelta(hours=6)]
        if len(seg):
            ev.append([r.start.strftime('%b %d, %Y'), float(seg.max()), float(r.peak_hs)])
    ev.sort(key=lambda x: -x[1])
    obs = h.obs_m.dropna()
    return dict(t=sd.index.strftime('%Y-%m-%dT%H:%M').tolist(), v=lst(sd.values), off=off, max=float(s.max()),
                tmax=s.idxmax().strftime('%b %d, %Y'), top=ev[:4], storms=[[r.start.strftime('%Y-%m-%dT%H:%M'), r.end.strftime('%Y-%m-%dT%H:%M')] for _, r in st.iterrows()],
                hw=float(obs.max()), hw_t=obs.idxmax().strftime('%b %d, %Y'), hw_storm=bool(any((obs.idxmax() >= r.start - pd.Timedelta(hours=12)) and (obs.idxmax() <= r.end + pd.Timedelta(hours=12)) for _, r in st.iterrows())))


def doy_window_stats(series, base_years, half, smooth, funcs):
    base = series[(series.index.year >= base_years[0]) & (series.index.year <= base_years[1])].dropna()
    doy = base.index.dayofyear.values
    out = {k: [] for k in funcs}
    for d in range(1, 367):
        w = ((doy - d) % 366 <= half) | ((d - doy) % 366 <= half)
        v = base.values[w]
        for k, f in funcs.items():
            out[k].append(f(v) if len(v) else np.nan)
    return {k: pd.Series(v, index=range(1, 367)).rolling(smooth, center=True, min_periods=1).mean() if smooth else pd.Series(v, index=range(1, 367))
            for k, v in out.items()}


def a_sst(C):
    d = C.ext('ndbc44007_daily.csv'); d.index = pd.to_datetime(d.date); w = d.wtmp_c
    cl = doy_window_stats(w, (1991, 2020), 5, 31, {'clim': np.mean, 'p10': lambda v: np.percentile(v, 10), 'p90': lambda v: np.percentile(v, 90)})
    end = w.dropna().index.max(); cur = w[w.index > end - pd.Timedelta(days=365)]
    cd = cur.index.dayofyear
    an = cur.values - cl['clim'].loc[cd].values
    hot = cur.values > cl['p90'].loc[cd].values
    mhw = 0; k = 0
    for hv in hot:
        k = k + 1 if hv else 0
        if k == 5: mhw += 5
        elif k > 5: mhw += 1
    ma = pd.Series(an, index=cur.index).resample('ME').mean().dropna()
    ya = w.groupby(w.index.year).agg(['mean', 'count']); ya = ya[ya['count'] > 330]['mean']
    lr = stats.linregress(ya.index.values.astype(float), ya.values)
    ce = C.H('camp-ellis', 'sensors_hourly.csv').iloc[:, 0].resample('D').mean()
    ce = ce[ce.index > end - pd.Timedelta(days=365)]
    return dict(clim=lst(cl['clim']), p10=lst(cl['p10']), p90=lst(cl['p90']), t=cur.index.strftime('%Y-%m-%d').tolist(), v=lst(cur.values, 2),
                start=cur.index.min().strftime('%Y-%m-%d'), end=end.strftime('%Y-%m-%d'),
                ce_t=ce.index.strftime('%Y-%m-%d').tolist(), ce=lst(ce.values, 2), meanan=float(np.nanmean(an)), mhw=int(mhw),
                warm=[[k.strftime('%B'), float(v)] for k, v in ma.sort_values(ascending=False).head(2).items()],
                cold=[[k.strftime('%B'), float(v)] for k, v in ma.sort_values().head(2).items() if v < 0],
                yr=ya.index.tolist(), yv=lst(ya.values, 2), slope=lr.slope, p=lr.pvalue, nyears=len(ya))


def a_flow(C):
    q = C.ext('saco_daily.csv'); q.index = pd.to_datetime(q.date); q = q.q_cfs * 0.0283168
    end = q.index.max(); base = q[q.index < end - pd.Timedelta(days=365)]
    doy = base.index.dayofyear.values
    pct = {p: [] for p in [10, 50, 90]}
    for d in range(1, 367):
        w = ((doy - d) % 366 <= 3) | ((d - doy) % 366 <= 3)
        for p in pct:
            pct[p].append(float(np.percentile(base.values[w], p)))
    cur = q[q.index > end - pd.Timedelta(days=365)]
    rank = [float((base.values[base.index.dayofyear.values == dd] < v).mean() * 100) for dd, v in zip(cur.index.dayofyear, cur.values)]
    p50 = np.array(pct[50]); pctn = cur.values / p50[cur.index.dayofyear.values - 1] * 100
    last60 = pd.Series(pctn, index=cur.index)[cur.index > end - pd.Timedelta(days=60)].median()
    pk = pd.Series(pctn, index=cur.index).resample('ME').median()
    return dict(t=cur.index.strftime('%Y-%m-%d').tolist(), v=lst(cur.values, 2), pct=lst(pctn, 1), rank=lst(rank, 0), p50=lst(p50, 2),
                start=int(q.index.min().year), med_rank=float(np.median(rank)), n_low=int((np.array(rank) < 10).sum()), n=len(rank),
                last60=float(last60), wettest=[pk.idxmax().strftime('%B %Y'), float(pk.max())], end=end.strftime('%b %d, %Y'))


def a_air(C):
    gh = C.ext('portland_air.csv'); gh.index = pd.to_datetime(gh.date)
    tav = (gh.tmax + gh.tmin) / 2
    cl = doy_window_stats(tav, (1991, 2020), 7, 0, {'n': np.nanmean})['n']
    end = tav.dropna().index.max(); cur = tav[tav.index > end - pd.Timedelta(days=365)]
    an = pd.Series(cur.values - cl.loc[cur.index.dayofyear].values, index=cur.index).resample('ME').mean().dropna()
    ri = C.H('ram-island').air_temp_c.resample('D').mean(); ri = ri[ri.index > end - pd.Timedelta(days=365)]
    j = pd.concat([ri, tav], axis=1).dropna()
    return dict(norm=lst(cl, 2), t=cur.index.strftime('%Y-%m-%d').tolist(), v=lst(cur.values, 2), ri_t=ri.index.strftime('%Y-%m-%d').tolist(), ri=lst(ri.values, 2),
                cold=[k.strftime('%B %Y') for k in [an.idxmin()]][0], coldv=float(an.min()), warm=an.idxmax().strftime('%B %Y'), warmv=float(an.max()),
                r=float(j.corr().iloc[0, 1]), diff=float((j.iloc[:, 0] - j.iloc[:, 1]).mean()), start=cur.index.min().strftime('%Y-%m-%d'))


# =========================================================================== one station
CON = {'M2': 12.4206012, 'S2': 12.0, 'N2': 12.65834751, 'K1': 23.93447213, 'O1': 25.81933871, 'M4': 6.210300601, 'M6': 4.140200401}


def harm_fit(y):
    y = y.dropna(); t = (y.index - pd.Timestamp('2026-01-01')).total_seconds() / 3600
    X = [np.ones(len(t))]
    for P in CON.values():
        X += [np.cos(2 * np.pi / P * t), np.sin(2 * np.pi / P * t)]
    X = np.array(X).T; b, *_ = np.linalg.lstsq(X, y.values, rcond=None); fit = X @ b
    amp = {k: float(np.hypot(b[1 + 2 * i], b[2 + 2 * i])) for i, k in enumerate(CON)}
    r2 = 1 - ((y - fit) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return amp, float(r2), pd.Series(fit, index=y.index)


def a_marsh(C):
    y = C.H('biddeford-pool-marsh').water_level_m.dropna()
    y30 = y[y.index > y.index.max() - pd.Timedelta(days=30)]
    amp, r2, fit = harm_fit(y30)
    seg = y30[y30.index > y30.index.max() - pd.Timedelta(days=8)]
    fs = sorted(glob.glob(os.path.join(ROOT, 'buoys', 'biddeford-pool-marsh', 'data', 'obs', 'obs_*.csv')))
    raw = pd.concat([pd.read_csv(f, index_col=0) for f in fs]).marsh_water_level.dropna()
    raw.index = utc_to_local(raw.index); raw = raw[~raw.index.duplicated()].sort_index().resample('5min').mean().interpolate(limit=3)
    sm = raw.rolling(7, center=True).mean()
    hi, _ = signal.find_peaks(sm.values, distance=100, prominence=0.3); lo, _ = signal.find_peaks(-sm.values, distance=100, prominence=0.3)
    ev = sorted([(i, 'H') for i in hi] + [(i, 'L') for i in lo]); rise, fall = [], []
    for (i, a), (j, b) in zip(ev, ev[1:]):
        if a != b and (j - i) * 5 / 60 < 10:
            (rise if a == 'L' else fall).append((j - i) * 5 / 60)
    return dict(t=seg.index.strftime('%Y-%m-%dT%H:%M').tolist(), obs=lst(seg.values), fit=lst(fit.reindex(seg.index).values), amp=amp, r2=r2,
                rise=float(np.median(rise)), fall=float(np.median(fall)), ntides=len(rise))


def a_tideclock(C):
    jp = C.H('jordan-point').sal_psu
    jp = jp[jp.index > jp.index.max() - pd.Timedelta(days=31)]
    hm = jp.groupby([jp.index.date, jp.index.hour]).mean().unstack().reindex(columns=range(24))
    return dict(dates=[str(d) for d in hm.index], z=[lst(r, 2) for r in hm.values], lo=float(jp.quantile(.02)), hi=float(jp.quantile(.98)))


def a_strat(C):
    ce = C.H('camp-ellis', 'sensors_hourly.csv')
    D = pd.concat([ce.iloc[:, 0].resample('D').mean().rename('t1'), ce.iloc[:, 1].resample('D').mean().rename('t2'), ce.iloc[:, 2].resample('D').mean().rename('t3')], axis=1)
    m = (D.t1 - D.t3).resample('ME').mean().dropna()
    mixed = m[m.abs() < 0.3]
    return dict(t=D.index.strftime('%Y-%m-%d').tolist(), t1=lst(D.t1, 2), t2=lst(D.t2, 2), t3=lst(D.t3, 2),
                maxm=m.idxmax().strftime('%B %Y'), maxd=float(m.max()), mixed=[k.strftime('%b') for k in mixed.index][:6])


def a_soil(C):
    w = C.H('une-363-woods')
    yr = w.soil_t_4.dropna().index.max().year
    if w.soil_t_4[f'{yr}-06-01':f'{yr}-09-15'].count() < 24 * 40:
        yr -= 1
    w = w[f'{yr}-06-01':f'{yr}-09-15']
    t = (w.index - pd.Timestamp('2026-01-01')).total_seconds() / 3600; om = 2 * np.pi / 24
    res = []
    for d in [4, 10, 20, 30, 40, 45]:
        y = w[f'soil_t_{d}']; yy = y - y.rolling(24, center=True).mean(); m = yy.notna().values
        X = np.c_[np.cos(om * t[m]), np.sin(om * t[m])]; b, *_ = np.linalg.lstsq(X, yy[m].values, rcond=None)
        res.append((d, float(np.hypot(*b)), float(np.degrees(np.arctan2(b[1], b[0])) / 360 * 24 % 24)))
    z = np.array([r[0] for r in res[:4]]) / 100; A = np.array([r[1] for r in res[:4]]); P = np.array([r[2] for r in res[:4]])
    s1 = stats.linregress(z, np.log(A)).slope; damp_a = -1 / s1
    lag_h_per_m = np.polyfit(z, np.unwrap(P * 2 * np.pi / 24) * 24 / (2 * np.pi), 1)[0]
    damp_p = 1 / (lag_h_per_m * 2 * np.pi / 24)
    kappa = damp_a ** 2 * (2 * np.pi / 86400) / 2
    wk = w[f'{yr}-07-15':f'{yr}-07-21']
    dev = {}
    for dd in [4, 10, 20, 30, 40, 45]:
        col = w[f'soil_t_{dd}']; dv = (col - col.rolling(24, center=True, min_periods=12).mean())[f'{yr}-07-15':f'{yr}-07-21']
        dev[dd] = lst(dv, 3)
    return dict(depth=[r[0] for r in res], amp=[r[1] for r in res], peak=[r[2] for r in res], damp_a=damp_a, damp_p=damp_p, kappa=kappa,
                lag10=lag_h_per_m / 10, year=yr, dev=dict(depths=[4, 10, 20, 30, 40, 45], z=[dev[k] for k in [4, 10, 20, 30, 40, 45]]), wk=dict(t=wk.index.strftime('%Y-%m-%dT%H:%M').tolist(), **{f'd{d}': lst(wk[f'soil_t_{d}'], 2) for d in [4, 10, 20, 45]}))


def a_headlines(C, surge):
    out = {}
    ce = C.H('camp-ellis', 'sensors_hourly.csv').iloc[:, 0].dropna()
    ce = ce[ce.index > ce.index.max() - pd.Timedelta(days=365)]
    dm = ce.resample('D').mean()
    sw = dm[dm >= 18.3]
    out['swim'] = int(len(sw)); out['swim_first'] = sw.index.min().strftime('%b %d') if len(sw) else ''; out['swim_last'] = sw.index.max().strftime('%b %d') if len(sw) else ''
    out['lob'] = int((ce > 20).sum())
    out['lob_month'] = ce[ce > 20].groupby(ce[ce > 20].index.month).size().idxmax() if (ce > 20).any() else None
    a = C.H('une-363-woods').air_temp_c.resample('D').agg(['min', 'max']).dropna()
    yr = a.index.max().year; aa = a[f'{yr}-04-01':]
    out['gdd'] = float(((aa['min'] + aa['max']) / 2 - 10).clip(lower=0).sum()); out['gdd_year'] = yr
    gp = C.H('great-pond').do_mgl.dropna(); gm = gp.groupby(gp.index.to_period('M')).apply(lambda x: (x < 2).mean() * 100)
    out['gp_low'] = float(gm.max()); out['gp_month'] = gm.idxmax().strftime('%B %Y'); out['gp_max'] = float(gp.max())
    hs = C.H('camp-ellis').hs.dropna(); hs = hs[hs.index > hs.index.max() - pd.Timedelta(days=365)]
    out['wave'] = float(hs.max()); out['wave_t'] = hs.idxmax().strftime('%b %d, %Y')
    out['hw'] = surge['hw']; out['hw_t'] = surge['hw_t']; out['hw_storm'] = surge['hw_storm']
    return out


def a_wrose(C):
    w = C.H('ram-island')[['wind_ms', 'wind_dir']].dropna()
    b = ((w.wind_dir + 11.25) % 360 // 22.5).astype(int)
    cls = pd.cut(w.wind_ms, [0, 3, 6, 9, 99], labels=['0–3', '3–6', '6–9', '9+'], include_lowest=True)
    rose = pd.crosstab(b, cls).reindex(range(16), fill_value=0) / len(w) * 100
    tot = rose.sum(axis=1)
    return dict(rose={c: lst(rose[c], 2) for c in rose.columns}, top=[int(i) for i in tot.sort_values(ascending=False).index[:3]],
                east=float(tot.loc[[2, 3, 4, 5]].sum()), start=w.index.min().strftime('%b %Y'))


def a_chl(C):
    out = {}
    for s, n in [('wood-island', 'Wood Island'), ('jordan-point', 'Jordan Point')]:
        d = C.H(s)[['chl_ugl', 'sal_psu']].dropna()
        d = d[d.index > d.index.max() - pd.Timedelta(days=60)]
        gq = d.chl_ugl.groupby(d.index.hour)
        night = d[(d.index.hour >= 22) | (d.index.hour <= 4)]
        nk = night.chl_ugl.groupby((night.index - pd.Timedelta(hours=6)).date).median()
        day = d[(d.index.hour >= 10) & (d.index.hour <= 14)].chl_ugl.median()
        cls = pd.cut(nk, [0, 5, 20, 60, 1e9], labels=['low', 'medium', 'high', 'very high']).value_counts().reindex(['low', 'medium', 'high', 'very high']).fillna(0)
        bins = night.groupby(pd.cut(night.sal_psu, [0, 15, 20, 25, 30, 40])).chl_ugl.median()
        out[n] = dict(h_med=lst(gq.median(), 2), h_q1=lst(gq.quantile(.25), 2), h_q3=lst(gq.quantile(.75), 2), ratio=float(day / night.chl_ugl.median()),
                      night=dict(t=[str(x) for x in nk.index], v=lst(nk.values, 2)), cls=[int(x) for x in cls.values], nn=int(len(nk)),
                      sc=dict(s=lst(night.sal_psu, 2), c=lst(night.chl_ugl, 2)), r=float(night[['chl_ugl', 'sal_psu']].corr().iloc[0, 1]),
                      bins=[None if pd.isna(v) else float(v) for v in bins.values], start=d.index.min().strftime('%b %d'), end=d.index.max().strftime('%b %d'))
    return out


# =========================================================================== compare
def a_anova(C):
    out = {}
    for v in ['sal_psu', 'temp_c', 'do_mgl']:
        D = pd.DataFrame({n: C.H(s)[v].resample('D').mean() for s, n in SONDES.items()}).dropna().iloc[1:-1]
        D = D[D.index > D.index.max() - pd.Timedelta(days=60)]
        groups = [D[c].values for c in D]
        F, p = stats.f_oneway(*groups); K, pk = stats.kruskal(*groups); Fr, pf = stats.friedmanchisquare(*groups)
        allv = np.concatenate(groups); eta = sum(len(gg) * (gg.mean() - allv.mean()) ** 2 for gg in groups) / ((allv - allv.mean()) ** 2).sum()
        hourly = [C.H(s)[v].dropna() for s in SONDES]; hourly = [h[h.index >= D.index.min()].values for h in hourly]
        pn = stats.f_oneway(*hourly).pvalue
        pairs = []
        names = list(D.columns)
        for i in range(4):
            for j in range(i + 1, 4):
                dd = D[names[i]] - D[names[j]]; r1 = dd.autocorr(1) if len(dd) > 3 else 0; r1 = 0 if not np.isfinite(r1) else max(r1, 0)
                neff = max(len(dd) * (1 - r1) / (1 + r1), 2); t = dd.mean() / (dd.std() / np.sqrt(neff)); pp = 2 * stats.t.sf(abs(t), neff - 1)
                hw = float(stats.t.ppf(1 - 0.05 / 12, neff - 1) * dd.std() / np.sqrt(neff))
                pairs.append([names[i], names[j], float(dd.mean()), float(neff), float(pp), hw])
        # Holm correction: six pairwise tests per measurement
        order = sorted(range(len(pairs)), key=lambda i: pairs[i][4]); m = len(pairs); run_max = 0
        for rank, i in enumerate(order):
            run_max = max(run_max, min(1.0, (m - rank) * pairs[i][4])); pairs[i][4] = run_max
        out[v] = dict(n=len(D), F=F, p=p, K=K, pk=pk, Fr=Fr, pf=pf, eta2=eta, pn=pn, pairs=pairs, daily={c: lst(D[c], 3) for c in D},
                      means={c: float(D[c].mean()) for c in D}, start=D.index.min().strftime('%b %d'), end=D.index.max().strftime('%b %d, %Y'))
    return out


def a_rain(C):
    jp = C.H('jordan-point').sal_psu
    end = jp.index.max(); start = max(jp.index.min(), end - pd.Timedelta(days=45))
    rain = C.H('ram-island').rain_mm.resample('D').sum()[start.normalize():]
    q = C.ext('saco_daily.csv'); q.index = pd.to_datetime(q.date); q = (q.q_cfs * 0.0283168)[start.normalize():]
    jd = jp.resample('D').mean()[start.normalize():]
    tide = tide_jp()
    tr = (tide.rolling(25, center=True).max() - tide.rolling(25, center=True).min()).resample('D').mean()
    j = pd.concat([jd.rename('S'), q.rename('Q'), tr.rename('TR'), rain.rolling(3).sum().rename('R3')], axis=1).dropna()
    wk = rain.rolling(7).sum(); wend = wk.idxmax(); wstart = wend - pd.Timedelta(days=6)
    before = jd[:wstart].tail(3).mean(); low = jd[wstart:wend + pd.Timedelta(days=3)]
    return dict(t=[str(d.date()) for d in rain.index], rain=lst(rain.values, 1), qt=[str(d.date()) for d in q.index], q=lst(q.values, 2),
                st=[str(d.date()) for d in jd.index], s=lst(jd.values, 2), wet=float(wk.max()), wet_start=wstart.strftime('%b %d'), wet_end=wend.strftime('%b %d'),
                before=float(before), low=float(low.min()), low_t=low.idxmin().strftime('%b %d'),
                r_q=float(j[['S', 'Q']].corr().iloc[0, 1]), r_tr=float(j[['S', 'TR']].corr().iloc[0, 1]), qrise=float(q[wstart:wend + pd.Timedelta(days=3)].max() / q[:wstart].tail(3).mean()))


def tide_jp():
    fs = sorted(glob.glob(os.path.join(ROOT, 'buoys', 'jordan-point', 'data', 'tide', 'tide_*.csv')))
    t = pd.concat([pd.read_csv(f, index_col=0) for f in fs]).water_level_m
    t.index = utc_to_local(t.index)
    return t[~t.index.duplicated()].sort_index()


def a_radar(C):
    r = pd.read_csv(os.path.join(ROOT, 'buoys', 'ram-island-radar', 'data', 'collects.csv'))
    r = r[r.status == 'ok']; r.index = utc_to_local(r.time_utc)
    rh = r[['sparkle_ring_pct', 'n_tracks']].resample('h').mean()
    j = pd.concat([rh, C.H('ram-island').wind_ms, C.H('camp-ellis').wspd], axis=1)
    jj = j[['sparkle_ring_pct', 'wind_ms']].dropna()
    jw = j[['sparkle_ring_pct', 'wspd']].dropna()
    t = r.n_tracks.dropna(); we = t.groupby(t.index.dayofweek >= 5).mean()
    return dict(n=len(jj), r=float(jj.corr().iloc[0, 1]), rs=float(stats.spearmanr(jj.iloc[:, 0], jj.iloc[:, 1])[0]), rw=float(jw.corr().iloc[0, 1]),
                x=lst(jj.wind_ms, 2), y=lst(jj.sparkle_ring_pct, 2), weekend=float(we.get(True, np.nan)), weekday=float(we.get(False, np.nan)))


# =========================================================================== physics
def waves_ce(C):
    d = C.H('camp-ellis')[['hs', 'tp', 'dm']].dropna()
    return d[d.tp > 2]


def drift(d, normal, h1=12.0, gam=0.78, s=2.65, n=0.4, K=0.39, mb=0.02, D50=0.0002):
    Hs, T, Dm = d.hs.values, d.tp.values, d.dm.values
    def ccg(T, h):
        k = kvec(T, h); c = 2 * np.pi / T / k; return c, 0.5 * (1 + 2 * k * h / np.sinh(2 * k * h)) * c
    c1, cg1 = ccg(T, np.full(len(T), h1))
    a1 = ((Dm - normal + 180) % 360) - 180; ok = np.abs(a1) < 85
    sa = np.sin(np.radians(a1)) / c1
    Hb = np.zeros(len(T)); ab = np.zeros(len(T)); done = ~ok
    for hb in np.arange(h1, 0.2, -0.05):
        c, cg = ccg(T, np.full(len(T), hb)); a = np.degrees(np.arcsin(np.clip(sa * c, -1, 1)))
        H = Hs * np.sqrt(cg1 / cg) * np.sqrt(np.abs(np.cos(np.radians(a1))) / np.cos(np.radians(a)))
        hit = (~done) & (H >= gam * hb); Hb[hit] = H[hit]; ab[hit] = a[hit]; done |= hit
        if done.all():
            break
    qc = -K * np.sqrt(g) * Hb ** 2.5 * np.sin(np.radians(2 * ab)) / (16 * np.sqrt(gam) * (s - 1) * (1 - n)) * 3600
    qk = -2.27 * Hb ** 2 * T ** 1.5 * mb ** 0.75 * D50 ** -0.25 * np.sign(ab) * np.abs(np.sin(np.radians(2 * ab))) ** 0.6 / ((s - 1) * 1000 * (1 - n)) * 3600
    return pd.Series(qc, index=d.index), pd.Series(qk, index=d.index)


def a_drift(C):
    """Potential longshore transport at Camp Ellis. Internally + = toward the north; results are reported in the net direction."""
    d = waves_ce(C); years = (d.index.max() - d.index.min()).days / 365.25
    sens = []
    for nm in range(50, 111, 5):
        qc, qk = drift(d, nm); sens.append([nm, float(-qc.sum() / years), float(-qk.sum() / years)])     # + = north
        if nm == SHORE_NORMAL:
            QC, QK = -qc, -qk
    north = QK.sum() > 0
    sgn = 1 if north else -1
    DK, DC = QK * sgn, QC * sgn                       # + = the net direction
    st = storms_ce(C)
    inn = pd.Series(False, index=DK.index); rows = []
    for _, r in st.iterrows():
        m = (DK.index >= r.start) & (DK.index <= r.end); inn |= m
        rows.append([r.start.strftime('%b %d, %Y'), float(DK[m].sum() / 1000), float(r.peak_hs)])
    rows.sort(key=lambda x: -x[1])
    E = d.hs ** 2 * d.tp; b = ((d.dm + 11.25) % 360 // 22.5).astype(int)
    erose = (E.groupby(b).sum() / E.sum() * 100).reindex(range(16), fill_value=0)
    rel = ((d.dm - SHORE_NORMAL + 540) % 360) - 180          # > 0: waves from south of straight-on -> push north
    north_share = float(E[(rel > 0) & (rel < 90)].sum() / E[(rel.abs() < 90)].sum() * 100)
    top2 = erose.sort_values(ascending=False).index[:2]
    mw = DK.clip(lower=0).resample('ME').sum() / 1000; ma = DK.clip(upper=0).resample('ME').sum() / 1000
    cK = DK.cumsum().resample('6h').last().ffill(); cC = DC.cumsum().resample('6h').last().ffill()
    tot = float(DK.sum() / 1000)
    summer = float(mw[mw.index.month.isin([6, 7, 8])].sum()); feb = float(mw[mw.index.month == 2].sum()) if (mw.index.month == 2).any() else np.nan
    flip = None
    for (a1, _, k1), (a2, _, k2) in zip(sens, sens[1:]):
        if k1 * k2 < 0:
            flip = a1 + (a2 - a1) * k1 / (k1 - k2)
    mean_dir = float(np.degrees(np.arctan2((E * np.sin(np.radians(d.dm))).sum(), (E * np.cos(np.radians(d.dm))).sum())) % 360)
    return dict(sens=sens, erose=lst(erose, 2), net_dir='north' if north else 'south', other_dir='south' if north else 'north',
                with_share=north_share if north else 100 - north_share, top_dirs=[int(i) for i in top2], flip=flip, mean_dir=mean_dir,
                cum=dict(t=cK.index.strftime('%Y-%m-%dT%H:%M').tolist(), k=lst(cK / 1000, 2), c=lst(cC / 1000, 2)),
                storms=[[r.start.strftime('%Y-%m-%dT%H:%M'), r.end.strftime('%Y-%m-%dT%H:%M')] for _, r in st.iterrows()],
                ranking=rows, total=tot, nonstorm=float(tot - sum(r[1] for r in rows)), storm_share_k=float(DK[inn].abs().sum() / DK.abs().sum() * 100),
                storm_share_c=float(DC[inn].abs().sum() / DC.abs().sum() * 100), storm_hours=float(inn.mean() * 100), nstorms=len(st),
                month=dict(m=[x.strftime('%Y-%m') for x in mw.index], w=lst(mw, 2), a=lst(ma, 3)), busiest=mw.idxmax().strftime('%B %Y'),
                against_frac=float(-DK.clip(upper=0).sum() / DK.abs().sum() * 100), summer=summer, feb=feb, years=years, start=d.index.min().strftime('%b %Y'),
                k_here=float(DK.sum() / years), c_here=float(DC.sum() / years))


def a_shields(C, D50=0.0002, s=2.65, nu=1.36e-6):
    d = waves_ce(C); Hs, T = d.hs.values, d.tp.values; h = 11.3 + 1.4
    k = kvec(T, np.full(len(T), h)); ub = np.pi * Hs / (T * np.sinh(k * h)); A = ub * T / (2 * np.pi)
    Ds = D50 * (g * (s - 1) / nu ** 2) ** (1 / 3); thcr = 0.3 / (1 + 1.2 * Ds) + 0.055 * (1 - np.exp(-0.02 * Ds))
    fw = 1.39 * (A / (2.5 * D50 / 30)) ** -0.52; th = pd.Series(0.5 * fw * ub ** 2 / ((s - 1) * g * D50), index=d.index)
    dm = th.resample('D').max(); mo = (th > thcr).resample('ME').mean() * 100
    win = mo[mo.index.month.isin([12, 1, 2, 3])].mean(); summ = mo[mo.index.month.isin([6, 7, 8])].mean()
    return dict(month=dict(m=[x.strftime('%Y-%m') for x in mo.index], pct=lst(mo, 1)), t=dm.index.strftime('%Y-%m-%d').tolist(), v=lst(dm, 4), cr=thcr, move=float((th > thcr).mean() * 100), sheet=float((th > 0.8).mean() * 100),
                winter=float(win), summer=float(summ), top=[k.strftime('%B') for k in mo.sort_values(ascending=False).index[:2]])


def a_currents(C):
    ce = C.H('camp-ellis', 'sensors_hourly.csv'); sp = ce.iloc[:, 5]; dr = (ce.iloc[:, 6] + DECLINATION) % 360
    u = sp * np.sin(np.radians(dr)); v = sp * np.cos(np.radians(dr)); ok = u.notna() & v.notna(); u, v = u[ok], v[ok]
    x = (u * 3600).cumsum() / 1000; y = (v * 3600).cumsum() / 1000
    xs = x.resample('D').last(); ys = y.resample('D').last()
    b = ((dr.dropna() + 11.25) % 360 // 22.5).astype(int)
    Cv = np.cov(np.c_[u, v].T); w, V = np.linalg.eigh(Cv); axis = float(np.degrees(np.arctan2(V[0, 1], V[1, 1])) % 180)
    ri = C.H('ram-island'); wu = (-ri.wind_ms * np.sin(np.radians(ri.wind_dir))).resample('D').mean(); wv = (-ri.wind_ms * np.cos(np.radians(ri.wind_dir))).resample('D').mean()
    a = np.radians(20); cal = u.resample('D').mean() * np.sin(a) + v.resample('D').mean() * np.cos(a); wal = wu * np.sin(a) + wv * np.cos(a)
    j = pd.concat([cal, wal], axis=1).dropna()
    return dict(t=xs.index.strftime('%Y-%m-%d').tolist(), x=lst(xs, 2), y=lst(ys, 2), rose=np.bincount(b, minlength=16).tolist(),
                speed=float(np.hypot(u.mean(), v.mean())), dir=float(np.degrees(np.arctan2(u.mean(), v.mean())) % 360), mean_speed=float(sp.mean()), axis=axis,
                km=float(np.hypot(xs.iloc[-1], ys.iloc[-1])), days=len(xs), cw=dict(t=j.index.strftime('%Y-%m-%d').tolist(), c=lst(j.iloc[:, 0] * 100, 2), w=lst(j.iloc[:, 1], 2)),
                r_wind=float(j.corr().iloc[0, 1]))


def godin(x):
    return x.rolling(24, center=True).mean().rolling(24, center=True).mean().rolling(25, center=True).mean()


def a_ode(C):
    jp = C.H('jordan-point').sal_psu.interpolate(limit=3)
    jp = jp[jp.index > jp.index.max() - pd.Timedelta(days=120)]
    f = godin(jp); Sd = f.resample('6h').mean().dropna()
    q = C.ext('saco_daily.csv'); q.index = pd.to_datetime(q.date); Q = q.q_cfs * 0.0283168
    tide = tide_jp(); TR = tide.rolling(25, center=True).max() - tide.rolling(25, center=True).min()
    tt = (Sd.index - Sd.index[0]).total_seconds() / 86400
    Qh = Q.resample('6h').interpolate().reindex(Sd.index, method='nearest'); TRh = TR.resample('6h').mean().reindex(Sd.index, method='nearest').interpolate()
    Q0, TR0 = float(Qh.mean()), float(TRh.mean())
    qf = lambda x: np.interp(x, tt, Qh.values); trf = lambda x: np.interp(x, tt, TRh.values)  # noqa: E731
    def sim(p):
        tau, Seq, bq, bt = p
        return solve_ivp(lambda t, S: (Seq + bq * (qf(t) - Q0) + bt * (trf(t) - TR0) - S) / tau, (tt[0], tt[-1]), [Sd.iloc[0]], t_eval=tt, max_step=0.1).y[0]
    r = optimize.least_squares(lambda p: sim(p) - Sd.values, [1, float(Sd.mean()), -0.5, 4], bounds=([0.05, 1, -20, -30], [30, 35, 20, 30]))
    res = r.fun; r1, infl = ar1_infl(res)
    cov = np.linalg.inv(r.jac.T @ r.jac) * (res ** 2).sum() / (len(res) - 4); se = np.sqrt(np.diag(cov)) * infl
    R2 = 1 - (res ** 2).sum() / ((Sd - Sd.mean()) ** 2).sum()
    jr = jp.resample('h').mean()
    rng = jp.rolling(13, center=True).max() - jp.rolling(13, center=True).min()
    jj = pd.concat([TR.resample('D').mean().rename('tr'), rng.resample('D').mean().rename('sr')], axis=1).dropna()
    lr = stats.linregress(jj.tr, jj.sr)
    qd = Q[Sd.index.min().normalize():]
    return dict(t=Sd.index.strftime('%Y-%m-%dT%H:%M').tolist(), obs=lst(Sd, 2), mod=lst(sim(r.x), 2), tr=lst(TRh, 3),
                rawt=jr.index.strftime('%Y-%m-%dT%H:%M').tolist(), raw=lst(jr, 2), qd=dict(t=qd.index.strftime('%Y-%m-%d').tolist(), v=lst(qd, 2)),
                par=dict(tau=r.x[0], Seq=r.x[1], bq=r.x[2], bt=r.x[3], se=se.tolist(), R2=float(R2), rmse=float(np.sqrt((res ** 2).mean())), Q0=Q0, TR0=TR0, r1=float(r1), infl=float(infl)),
                corr_qtr=float(pd.concat([Qh, TRh], axis=1).corr().iloc[0, 1]), days=int(round(tt[-1])),
                sc=dict(tr=lst(jj.tr, 3), sr=lst(jj.sr, 2), d=jj.index.strftime('%b %d').tolist()), slope=lr.slope, r_sc=lr.rvalue, med_swing=float(rng.median()),
                S_mean=float(jp.mean()), Q30=float(Q[Q.index > Q.index.max() - pd.Timedelta(days=30)].mean()),
                S_ocean=float(C.H('wood-island').sal_psu.dropna().iloc[-24 * 30:].mean()))


def a_coast(C):
    """Saco Bay coastline (OpenStreetMap) plus each water-quality buoy's recent average salinity, for the map."""
    co = json.load(open(os.path.join(EXT, 'saco_coast.json')))
    pos = {'wood-island': ((43.455593, -70.317699), 'bottom center'), 'jordan-point': ((43.460893, -70.389691), 'bottom left'),
           'ferry-beach': ((43.497213, -70.379113), 'top right'), 'goose-rocks-beach': ((43.396733, -70.402301), 'bottom right')}
    buoys = []
    for slug, name in SONDES.items():
        h = C.H(slug); end = h.sal_psu.dropna().index.max()
        m30 = lambda col: (lambda x: float(x[x.index > end - pd.Timedelta(days=30)].mean()) if len(x) else None)(h[col].dropna()) if col in h else None
        (lat, lon), tp = pos[slug]
        buoys.append(dict(name=name, lat=lat, lon=lon, sal=m30('sal_psu'), tmp=m30('temp_c'), do=m30('do_mgl'), pos=tp))
    return dict(lines=co['lines'], buoys=buoys, source=co['source'])


def a_events(C):
    return json.load(open(os.path.join(HERE, 'events.json')))


def a_flood(C):
    """Days per year when Portland's highest water reached Portland Pier's flooding level (12 ft MLLW)."""
    d = pd.read_csv(os.path.join(EXT, 'portland_daymax.csv'), parse_dates=['date']).set_index('date').max_m
    thr = 12.0 * 0.3048
    g = d.groupby(d.index.year); n = g.count(); days = g.apply(lambda x: int((x >= thr).sum()))
    ok = n >= 330
    yrs = days[ok]
    dec = yrs.groupby((yrs.index // 10) * 10).mean()
    first = yrs[yrs.index < 1950].mean(); last = yrs[yrs.index >= yrs.index.max() - 9].mean()
    return dict(yr=yrs.index.tolist(), days=yrs.values.tolist(), dec=[[int(k), float(v)] for k, v in dec.items()], thr=thr,
                first=float(first), last=float(last), last_span=[int(yrs.index.max() - 9), int(yrs.index.max())], max=[int(yrs.idxmax()), int(yrs.max())],
                start=int(yrs.index.min()), partial=[int(y) for y in days.index[~ok]])


ANALYSES = [('events', a_events), ('msl', a_msl), ('flood', a_flood), ('amax', None), ('surge', a_surge), ('sst', a_sst), ('flow', a_flow), ('air', a_air),
            ('marsh', a_marsh), ('tideclock', a_tideclock), ('strat', a_strat), ('soil', a_soil), ('head', None), ('wrose', a_wrose),
            ('chl', a_chl), ('anova', a_anova), ('coast', a_coast), ('rain', a_rain), ('radar', a_radar),
            ('drift', a_drift), ('shields', a_shields), ('currents', a_currents), ('ode', a_ode)]


def run(site):
    C = Ctx(site); R = {}; errors = {}
    for key, fn in ANALYSES:
        try:
            if key == 'amax':
                R[key] = a_amax(C, R['msl'])
            elif key == 'head':
                R[key] = a_headlines(C, R['surge'])
            else:
                R[key] = fn(C)
            print(f'  ✓ {key}')
        except Exception as e:  # noqa: BLE001
            errors[key] = f'{type(e).__name__}: {e}'
            print(f'::warning::analysis "{key}" skipped: {e}')
            traceback.print_exc()
    R['cfg'] = dict(normal=SHORE_NORMAL)
    R['_errors'] = errors
    R['_built'] = pd.Timestamp.now(tz=TZ).strftime('%b %d, %Y %I:%M %p')
    return R


if __name__ == '__main__':
    import sys
    R = run(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'site'))
    print(json.dumps({k: (v if k.startswith('_') else '…') for k, v in R.items()}, indent=1, default=str))
