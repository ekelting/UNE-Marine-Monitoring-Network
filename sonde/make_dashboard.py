"""
make_dashboard.py — builds the dashboard page (index.html) for the BlueSonde buoy.
Same look and behaviour as the Camp Ellis / Biddeford Pool wave-buoy pages.
"""
import html
import json

import numpy as np
import pandas as pd

import core as bc
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'shared'))
import mapjs  # noqa: E402
import explain  # noqa: E402

BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    '#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948')
SEQ = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
WARM = ['#2a78d6', '#6da7ec', '#cde2fb', '#fde3b5', '#f6a86c', '#eb6834', '#b8381a']   # cold → warm
GRNS = ['#e6f4ea', '#bfe3c7', '#8fcf9e', '#5cb877', '#2f9a52', '#137a37', '#065a25']
esc = html.escape


def _clean(v):
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, (float, np.floating)):
        return None if not np.isfinite(v) else round(float(v), 4)
    if isinstance(v, np.integer):
        return int(v)
    return v


def _ts(idx):
    return [t.strftime('%Y-%m-%d %H:%M') for t in idx]


def _loc(s):
    s = s.copy()
    s.index = bc.local(s.index).tz_localize(None)
    return s


def _fig(traces, layout):
    return {'data': traces, 'layout': layout}


def _for_plot(df, max_full_days=60):
    """Full-resolution readings for the last N days, hourly averages before that (keeps the page light)."""
    num = df.drop(columns=['res'], errors='ignore')
    cut = num.index.max() - pd.Timedelta(days=max_full_days)
    old = num[num.index < cut]
    if len(old):
        old = old.resample('1h').mean().dropna(how='all')
    out = pd.concat([old, num[num.index >= cut]]) if len(old) else num
    out = out.dropna(how='all', subset=[c for c in bc.SCIENCE if c in out] or None)
    gaps = out.index.to_series().diff() > pd.Timedelta(hours=3)        # break the line across data gaps
    if gaps.any():
        brk = pd.DataFrame(index=out.index[gaps.values] - pd.Timedelta(minutes=1), columns=out.columns, dtype=float)
        out = pd.concat([out, brk]).sort_index()
    return _loc(out)


def build_figs(S):
    df, st = S['df'], S['stats']
    figs = {}
    P = _for_plot(df)
    x = _ts(P.index)
    T = _loc(S['tide'].dropna()) if len(S['tide']) else pd.Series(dtype=float)
    if len(T):
        T = T[T.index >= P.index.min() - pd.Timedelta(hours=6)]

    # 1) every reading — stacked panels on one time axis ----------------------------
    panels = []      # (key, title, trace)
    if len(T):
        panels.append(('Water level (LUNIT)', dict(type='scatter', mode='lines', name='Water level', x=_ts(T.index),
                       y=_clean(T.tolist()), line=dict(color=VIOLET, width=1.4), meta='len',
                       hovertemplate='%{x|%b %d %I:%M %p}<br>water level %{y:.1f} LUNIT<extra></extra>')))
    spec = [('temp_c', 'Water temp (TUNIT)', ORANGE, 'temp', '%{y:.1f} TUNIT'),
            ('sal_psu', 'Salinity (PSU)', BLUE, None, '%{y:.2f} PSU'),
            ('do_mgl', 'Oxygen (mg/L)', AQUA, None, '%{y:.2f} mg/L'),
            ('chl_ugl', 'Chlorophyll (µg/L)', GREEN, None, '%{y:.2f} µg/L'),
            ('trp_ppb', 'Tryptophan (ppb)', MAGENTA, None, '%{y:.1f} ppb'),
            ('turb_ntu', 'Turbidity (NTU)', '#8a6d3b', None, '%{y:.2f} NTU')]
    for c, title, col, meta, hv in spec:
        if c in P and P[c].notna().any():
            panels.append((title, dict(type='scattergl', mode='lines', name=title.split(' (')[0], x=x, y=_clean(P[c].tolist()),
                                       line=dict(color=col, width=1.3), connectgaps=False, meta=meta,
                                       hovertemplate='%{x|%b %d %I:%M %p}<br><b>' + hv + '</b><extra></extra>')))
    n = len(panels)
    gap = 0.035
    h = (1 - gap * (n - 1)) / max(n, 1)
    layout = dict(showlegend=False, height=170 * n + 90, margin=dict(l=70, r=20, t=40, b=40),
                  xaxis=dict(type='date', anchor=f'y{n if n > 1 else ""}',
                             rangeselector=dict(buttons=[dict(count=1, label='1 day', step='day', stepmode='backward'),
                                                         dict(count=3, label='3 days', step='day', stepmode='backward'),
                                                         dict(count=7, label='1 wk', step='day', stepmode='backward'),
                                                         dict(count=1, label='1 mo', step='month', stepmode='backward'),
                                                         dict(step='all', label='All')], y=1.0, yanchor='bottom')),
                  shapes=[])
    traces = []
    for i, (title, tr) in enumerate(panels):
        ax = '' if i == 0 else str(i + 1)
        top = 1 - i * (h + gap)
        tr['xaxis'], tr['yaxis'] = 'x', 'y' + ax
        traces.append(tr)
        layout['yaxis' + ax] = dict(title=title, domain=[max(top - h, 0), top], anchor='x')
        if title.startswith('Oxygen'):
            for lvl, colr in [(bc.DO_STRESS, YELLOW), (bc.DO_HYPOXIC, RED)]:
                if st.get('do_mgl', {}).get('min', 99) < lvl + 2:
                    layout['shapes'].append(dict(type='line', xref='x domain', x0=0, x1=1, yref='y' + ax, y0=lvl, y1=lvl,
                                                 line=dict(color=colr, width=1.2, dash='dash')))
    figs['timeline'] = _fig(traces, layout)

    # 2) tide phase small multiples -----------------------------------------------------
    pt = S.get('phase_tab')
    if pt is not None and len(pt):
        items = [(c, t, col, m) for c, t, col, m in [('sal_psu', 'Salinity (PSU)', BLUE, None), ('temp_c', 'Water temp (TUNIT)', ORANGE, 'temp'),
                                                     ('do_pct', 'Oxygen saturation (%)', AQUA, None), ('turb_ntu', 'Turbidity (NTU)', '#8a6d3b', None)]
                 if (c, 'mean') in pt]
        tr, lay = [], dict(showlegend=False, height=460, margin=dict(l=60, r=20, t=30, b=50), annotations=[], shapes=[])
        for i, (c, t, col, m) in enumerate(items):
            r, cc = divmod(i, 2)
            ax = '' if i == 0 else str(i + 1)
            s = pt[(c, 'mean')][pt[(c, 'count')] >= 4]
            tr.append(dict(type='scatter', mode='lines+markers', x=_clean(s.index.tolist()), y=_clean(s.tolist()),
                           line=dict(color=col, width=2.4, shape='spline'), marker=dict(size=4, color=col), meta=m,
                           xaxis='x' + ax, yaxis='y' + ax, name=t,
                           hovertemplate='%{x:+.1f} h from high tide<br><b>%{y:.2f}</b> ' + t.split('(')[-1].rstrip(')') + '<extra></extra>'))
            x0, x1 = (0, 0.4) if cc == 0 else (0.6, 1)
            y0, y1 = (0.58, 1) if r == 0 else (0, 0.42)
            lay['xaxis' + ax] = dict(domain=[x0, x1], anchor='y' + ax, range=[-6.4, 6.4], dtick=2, zeroline=False,
                                     title='Hours from high tide' if r == 1 else None)
            lay['yaxis' + ax] = dict(domain=[y0, y1], anchor='x' + ax, title=t)
            lay['shapes'].append(dict(type='line', xref='x' + ax, x0=0, x1=0, yref=f'y{ax} domain', y0=0, y1=1,
                                      line=dict(color='#8a8984', width=1, dash='dot')))
        figs['tidephase'] = _fig(tr, lay)

    # 3) daily rhythm -----------------------------------------------------------------
    di = S.get('diel')
    if di is not None and len(di):
        hrs = [f'{h:02d}:00' for h in di.index]
        lbl = [f'{(h % 12) or 12} {"AM" if h < 12 else "PM"}' for h in di.index]
        tr, lay = [], dict(showlegend=False, height=380, margin=dict(l=60, r=20, t=20, b=50),
                           xaxis=dict(tickvals=hrs[::3], ticktext=lbl[::3], title='Time of day (Eastern)', anchor='y2'))
        items = [(c, t, col, m) for c, t, col, m in [('do_pct', 'Oxygen saturation (%)', AQUA, None), ('temp_c', 'Water temp (TUNIT)', ORANGE, 'temp')] if c in di]
        for i, (c, t, col, m) in enumerate(items):
            ax = '' if i == 0 else str(i + 1)
            tr.append(dict(type='scatter', mode='lines+markers', x=hrs, y=_clean(di[c].tolist()), customdata=lbl, meta=m,
                           line=dict(color=col, width=2.4, shape='spline'), marker=dict(size=5), xaxis='x', yaxis='y' + ax,
                           hovertemplate='%{customdata}: <b>%{y:.2f}</b> ' + t.split('(')[-1].rstrip(')') + '<extra></extra>'))
            lay['yaxis' + ax] = dict(title=t, domain=[0.55, 1] if i == 0 else [0, 0.45], anchor='x')
        figs['diel'] = _fig(tr, lay)

    # 4) calendars --------------------------------------------------------------------
    dy = S['daily']
    cal = {'temp': ('temp_c_mean', 'Daily average water temp (TUNIT)', WARM, 'temp', '%{z:.1f} TUNIT'),
           'sal': ('sal_psu_min', 'Daily lowest salinity (PSU)', SEQ, None, 'lowest salinity %{z:.1f} PSU'),
           'do': ('do_mgl_min', 'Daily lowest oxygen (mg/L)', list(reversed(WARM)), None, 'lowest oxygen %{z:.1f} mg/L'),
           'chl': ('chl_ugl_mean', 'Daily average chlorophyll (µg/L)', GRNS, None, 'average chlorophyll %{z:.2f} µg/L'),
           'trp': ('trp_ppb_mean', 'Daily average tryptophan (ppb)', SEQ, None, 'average tryptophan %{z:.1f} ppb')}
    for k, (col, title, pal, m, hv) in cal.items():
        if col not in dy or dy[col].notna().sum() == 0:
            continue
        d = dy[col].copy()
        d.index = pd.to_datetime(d.index)
        months = pd.period_range(d.index.min(), d.index.max(), freq='M')
        z, txt = [], []
        for p in months:
            row, trow = [], []
            for day in range(1, 32):
                try:
                    t = pd.Timestamp(year=p.year, month=p.month, day=day)
                except ValueError:
                    row.append(None)
                    trow.append('')
                    continue
                v = d.get(t, np.nan)
                row.append(None if pd.isna(v) else round(float(v), 3))
                trow.append(t.strftime('%a %b %d, %Y'))
            z.append(row)
            txt.append(trow)
        vals = d.dropna().values
        figs['cal_' + k] = _fig([dict(
            type='heatmap', z=z, x=list(range(1, 32)), y=[p.strftime('%b %Y') for p in months], text=txt, meta=m,
            colorscale=[[i / (len(pal) - 1), c] for i, c in enumerate(pal)], xgap=2, ygap=2,
            zmin=float(np.nanpercentile(vals, 2)), zmax=float(np.nanpercentile(vals, 98)) + 1e-6,
            colorbar=dict(title=dict(text=title, side='right'), thickness=10, len=0.9),
            hovertemplate='%{text}<br><b>' + hv + '</b><extra></extra>')],
            dict(margin=dict(l=80, r=20, t=20, b=50), yaxis=dict(autorange='reversed', fixedrange=True, title='Month'),
                 xaxis=dict(title='Day of the month', dtick=5, fixedrange=True, range=[0.5, 31.5]),
                 height=max(240, 40 * len(months) + 120)))

    # 6) buoy health ------------------------------------------------------------------
    hcols = [(c, t, col, m) for c, t, col, m in [('volt_v', 'Solar/battery diag. (V)', GREEN, None), ('batt_ma', 'Battery current (mA)', BLUE, None),
                                                 ('hull_rh', 'Hull humidity (%)', AQUA, None), ('hull_c', 'Hull temp (TUNIT)', ORANGE, 'temp')]
             if c in df and df[c].notna().any()]
    if hcols:
        Hh = _loc(df[[c for c, *_ in hcols]].resample('1h').mean())
        n = len(hcols)
        h = (1 - 0.05 * (n - 1)) / n
        tr, lay = [], dict(showlegend=False, height=150 * n + 60, margin=dict(l=70, r=20, t=20, b=40), xaxis=dict(type='date', anchor=f'y{n if n > 1 else ""}'))
        for i, (c, t, col, m) in enumerate(hcols):
            ax = '' if i == 0 else str(i + 1)
            top = 1 - i * (h + 0.05)
            tr.append(dict(type='scatter', mode='lines', x=_ts(Hh.index), y=_clean(Hh[c].tolist()), meta=m, connectgaps=False,
                           line=dict(color=col, width=1.6), xaxis='x', yaxis='y' + ax,
                           hovertemplate='%{x|%b %d %I %p}: <b>%{y:.2f}</b> ' + t.split('(')[-1].rstrip(')') + '<extra></extra>'))
            lay['yaxis' + ax] = dict(title=t, domain=[max(top - h, 0), top], anchor='x')
        figs['health'] = _fig(tr, lay)
    return figs


def level(v, cuts):
    for lim, word in cuts:
        if v < lim:
            return word
    return cuts[-1][1]


def build_html(S, path, plotly_src, downloads=None, notice='', tides=None):
    st = S['stats']
    lt = st['latest']
    figs = build_figs(S)
    now = pd.Timestamp.now(tz=bc.LOCAL_TZ)
    age_days = (now - st['last']) / pd.Timedelta(days=1)

    EXL = {'Salinity': 'salinity', 'Water temperature': 'water_temp', 'Dissolved oxygen': 'do', 'Chlorophyll (algae)': 'chl',
           'Tryptophan (relative)': 'trp', 'Turbidity (cloudiness)': 'turb', 'Specific conductivity': 'conductivity'}

    def tile(emoji, label, value, sub=''):
        k = EXL.get(label)
        info = f' <a class="ti" href="#ex-{"cond" if k == "conductivity" else k}" title="What is this?">ⓘ</a>' if k else ''
        return (f'<div class="tile"><div class="t-emoji">{emoji}</div><div class="t-label">{esc(label)}{info}</div>'
                f'<div class="t-value">{value}</div><div class="t-sub">{sub}</div></div>')

    def T(c, dec=1):
        return f'<span class="temp" data-c="{c}" data-d="{dec}">{bc.c2f(c):.{dec}f} °F</span>'

    def T2(c):        # the other unit, for subtitles
        return f'<span class="temp-alt" data-c="{c}">{c:.1f} °C</span>'

    def g(c):
        return lt[c][0] if c in lt else np.nan

    tiles = []
    if np.isfinite(g('sal_psu')):
        e, n, d = bc.sal_vibe(g('sal_psu'))
        tiles.append(tile(e, 'Salinity', f'{g("sal_psu"):.1f} PSU', f'{n} — {esc(d)}'))
    if np.isfinite(g('temp_c')):
        tiles.append(tile('🌡️', 'Water temperature', T(g('temp_c')), T2(g('temp_c'))))
    if np.isfinite(g('do_mgl')) or np.isfinite(g('do_pct')):
        mg, pc = g('do_mgl'), g('do_pct')
        health = '' if not np.isfinite(mg) else (' · healthy ✅' if mg >= bc.DO_STRESS else (' · stressful ⚠️' if mg >= bc.DO_HYPOXIC else ' · hypoxic 🚨'))
        tiles.append(tile('🫧', 'Dissolved oxygen', f'{mg:.1f} mg/L' if np.isfinite(mg) else f'{pc:.0f}%',
                          (f'{pc:.0f}% saturation' if np.isfinite(pc) else '') + health))
    if np.isfinite(g('chl_ugl')):
        tiles.append(tile('🌿', 'Chlorophyll (algae)', f'{g("chl_ugl"):.1f} µg/L',
                          level(g('chl_ugl'), [(2, 'low — clear water'), (5, 'moderate'), (10, 'elevated'), (1e9, 'bloom level 🌱')])))
    if np.isfinite(g('trp_ppb')):
        v = S['df']['trp_ppb'].dropna()
        base = v.iloc[-500:].median() if len(v) else np.nan
        d = g('trp_ppb') - base
        tiles.append(tile('🔬', 'Tryptophan (relative)', f'{g("trp_ppb"):.0f} ppb',
                          f'{d:+.0f} vs. its usual level · rises can signal sewage or runoff' if np.isfinite(base) else 'pollution early-warning signal'))
    if np.isfinite(g('turb_ntu')):
        tiles.append(tile('🟤', 'Turbidity (cloudiness)', f'{g("turb_ntu"):.1f} NTU',
                          level(g('turb_ntu'), [(5, 'clear'), (20, 'a little cloudy'), (100, 'murky'), (1e9, 'very muddy')])))
    if np.isfinite(g('spcond_uscm')):
        tiles.append(tile('⚡', 'Specific conductivity', f'{g("spcond_uscm") / 1000:.1f} mS/cm', 'how well the water carries electricity (salt)'))
    now_tiles = ''.join(tiles)

    season = [tile('📆', 'Days on watch', f'{st["days"]:.0f}', f'since {st["first"]:%b %d, %Y}'),
              tile('📡', 'Readings', f'{st["n"]:,}', f'{st["coverage_pct"]:.0f}% of hours covered')]
    if 'temp_c' in st:
        season += [tile('🔥', 'Warmest water', T(st['temp_c']['max']), f'{st["temp_c"]["tmax"]:%b %d, %Y}'),
                   tile('🧊', 'Coldest water', T(st['temp_c']['min']), f'{st["temp_c"]["tmin"]:%b %d, %Y}')]
    if 'sal_psu' in st:
        season.append(tile('💧', 'Freshest water', f'{st["sal_psu"]["min"]:.1f} PSU', f'{st["sal_psu"]["tmin"]:%b %d, %Y}'))
    if 'do_mgl' in st:
        season.append(tile('🫧', 'Lowest oxygen', f'{st["do_mgl"]["min"]:.1f} mg/L', f'{st["do_mgl"]["tmin"]:%b %d, %Y}'))
    if 'chl_ugl' in st:
        season.append(tile('🌿', 'Most algae', f'{st["chl_ugl"]["max"]:.1f} µg/L', f'{st["chl_ugl"]["tmax"]:%b %d, %Y}'))
    season_tiles = ''.join(season)

    cards = ''.join(f'<div class="card insight"><div class="i-emoji">{em}</div><div><h4>{esc(h)}</h4><p>{esc(t)}</p></div></div>'
                    for em, h, t in bc.insights(S))

    # month-by-month table
    mo = S['monthly']
    def cell(r, c, f='{:.1f}', temp=False):
        v = r.get(c, np.nan)
        if pd.isna(v):
            return '<td>—</td>'
        return f'<td>{T(v)}</td>' if temp else f'<td>{f.format(v)}</td>'
    mcols = [(c, lbl, f, t) for c, lbl, f, t in [
        ('temp_c_mean', 'Temp avg', None, True), ('temp_c_min', 'Temp low', None, True), ('temp_c_max', 'Temp high', None, True),
        ('sal_psu_mean', 'Salinity avg', '{:.1f}', False), ('sal_psu_min', 'Salinity low', '{:.1f}', False),
        ('do_mgl_mean', 'Oxygen avg (mg/L)', '{:.1f}', False), ('do_mgl_min', 'Oxygen low', '{:.1f}', False),
        ('chl_ugl_mean', 'Chlorophyll avg (µg/L)', '{:.2f}', False), ('chl_ugl_max', 'Chl. high', '{:.1f}', False),
        ('trp_ppb_mean', 'Tryptophan avg (ppb)', '{:.0f}', False), ('trp_ppb_max', 'Trp. high', '{:.0f}', False),
        ('turb_ntu_mean', 'Turbidity avg (NTU)', '{:.1f}', False), ('turb_ntu_max', 'Turb. high', '{:.0f}', False)] if c in mo]
    mhead = '<th>Month</th><th>Days</th>' + ''.join(f'<th>{esc(l)}</th>' for _, l, _, _ in mcols)
    mrows = ''.join(
        f'<tr><td><b>{esc(r["label"])}</b></td><td>{int(r["days_with_data"])}/{int(r["days_in_month"])}</td>'
        + ''.join(cell(r, c, f or '{:.1f}', t) for c, _, f, t in mcols) + '</tr>'
        for r in mo.to_dict('records')[::-1])

    stale = ''
    if age_days > 0.5:
        stale = (f'<div class="banner">📡 The buoy hasn\'t reported since <b>{st["last"]:%b %d, %Y %I:%M %p}</b> ({age_days:.1f} days). '
                 'It may be out of the water for maintenance, or the data link may be delayed — this page catches up automatically '
                 'once readings resume.</div>')
    if notice:
        stale += ('<div class="banner">⚠️ Part of the latest hourly update didn\'t come through, so the newest readings may be '
                  'missing for a little while. It usually sorts itself out on the next update.</div>')
    dl = ''
    if downloads:
        dl = '<div class="chips" style="margin-top:12px">' + ''.join(
            f'<a class="chip dl" href="{esc(h)}" download>{esc(lbl)}</a>' for lbl, h in downloads) + '</div>'
    rows = [('📍 Position', f'{bc.CFG["mooring_lat"]:.5f}° N, {abs(bc.CFG["mooring_lon"]):.5f}° W'),
            ('🔬 Instrument', f'BlueSonde {esc(bc.DEV)} — ' + ', '.join(n for c, n in [('temp_c', 'temperature'), ('sal_psu', 'salinity'),
                ('do_mgl', 'oxygen'), ('chl_ugl', 'chlorophyll'), ('trp_ppb', 'tryptophan'), ('turb_ntu', 'turbidity')] if c in S['df'])),
            ('🕒 Reports', 'about every 15 minutes'),
            ('🚀 Data since', f'{st["first"]:%B %d, %Y}'),
            ('🔗 Live source', f'<a href="{esc(bc.CFG["cumulus_url"])}">CUMULUS sensor page</a>')]
    where = ''.join(f'<div class="kv"><span>{k}</span><b>{v}</b></div>' for k, v in rows)
    tide_st = str(bc.CFG.get('tide_station') or '')
    if tide_st:
        where += (f'<div class="tidebox"><h3>🌙 Tides today &amp; tomorrow</h3><div class="tide-next" id="tide-next"></div>'
                  f'<div id="tide" class="tidechart"></div>'
                  f'<p class="t-sub" style="margin:4px 0 0">Predicted by NOAA for {esc(bc.CFG.get("tide_station_name") or tide_st)} '
                  f'(<a href="https://tidesandcurrents.noaa.gov/noaatidepredictions.html?id={esc(tide_st)}">station {esc(tide_st)}</a>). '
                  'Heights are above average low tide (MLLW).</p></div>')
    me = dict(lat=bc.CFG['mooring_lat'], lon=bc.CFG['mooring_lon'], kind='wq', label=bc.SITE_SHORT,
              sub=f'BlueSonde {bc.DEV} water-quality buoy')
    mapdata = mapjs.mapdata(me, bc.SISTER_SITES, center=[me['lat'] + 0.005, me['lon'] - 0.025], zoom=11)
    sisters = mapjs.nav_buttons(bc.SISTER_SITES)
    here = {}
    if 'temp_c' in st:
        t = st['temp_c']
        here['water_temp'] = f'typically {bc.c2f(t["median"]):.0f} °F ({t["median"]:.1f} °C); {bc.c2f(t["min"]):.0f}–{bc.c2f(t["max"]):.0f} °F so far.'
    if 'sal_psu' in st:
        t = st['sal_psu']
        here['salinity'] = f'typically {t["median"]:.1f} PSU; lowest so far {t["min"]:.1f}, highest {t["max"]:.1f}.'
    if 'do_mgl' in st:
        t = st['do_mgl']
        here['do'] = f'averages {t["mean"]:.1f} mg/L; lowest so far {t["min"]:.1f} mg/L.'
    if 'chl_ugl' in st:
        here['chl'] = f'typically {st["chl_ugl"]["median"]:.1f} µg/L; highest so far {st["chl_ugl"]["max"]:.1f}.'
    if 'trp_ppb' in st:
        here['trp'] = f'usual level about {st["trp_ppb"]["median"]:.0f} ppb on this sensor — look for rises above that.'
    if 'turb_ntu' in st:
        here['turb'] = f'typically {st["turb_ntu"]["median"]:.1f} NTU.'
    if 'spcond_uscm' in st:
        here['cond'] = f'typically {st["spcond_uscm"]["median"] / 1000:.1f} mS/cm.'
    exp_keys = [explain.FOR_KEY[c] for c in ['temp_c', 'sal_psu', 'do_mgl', 'chl_ugl', 'trp_ppb', 'turb_ntu', 'spcond_uscm'] if c in S['df']] + ['tide']
    explain_html = explain.SECTION.format(cards=explain.cards(exp_keys, here))
    vibes = ''.join(f'<span class="chip">{v[1]} {v[2]} <small>{"&lt;" + format(v[0], "g") + " PSU" if v[0] < 99 else "30+ PSU"}</small></span>'
                    for v in bc.SAL_VIBES)
    qc = ''.join(f'<li>{esc(n)}</li>' for n in bc.qc_notes(S))
    cal_btns = ''.join(f'<button class="seg" data-cal="{k}" aria-pressed="false">{lbl}</button>' for k, lbl in
                       [('temp', '🌡️ Temperature'), ('sal', '💧 Salinity'), ('do', '🫧 Oxygen'), ('chl', '🌿 Chlorophyll'), ('trp', '🔬 Tryptophan')]
                       if 'cal_' + k in figs)
    howto = ('<li>This page updates itself <b>every hour</b> with the buoy\'s newest readings from the public '
             f'<a href="{esc(bc.CFG["cumulus_url"])}">CUMULUS (Coastal Measures)</a> sensor page. All times are US Eastern.</li>'
             '<li>Want the numbers? Use the download buttons at the top: a spreadsheet plus CSV files (every reading, hourly, daily, monthly).</li>'
             '<li>Tip: to keep a Google Sheet that stays current on its own, type this into any cell: '
             f'<code>=IMPORTDATA("{bc.SITE_URL}data/daily.csv")</code></li>')
    page = TEMPLATE
    for k, v in {
        '%%PLOTLY_TAG%%': f'<script src="{plotly_src}"></script>', '%%FIGS%%': json.dumps(figs, default=str, ensure_ascii=False),
        '%%MAPHEAD%%': mapjs.HEAD, '%%MAPCSS%%': mapjs.CSS, '%%MAPJS%%': mapjs.JS.replace('%%MAPDATA%%', mapdata), '%%LEGEND%%': mapjs.LEGEND, '%%EXCSS%%': explain.CSS, '%%EXPLAIN%%': explain_html,
        '%%TIDES%%': json.dumps(tides or []), '%%TIDE_ST%%': json.dumps(tide_st), '%%TZ%%': json.dumps(bc.LOCAL_TZ),
        '%%WHERE%%': where, '%%SISTERS%%': sisters, '%%DOWNLOADS%%': dl, '%%NOW_TILES%%': now_tiles,
        '%%SEASON_TILES%%': season_tiles, '%%CARDS%%': cards, '%%MROWS%%': mrows, '%%MHEAD%%': mhead, '%%STALE%%': stale, '%%VIBES%%': vibes,
        '%%QC%%': qc, '%%HOWTO%%': howto, '%%CALBTNS%%': cal_btns,
        '%%FOOTSRC%%': f'from <a href="{bc.REPO_URL}">{bc.GITHUB_USER}/{bc.GITHUB_REPO}</a> on GitHub',
        '%%TIDE_ST_TXT%%': esc(f"{tide_st} ({bc.CFG.get('tide_station_name', '')})" if tide_st else 'n/a'),
        '%%SHORT%%': esc(bc.SITE_SHORT), '%%SITE%%': esc(bc.SITE_PHRASE), '%%DEV%%': esc(bc.DEV),
        '%%LATEST%%': f'{st["last"]:%A, %b %d %Y at %I:%M %p}',
        '%%GENERATED%%': f'{now:%b %d, %Y %I:%M %p %Z}',
    }.items():
        page = page.replace(k, v)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(page)


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%%SHORT%% Water Quality</title>
%%MAPHEAD%%
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>💧</text></svg>">
<style>
:root{--bg:#f5f8fa;--card:#ffffff;--ink:#0b0b0b;--ink2:#52514e;--muted:#8a8984;--line:#e3e8ec;--accent:#1c5cab;
--hero1:#0d4a5a;--hero2:#2a7a5c;--chip:#eef4fb;--chip2:#b7d3f6;--warn:#fff4e0;--warnline:#eda100;--grid:#e8ecef}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#111213;--card:#1a1a19;--ink:#ffffff;--ink2:#c3c2b7;
--muted:#8f8e86;--line:#2c2d2e;--accent:#86b6ef;--hero1:#0b3540;--hero2:#1d5a44;--chip:#23282e;--chip2:#1c5cab;--warn:#2d2616;--warnline:#c98500;--grid:#2a2b2c}}
:root[data-theme="dark"]{--bg:#111213;--card:#1a1a19;--ink:#ffffff;--ink2:#c3c2b7;--muted:#8f8e86;--line:#2c2d2e;--accent:#86b6ef;
--hero1:#0b3540;--hero2:#1d5a44;--chip:#23282e;--chip2:#1c5cab;--warn:#2d2616;--warnline:#c98500;--grid:#2a2b2c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:0 16px 48px}
header.hero{background:linear-gradient(135deg,var(--hero1),var(--hero2));color:#fff;padding:36px 16px 70px;position:relative;overflow:hidden}
header.hero .wrap{padding-bottom:0}
header h1{margin:0;font-size:clamp(26px,4vw,40px);letter-spacing:-.5px}
header p{margin:6px 0 0;opacity:.88}
.waves{position:absolute;left:0;right:0;bottom:-2px;height:60px}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
.btn{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.35);color:#fff;border-radius:999px;padding:6px 14px;cursor:pointer;font:inherit;font-size:14px}
a.btn{text-decoration:none;display:inline-block}
.btn[aria-pressed="true"]{background:#fff;color:#0d4a5a;font-weight:600}
.maptools{display:flex;gap:6px;flex-wrap:wrap;padding:10px 12px}
.seg{background:var(--chip);color:var(--ink);border:1px solid var(--line);border-radius:999px;padding:5px 12px;cursor:pointer;font:inherit;font-size:13px}
.seg[aria-pressed="true"]{background:var(--accent);color:#fff;border-color:var(--accent)}
.kv{display:flex;justify-content:space-between;gap:12px;padding:9px 0;border-bottom:1px solid var(--line);font-size:14px}
.kv span{color:var(--ink2);white-space:nowrap}.kv b{text-align:right}
.wherecard{display:flex;flex-direction:column}.mapcard{display:flex;flex-direction:column}.mapcard #map{flex:1}
.tidebox{margin-top:14px;padding-top:12px;border-top:1px solid var(--line);flex:1;display:flex;flex-direction:column}
.tidebox h3{margin:0 0 6px;font-size:15px}.tidechart{min-height:250px}
.tide-next{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:14px;color:var(--ink2)}.tide-next b{color:var(--ink)}
section{margin-top:28px}
h2{font-size:22px;margin:0 0 4px}
h3{font-size:17px;margin:14px 0 8px}
.lede{color:var(--ink2);margin:0 0 14px}
.grid{display:grid;gap:12px}
.tiles{grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}
.tile,.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.now{margin-top:-52px;position:relative}
.t-emoji{font-size:26px;line-height:1.1}
.t-label{color:var(--ink2);font-size:13px;margin-top:6px}
.t-value{font-size:28px;font-weight:700;letter-spacing:-.5px}
.t-sub{color:var(--muted);font-size:13px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
a.chip.dl{background:rgba(255,255,255,.14);color:#fff;text-decoration:none;border:1px solid rgba(255,255,255,.35)}
.chip{background:var(--chip);border-radius:999px;padding:3px 10px;font-size:13px;color:var(--ink2)}
.insights{grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr))}
.insight{display:flex;gap:12px}
.i-emoji{font-size:28px}
.insight h4{margin:0 0 4px;font-size:15px}
.insight p{margin:0;color:var(--ink2);font-size:14px}
.chart{width:100%;min-height:260px}
.two{grid-template-columns:repeat(auto-fit,minmax(min(100%,460px),1fr))}
.banner{background:var(--warn);border-left:4px solid var(--warnline);border-radius:10px;padding:10px 14px;margin-top:16px;color:var(--ink)}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);white-space:nowrap}
th{color:var(--ink2);font-weight:600;font-size:13px}
.tablewrap{overflow-x:auto}
details{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 16px;margin-top:12px}
summary{cursor:pointer;font-weight:600}
details li{color:var(--ink2);margin:6px 0;font-size:14px}
dl{display:grid;grid-template-columns:max-content 1fr;gap:6px 14px;font-size:14px}
dt{font-weight:600}dd{margin:0;color:var(--ink2)}
footer{color:var(--muted);font-size:13px;margin-top:36px}
a{color:var(--accent)}
code{background:var(--chip);padding:1px 5px;border-radius:5px;word-break:break-all}
%%MAPCSS%%
a.ti{text-decoration:none;font-size:12px;opacity:.75;margin-left:2px}a.ti:hover{opacity:1}
table.mtable{font-size:13.5px}.mtable th{white-space:normal;vertical-align:bottom;line-height:1.25}.mtable th,.mtable td{padding:6px 7px}
%%EXCSS%%
@media (max-width:560px){dl{grid-template-columns:1fr}.t-value{font-size:24px}.kv{flex-direction:column;gap:2px}.kv b{text-align:left}}
</style></head>
<body>
<header class="hero"><div class="wrap">
  <h1>💧 The %%SHORT%% Water-Quality Buoy</h1>
  <p>What the water is doing %%SITE%% · BlueSonde <b>%%DEV%%</b></p>
  <div class="toolbar">%%SISTERS%%</div>
  <div class="toolbar">
    <button class="btn" id="u-us" aria-pressed="true">🇺🇸 °F · feet</button>
    <button class="btn" id="u-si" aria-pressed="false">🌍 °C · metres</button>
    <button class="btn" id="theme">🌓 light / dark</button>
  </div>
  %%DOWNLOADS%%
</div>
<svg class="waves" viewBox="0 0 1200 60" preserveAspectRatio="none" aria-hidden="true">
<path d="M0,30 C150,60 300,0 450,30 C600,60 750,0 900,30 C1050,60 1150,15 1200,30 L1200,60 L0,60 Z" fill="var(--bg)"/></svg>
</header>
<div class="wrap">
  <section class="now" style="margin-top:-44px">
    <div class="grid tiles">%%NOW_TILES%%</div>
    <p class="lede" style="margin-top:10px">🕒 Latest reading: <b>%%LATEST%%</b>. How salty is it? The salinity scale (fresh water from rain, streams or rivers lowers it):</p>
    <div class="chips">%%VIBES%%</div>
    %%STALE%%
  </section>

  <section><h2>📍 Where is the buoy?</h2><p class="lede">This buoy is highlighted in orange. The others are UNE's nearby wave buoys (yellow) and water-quality buoys (orange floats) — click one to visit its page.</p>
    <div class="grid two"><div class="card mapcard" style="padding:0;overflow:hidden">
      <div class="maptools"><button class="seg" data-map="street" aria-pressed="true">🗺️ Street map</button><button class="seg" data-map="chart" aria-pressed="false">⚓ Nautical chart (depths &amp; contours)</button></div>
      <div id="map"></div>%%LEGEND%%
      <p class="t-sub" style="margin:6px 12px 10px">Nautical chart: NOAA Office of Coast Survey — depths at low tide, in the units you pick at the top. Not for navigation.</p></div>
    <div class="card wherecard">%%WHERE%%</div></div></section>

  <section><h2>📊 Since the buoy went in</h2><p class="lede">Big-picture numbers from every reading so far.</p>
    <div class="grid tiles">%%SEASON_TILES%%</div></section>

  <section><h2>💡 What the data says</h2><p class="lede">Written automatically from the numbers — it changes as new data arrives.</p>
    <div class="grid insights">%%CARDS%%</div></section>

  %%EXPLAIN%%

  <section><h2>📈 Every reading</h2>
    <p class="lede">All the measurements on one shared timeline, with the tide on top. Use the buttons to zoom to the last day, week or month, or drag across any panel. Dashed lines on the oxygen panel mark the 5 mg/L stress and 2 mg/L hypoxia levels.</p>
    <div class="card"><div id="timeline" class="chart"></div></div></section>

  <section class="grid two">
    <div><h2>🌙 The water breathes with the tide</h2><p class="lede">Each line is the average across every tide so far, lined up by hours before (−) and after (+) high tide. The rising tide brings in ocean water; the falling tide carries water from closer to shore back past the buoy.</p>
      <div class="card"><div id="tidephase" class="chart"></div><p class="t-sub" style="margin:6px 0 0">High-tide times from NOAA predictions for station %%TIDE_ST_TXT%%.</p></div></div>
    <div><h2>☀️ The daily rhythm</h2><p class="lede">Average for each hour of the day. Algae make oxygen in sunlight and everything uses it up overnight; the water warms through the afternoon.</p>
      <div class="card"><div id="diel" class="chart"></div></div></div>
  </section>

  <section><h2>🗓️ The water calendar</h2><p class="lede">Each square is one day. Pick what to colour by. Blank squares = no data.</p>
    <div class="card"><div class="maptools" style="padding:0 0 8px">%%CALBTNS%%</div><div id="calendar" class="chart"></div></div></section>

  <section><h2>📅 Month by month</h2><p class="lede">Averages, lows and highs for each month (newest first).</p>
    <div class="card tablewrap"><table class="mtable"><thead><tr>%%MHEAD%%</tr></thead>
    <tbody>%%MROWS%%</tbody></table></div></section>

  <section><h2>🔧 Buoy health</h2><p class="lede">Power and conditions inside the hull, hourly. The voltage channel drops to 0 every night and climbs with the sun, so it looks like solar-charge input. Humidity creeping upward can mean moisture is getting in.</p>
    <div class="card"><div id="health" class="chart"></div></div></section>

  <section>
    <details><summary>⚠️ Data-quality notes — what was cleaned and why</summary><ul>%%QC%%</ul></details>

    <details><summary>ℹ️ About this data</summary><ul>%%HOWTO%%</ul></details>
  </section>
  <footer>Generated %%GENERATED%% %%FOOTSRC%%. Data: BlueSonde %%DEV%% via CUMULUS (Coastal Measures), University of New England.</footer>
</div>
%%PLOTLY_TAG%%
<script>
const FIGS = %%FIGS%%;
function unitKey(){ return unit==='si' ? 'metric' : 'us'; }
%%MAPJS%%
const M2FT = 3.28084;
let unit = 'us';
try { unit = localStorage.getItem('wq-unit') || 'us'; } catch (e) {}
const ORIG = JSON.parse(JSON.stringify(FIGS));
function css(v){return getComputedStyle(document.documentElement).getPropertyValue(v).trim();}
function sub(s){ if (typeof s!=='string') return s; return s.replaceAll('TUNIT', unit==='us'?'°F':'°C').replaceAll('LUNIT', unit==='us'?'ft':'m'); }
function conv(a,f){return Array.isArray(a)? a.map(x=>Array.isArray(x)? conv(x,f) : (x==null? null: f(x))) : a;}
const toF = c=>c*9/5+32, toFt = m=>m*M2FT;
function themed(layout){
  const ink=css('--ink2'), grid=css('--grid');
  const L = Object.assign({}, layout, {paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
    font:{family:'system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif', color:ink, size:13},
    margin:layout.margin||{l:60,r:20,t:30,b:50}, hoverlabel:{font:{size:13}}});
  for (const k of Object.keys(L)) if (/^[xy]axis\d*$/.test(k)) {
    L[k]=Object.assign({gridcolor:grid, zerolinecolor:grid, linecolor:grid}, L[k]);
    if (typeof L[k].title === 'string') L[k].title = {text: L[k].title, standoff: 10};
    if (L[k].title) L[k].title.font = Object.assign({size: 12, color: ink}, L[k].title.font || {});
  }
  if (L.map) { const dark = getComputedStyle(document.body).backgroundColor.match(/\d+/g).slice(0,3).reduce((a,c)=>a+ +c,0) < 300;
    L.map = Object.assign({}, L.map, {style: dark ? 'carto-darkmatter' : 'carto-positron'}); delete L.xaxis; delete L.yaxis;
    if (L.legend) L.legend = Object.assign({}, L.legend, {bgcolor: dark ? 'rgba(26,26,25,0.8)' : 'rgba(255,255,255,0.8)'}); }
  if (L.xaxis && L.xaxis.rangeselector) L.xaxis.rangeselector=Object.assign({bgcolor:css('--chip'),activecolor:css('--chip2'),font:{color:ink}},L.xaxis.rangeselector);
  return L;
}

// ---------- tide chart (NOAA high/low predictions, smooth cosine curve between them) ----------
let TIDES = %%TIDES%%;
const TIDE_ST = %%TIDE_ST%%, SITE_TZ = %%TZ%%;
const tms = s => Date.parse(s.replace(' ','T')+':00Z');
const tstr = ms => new Date(ms).toISOString().slice(0,16).replace('T',' ');
function siteNow(){ const p=new Intl.DateTimeFormat('en-CA',{timeZone:SITE_TZ,year:'numeric',month:'2-digit',day:'2-digit',
  hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date()); const g=k=>p.find(x=>x.type===k).value;
  return `${g('year')}-${g('month')}-${g('day')} ${g('hour')}:${g('minute')}`; }
function clock(s){ const [h,m]=s.slice(11,16).split(':').map(Number); return `${(h%12)||12}:${String(m).padStart(2,'0')} ${h<12?'AM':'PM'}`; }
function fmtH(ft){ return unit==='us'? ft.toFixed(1)+' ft' : (ft/M2FT).toFixed(2)+' m'; }
function renderTide(){
  const el=document.getElementById('tide'); if(!el || !TIDES.length) return;
  const now=siteNow(), nowMs=tms(now), day0=tms(now.slice(0,10)+' 00:00'), end=day0+48*3600e3;
  const ev=TIDES.map(e=>({ms:tms(e.t), t:e.t, v:+e.v, type:e.type})).sort((a,b)=>a.ms-b.ms);
  const k = unit==='us'? 1 : 1/M2FT, xs=[], ys=[], lu = unit==='us'?'ft':'m';
  for (let i=0;i<ev.length-1;i++){ const a=ev[i], b=ev[i+1];
    for (let ms=Math.max(a.ms,day0-3600e3); ms<b.ms && ms<=end+3600e3; ms+=10*60e3){
      const f=(ms-a.ms)/(b.ms-a.ms); xs.push(tstr(ms)); ys.push((a.v+(b.v-a.v)*(1-Math.cos(Math.PI*f))/2)*k); } }
  const vis=ev.filter(e=>e.ms>=day0 && e.ms<=end), ink=css('--ink2'), acc=css('--accent'), narrow=el.clientWidth<480;
  let cur=null; for (let i=0;i<ev.length-1;i++) if (ev[i].ms<=nowMs && nowMs<ev[i+1].ms){ const a=ev[i],b=ev[i+1],f=(nowMs-a.ms)/(b.ms-a.ms);
    cur={v:a.v+(b.v-a.v)*(1-Math.cos(Math.PI*f))/2, rising:b.type==='H', next:b}; }
  const data=[
    {x:xs,y:ys,type:'scatter',mode:'lines',line:{color:acc,width:2.5,shape:'spline'},fill:'tozeroy',fillcolor:'rgba(28,92,171,0.13)',
     hovertemplate:'%{x|%a %I:%M %p}<br>%{y:.1f} '+lu+'<extra></extra>',name:'tide'},
    {x:vis.map(e=>e.t),y:vis.map(e=>e.v*k),type:'scatter',mode:'markers+text',marker:{size:7,color:acc},
     text:vis.map(e=>(narrow?'':(e.type==='H'?'High ':'Low '))+clock(e.t)),textposition:vis.map(e=>(e.type==='H'?'top ':'bottom ')+(e.ms-day0<3*3600e3?'right':end-e.ms<3*3600e3?'left':'center')),
     cliponaxis:false,textfont:{size:11,color:ink},hovertemplate:vis.map(e=>(e.type==='H'?'High tide':'Low tide')+'<br>%{x|%a %I:%M %p}<br>'+fmtH(e.v)+'<extra></extra>'),name:'hi/lo'}];
  if (cur) data.push({x:[now],y:[cur.v*k],type:'scatter',mode:'markers',marker:{size:12,color:'#f28f16',line:{color:'#fff',width:2}},
     hovertemplate:'Now: '+fmtH(cur.v)+(cur.rising?' and rising':' and falling')+'<extra></extra>',name:'now'});
  const lo=Math.min(...ys), hi=Math.max(...ys), pad=(hi-lo)*0.28;
  const L=themed({showlegend:false,height:250,margin:{l:46,r:14,t:22,b:30},
    xaxis:{type:'date',range:[tstr(day0-40*60e3),tstr(end+40*60e3)],tickformat:'%-I %p',dtick:(narrow?12:6)*3600e3,tickangle:0},
    yaxis:{title:'Tide ('+lu+')',range:[lo-pad,hi+pad],zeroline:true},
    shapes:[{type:'line',x0:now,x1:now,y0:0,y1:1,yref:'paper',line:{color:'#f28f16',width:1.5,dash:'dot'}},
            {type:'line',x0:tstr(day0+24*3600e3),x1:tstr(day0+24*3600e3),y0:0,y1:1,yref:'paper',line:{color:css('--grid'),width:1}}],
    annotations:[{x:tstr(day0+12*3600e3),y:1.0,yref:'paper',yanchor:'bottom',text:'<b>Today</b>',showarrow:false,font:{size:12,color:ink}},
                 {x:tstr(day0+36*3600e3),y:1.0,yref:'paper',yanchor:'bottom',text:'<b>Tomorrow</b>',showarrow:false,font:{size:12,color:ink}}]});
  try{ Plotly.react(el,data,L,{responsive:true,displaylogo:false,displayModeBar:false}); }catch(e){ console.error('tide',e); }
  const nx=document.getElementById('tide-next');
  if (nx){ const up=ev.filter(e=>e.ms>nowMs).slice(0,2);
    nx.innerHTML=(cur? `<span>Now: <b>${fmtH(cur.v)}</b> ${cur.rising?'⬆️ rising':'⬇️ falling'}</span>`:'')+
      up.map(e=>`<span>Next ${e.type==='H'?'high':'low'}: <b>${clock(e.t)}</b> (${fmtH(e.v)})</span>`).join(''); }
}
async function refreshTides(){
  if (!TIDE_ST) return; const now=siteNow(), last=TIDES.length? tms(TIDES[TIDES.length-1].t):0;
  if (last > tms(now)+36*3600e3) return;
  const d=new Date(tms(now)-86400e3).toISOString().slice(0,10).replaceAll('-','');
  try{ const r=await fetch(`https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=predictions&application=UNE_buoy&begin_date=${d}&range=96&datum=MLLW&station=${TIDE_ST}&time_zone=lst_ldt&units=english&interval=hilo&format=json`);
    const j=await r.json(); if (j.predictions && j.predictions.length){ TIDES=j.predictions; renderTide(); } }catch(e){ console.warn('tides',e); }
}
let mapMode='street', calMetric='temp';
try{ mapMode = localStorage.getItem('buoy-map') || 'street'; calMetric = localStorage.getItem('wq-cal') || 'temp'; }catch(e){}
if (!ORIG['cal_'+calMetric]) calMetric = (Object.keys(ORIG).find(k=>k.startsWith('cal_'))||'cal_temp').slice(4);
function render(){
  const ids = Object.keys(ORIG).filter(k=>!k.startsWith('cal_')).concat(['calendar']);
  for (const id of ids){
    const el=document.getElementById(id); const src = id==='calendar'? ORIG['cal_'+calMetric] : ORIG[id];
    if(!el || !src) continue;
    const f=JSON.parse(JSON.stringify(src));
    for (const t of f.data){
      const fn = unit==='us' ? (t.meta==='temp'? toF : t.meta==='len'? toFt : null) : null;
      if (fn){ if (t.type==='heatmap'){ t.z=conv(t.z,fn); t.zmin=fn(t.zmin); t.zmax=fn(t.zmax);} else t.y=conv(t.y,fn); }
      t.hovertemplate=sub(t.hovertemplate);
      if (t.colorbar&&t.colorbar.title) t.colorbar.title.text=sub(t.colorbar.title.text);
    }
    const L=themed(JSON.parse(sub(JSON.stringify(f.layout))));
    let chartLayers=[];
    if (L.map && mapMode==='chart') {
      const dp=encodeURIComponent(JSON.stringify({ECDISParameters:{DynamicParameters:{Parameter:[{name:'DisplayDepthUnits',value: unit==='us'?2:1}]}}}));
      L.map.style='white-bg';
      chartLayers=[{sourcetype:'raster', below:'traces', sourceattribution:'NOAA Office of Coast Survey — not for navigation',
        source:['https://gis.charttools.noaa.gov/arcgis/rest/services/MCS/NOAAChartDisplay/MapServer/exts/MaritimeChartService/WMSServer?service=WMS&request=GetMap&version=1.3.0&layers=0,1,2,3,4,5,6,7&styles=&format=image/png&transparent=false&crs=EPSG:3857&width=256&height=256&bbox={bbox-epsg-3857}&display_params='+dp]}];
    }
    if (L.map) L.height = Math.max(380, el.clientHeight || 0);
    if (id==='tidephase' && el.clientWidth < 520) L.height = 560;
    try {
      const p = Plotly.react(el,f.data,L,{responsive:true,displaylogo:false,modeBarButtonsToRemove:['lasso2d','select2d']});
      if (L.map) { const lay = (mapMode==='chart') ? chartLayers : [];
        Promise.resolve(p).then(()=>setTimeout(()=>Plotly.relayout(el, {'map.layers': lay}), 150)); }
    } catch(e) { console.error('chart '+id, e); }
  }
  document.querySelectorAll('[data-map]').forEach(b=>b.setAttribute('aria-pressed', b.dataset.map===mapMode));
  document.querySelectorAll('[data-cal]').forEach(b=>b.setAttribute('aria-pressed', b.dataset.cal===calMetric));
  document.querySelectorAll('.temp').forEach(el=>{const c=parseFloat(el.dataset.c), d=+(el.dataset.d||1); if(isNaN(c))return;
    el.textContent = unit==='us'? toF(c).toFixed(d)+' °F' : c.toFixed(d)+' °C';});
  document.querySelectorAll('.temp-alt').forEach(el=>{const c=parseFloat(el.dataset.c); if(isNaN(c))return;
    el.textContent = unit==='us'? c.toFixed(1)+' °C' : toF(c).toFixed(1)+' °F';});
  document.querySelectorAll('.len').forEach(el=>{const m=parseFloat(el.dataset.m); if(isNaN(m))return;
    el.textContent = unit==='us'? (m*M2FT).toFixed(1)+' ft' : m.toFixed(2)+' m';});
  try { renderMap(); } catch(e) { console.error('map', e); }
  renderTide();
  document.getElementById('u-us').setAttribute('aria-pressed', unit==='us');
  document.getElementById('u-si').setAttribute('aria-pressed', unit==='si');
}
document.getElementById('u-us').onclick=()=>{unit='us'; try{localStorage.setItem('wq-unit',unit)}catch(e){} render();};
document.getElementById('u-si').onclick=()=>{unit='si'; try{localStorage.setItem('wq-unit',unit)}catch(e){} render();};
document.getElementById('theme').onclick=()=>{const r=document.documentElement;
  const dark = r.dataset.theme? r.dataset.theme==='dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  r.dataset.theme = dark? 'light':'dark'; try{localStorage.setItem('buoy-theme',r.dataset.theme)}catch(e){} render();};
try{const t=localStorage.getItem('buoy-theme'); if(t) document.documentElement.dataset.theme=t;}catch(e){}
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',render);
document.querySelectorAll('[data-map]').forEach(b=>b.onclick=()=>{mapMode=b.dataset.map; try{localStorage.setItem('buoy-map',mapMode)}catch(e){} render();});
document.querySelectorAll('[data-cal]').forEach(b=>b.onclick=()=>{calMetric=b.dataset.cal; try{localStorage.setItem('wq-cal',calMetric)}catch(e){} render();});
render();
refreshTides(); setInterval(()=>{refreshTides(); renderTide();}, 10*60e3);
</script>
</body></html>
"""
