"""
make_dashboard.py — builds the page (index.html) for a UNE weather / environmental station.
Same look and behaviour as the buoy pages. Charts and tiles come from site.json → "vars".
"""
import html
import json
import os as _os
import sys as _sys

import numpy as np
import pandas as pd

import core as bc

_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'shared'))
import explain  # noqa: E402
import mapjs  # noqa: E402

BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    '#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948')
CAT = [ORANGE, BLUE, AQUA, VIOLET, YELLOW, MAGENTA, GREEN, RED]
SEQ = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
UNITPH = {'temp': 'TUNIT', 'speed': 'SUNIT', 'rain': 'RUNIT', 'len': 'LUNIT'}
esc = html.escape


def _clean(v):
    if isinstance(v, (list, tuple, np.ndarray)):
        return [_clean(x) for x in v]
    if isinstance(v, (float, np.floating)):
        return None if not np.isfinite(v) else round(float(v), 4)
    if isinstance(v, np.integer):
        return int(v)
    return v


def _ts(idx):
    return [t.strftime('%Y-%m-%d %H:%M') for t in idx]


def _loc(df):
    d = df.copy()
    d.index = bc.local(d.index).tz_localize(None)
    return d


def ulabel(v):
    return UNITPH.get(v.get('conv'), v.get('unit', ''))


def cv(value, v, dec=None):
    """A number the page re-formats when the visitor switches units."""
    if value is None or not np.isfinite(value):
        return '—'
    d = v.get('dec', 1) if dec is None else dec
    return f'<span class="cv" data-v="{value}" data-c="{v.get("conv", "")}" data-u="{esc(v.get("unit", ""))}" data-d="{d}">{value:.{d}f} {esc(v.get("unit", ""))}</span>'


def build_figs(S):
    df = S['df']
    figs = {}
    # ---------- timeline: stacked panels on one time axis ----------
    cut = df.index.max() - pd.Timedelta(days=60)
    old = bc.resample(df[df.index < cut], '1h') if (df.index < cut).any() else pd.DataFrame()
    recent = df[df.index >= cut]
    P = _loc(pd.concat([old, recent]) if len(old) else recent)
    gaps = P.index.to_series().diff() > pd.Timedelta(hours=3)
    if gaps.any():
        P = pd.concat([P, pd.DataFrame(index=P.index[gaps.values] - pd.Timedelta(minutes=1), columns=P.columns, dtype=float)]).sort_index()
    H = _loc(S['hourly'])
    panels = []
    for v in bc.VARS:
        if v['key'] not in df or v.get('agg') == 'dir' or not v.get('panel'):
            continue
        if v['panel'] not in [p for p, _ in panels]:
            panels.append((v['panel'], []))
        dict(panels)[v['panel']].append(v)
    dirv = next((v for v in bc.VARS if v.get('agg') == 'dir' and v['key'] in df and df[v['key']].notna().sum() > 24), None)
    if dirv:   # where the wind came from, day by day (a 0-360° line or dots are hard to read)
        panels.append(('Wind', [dirv]))
    n = len(panels)
    gap = 0.04
    wts = [1.6 if vs[0].get('agg') == 'dir' else 1 for _, vs in panels]     # the 8-row wind strip gets more room
    hs_ = [(1 - gap * (n - 1)) * w / sum(wts) for w in wts]
    tops = [1 - sum(hs_[:i]) - gap * i for i in range(n)]
    lay = dict(showlegend=True, legend=dict(orientation='h', y=-0.03, yanchor='top', x=0, xanchor='left'),
               height=int(165 * sum(wts) + 150), margin=dict(l=70, r=20, t=50, b=40), hovermode='x unified',
               xaxis=dict(type='date', anchor=f'y{n if n > 1 else ""}',
                          rangeselector=dict(buttons=[dict(count=1, label='1 day', step='day', stepmode='backward'),
                                                      dict(count=3, label='3 days', step='day', stepmode='backward'),
                                                      dict(count=7, label='1 wk', step='day', stepmode='backward'),
                                                      dict(count=1, label='1 mo', step='month', stepmode='backward'),
                                                      dict(step='all', label='All')], x=0, y=1.0, yanchor='bottom')))
    tr = []
    for i, (title, vs) in enumerate(panels):
        ax = '' if i == 0 else str(i + 1)
        top, h = tops[i], hs_[i]
        if vs[0].get('agg') == 'dir':
            # Where the wind came from, day by day: 8 compass rows x 1 column per day, shaded by the share of that
            # day's hours the wind blew from that direction. Reads at any zoom, unlike a 0-360 degree line or dots.
            v = vs[0]
            comp8 = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
            lay['yaxis' + ax] = dict(title='Wind from', domain=[max(top - h, 0), top], anchor='x', type='category',
                                     categoryorder='array', categoryarray=comp8[::-1], fixedrange=True, showgrid=False)
            Wd = df[[v['key']] + (['wind_ms'] if 'wind_ms' in df else [])].dropna()
            if 'wind_ms' in Wd:
                Wd = Wd[Wd['wind_ms'] > 0.3]                      # calm hours have no direction
            if len(Wd):
                Wd = _loc(Wd)
                sec = ((Wd[v['key']] % 360 + 22.5) // 45 % 8).astype(int).map(lambda i: comp8[i])
                tab_ = pd.crosstab(Wd.index.normalize(), sec, normalize='index').reindex(columns=comp8).fillna(0) * 100
                tab_ = tab_.asfreq('1D')                           # keep gaps as gaps
                days = [d.strftime('%Y-%m-%d') for d in tab_.index]
                tr.append(dict(type='heatmap', x=days, y=comp8, z=_clean(tab_.T.round(0).values), xaxis='x', yaxis='y' + ax,
                               colorscale=[[0, 'rgba(183,211,246,0)'], [0.15, '#d6e6fa'], [0.5, '#5598e7'], [1, '#0d366b']],
                               zmin=0, zmax=60, xgap=0, ygap=1, showscale=True, name='Wind from',
                               colorbar=dict(title=dict(text='% of the day', side='right'), thickness=8, len=max(0.12, h),
                                             y=top - h / 2, yanchor='middle', ticksuffix='%'),
                               hovertemplate='%{x|%a %b %d}: from the %{y} %{z:.0f}% of the time<extra></extra>'))
            continue
        units = ulabel(vs[0])
        lay['yaxis' + ax] = dict(title=f'{title} ({units})' if units else title, domain=[max(top - h, 0), top], anchor='x',
                                 rangemode='tozero' if vs[0].get('agg') == 'sum' or vs[0].get('conv') == 'speed' else 'normal')
        for j, v in enumerate(vs):
            col = v.get('color') or CAT[(i + j) % len(CAT)]
            if v.get('agg') == 'sum':
                tr.append(dict(type='bar', name=v['label'] + ' (hourly total)', x=_ts(H.index), y=_clean(H[v['key']].values),
                               marker=dict(color=col), meta=v.get('conv'), xaxis='x', yaxis='y' + ax,
                               hovertemplate='%{y:.2f} ' + ulabel(v) + '<extra>' + esc(v['label']) + '</extra>'))
            else:
                tr.append(dict(type='scattergl', mode='lines', name=v['label'], x=_ts(P.index), y=_clean(P[v['key']].values),
                               line=dict(color=col, width=1.4), connectgaps=False, meta=v.get('conv'), xaxis='x', yaxis='y' + ax,
                               hovertemplate='%{y:.' + str(v.get('dec', 1)) + 'f} ' + ulabel(v) + '<extra>' + esc(v['label']) + '</extra>'))
    figs['timeline'] = dict(data=tr, layout=lay)

    # ---------- day by day ----------
    dy = S['daily'].copy()
    dy.index = pd.to_datetime(dy.index)
    dkeys = [v for v in bc.VARS if v.get('daily') and (f'{v["key"]}_mean' in dy or f'{v["key"]}_total' in dy)]
    if dkeys and len(dy) > 1:
        n = len(dkeys)
        h = (1 - 0.06 * (n - 1)) / n
        tr, lay = [], dict(showlegend=False, height=200 * n + 70, margin=dict(l=70, r=20, t=20, b=40), xaxis=dict(type='date', anchor=f'y{n if n > 1 else ""}'))
        x = [d.strftime('%Y-%m-%d') for d in dy.index]
        for i, v in enumerate(dkeys):
            ax = '' if i == 0 else str(i + 1)
            top = 1 - i * (h + 0.06)
            col = v.get('color') or CAT[i % len(CAT)]
            k = v['key']
            if v.get('agg') == 'sum':
                tr.append(dict(type='bar', x=x, y=_clean(dy[f'{k}_total'].values), marker=dict(color=col), meta=v.get('conv'),
                               xaxis='x', yaxis='y' + ax, hovertemplate='%{x|%a %b %d}: <b>%{y:.2f} ' + ulabel(v) + '</b><extra>daily total</extra>'))
                ttl = f'Daily {v["label"].lower()} ({ulabel(v)})'
            else:
                tr.append(dict(type='scatter', mode='lines', x=x, y=_clean(dy[f'{k}_min'].values), line=dict(width=0, color=col),
                               meta=v.get('conv'), xaxis='x', yaxis='y' + ax, hoverinfo='skip', showlegend=False))
                tr.append(dict(type='scatter', mode='lines', x=x, y=_clean(dy[f'{k}_max'].values), line=dict(width=0, color=col),
                               fill='tonexty', fillcolor=col + '40', meta=v.get('conv'), xaxis='x', yaxis='y' + ax, hoverinfo='skip'))
                tr.append(dict(type='scatter', mode='lines', x=x, y=_clean(dy[f'{k}_mean'].values), line=dict(width=2, color=col),
                               customdata=_clean(np.c_[dy[f'{k}_min'].values, dy[f'{k}_max'].values]), meta=v.get('conv'),
                               xaxis='x', yaxis='y' + ax,
                               hovertemplate='%{x|%a %b %d}: average <b>%{y:.1f}</b> ' + ulabel(v) + '<extra></extra>'))
                ttl = f'{v["label"]} ({ulabel(v)})'
            lay['yaxis' + ax] = dict(title=ttl, domain=[max(top - h, 0), top], anchor='x')
        figs['days'] = dict(data=tr, layout=lay)

    # ---------- wind rose ----------
    if 'wind_dir' in df and 'wind_ms' in df:
        d = df[['wind_dir', 'wind_ms']].dropna()
        d = d[d['wind_ms'] > 0.3]
        if len(d) > 100:
            comp = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
            sector = ((d['wind_dir'] % 360 + 11.25) // 22.5 % 16).astype(int).map(lambda i: comp[i])
            mph = d['wind_ms'] * 2.23694
            bins, labs = [0, 5, 10, 15, 20, 1e9], ['under 5 mph', '5–10 mph', '10–15 mph', '15–20 mph', '20+ mph']
            cut_ = pd.cut(mph, bins=bins, labels=labs, right=False)
            tab = (pd.crosstab(sector, cut_, normalize=True) * 100).reindex(comp).fillna(0)
            tr = [dict(type='barpolar', name=c, r=_clean(tab[c].values) if c in tab else [0] * 16, theta=comp,
                       marker=dict(color=SEQ[min(i + 2, len(SEQ) - 1)]), hovertemplate='from %{theta}: %{r:.1f}% of the time<extra>' + c + '</extra>')
                  for i, c in enumerate(labs)]
            figs['rose'] = dict(data=tr, layout=dict(
                polar=dict(domain=dict(x=[0, 0.62]), angularaxis=dict(direction='clockwise', rotation=90), radialaxis=dict(ticksuffix='%', angle=90)),
                legend=dict(title=dict(text='Wind speed'), x=0.72, y=0.5, yanchor='middle'), height=400, margin=dict(l=30, r=20, t=30, b=30)))
    return figs


def build_html(S, path, plotly_src, downloads=None, notice='', archive_url=None, source_url=None):
    st = S['stats']
    lt = st['latest']
    df = S['df']
    figs = build_figs(S)
    now = pd.Timestamp.now(tz=bc.LOCAL_TZ)
    age_h = (now - st['last']) / pd.Timedelta(hours=1)

    def tile(v):
        k = v['key']
        if k not in lt:
            return ''
        val = lt[k][0]
        sub = ''
        if v.get('agg') == 'sum':
            today, last24 = st['today'].get(k, {}).get('total'), st['last24'].get(k, {}).get('total')
            value = cv(today if today is not None and np.isfinite(today) else 0.0, v, 2)
            sub = f'today so far · last 24 h: {cv(last24, v, 2)}'
            label = v['label'] + ' today'
        elif k == 'wind_ms':
            g = lt.get('gust_ms', (np.nan,))[0]
            dr = lt.get('wind_dir', (np.nan,))[0]
            value = cv(val, v, 0 if v.get('conv') == 'speed' else 1)
            sub = (f'gusting {cv(g, bc.VBY.get("gust_ms", v), 0)}' if np.isfinite(g) else '') + (
                f' · from the {mapjs_compass(dr)}' if np.isfinite(dr) else '')
            label = v['label']
        else:
            value = cv(val, v)
            t = st['today'].get(k, {})
            if t and np.isfinite(t.get('min', np.nan)) and v.get('today_range', True):
                sub = f'today {cv(t["min"], v)} – {cv(t["max"], v)}'
            if v.get('note'):
                sub = (sub + ' · ' if sub else '') + esc(v['note'])
            label = v['label']
        ek = explain.FOR_KEY.get(k)
        info = f' <a class="ti" href="#ex-{ek}" title="What is this?">ⓘ</a>' if ek else ''
        return (f'<div class="tile"><div class="t-emoji">{v.get("emoji", "📍")}</div><div class="t-label">{esc(label)}{info}</div>'
                f'<div class="t-value">{value}</div><div class="t-sub">{sub}</div></div>')

    now_tiles = ''.join(tile(v) for v in bc.VARS if v.get('tile'))
    cards = ''.join(f'<div class="card insight"><div class="i-emoji">{em}</div><div><h4>{esc(h)}</h4><p>{esc(t)}</p></div></div>'
                    for em, h, t in bc.insights(S))

    # month by month
    mo = S['monthly']
    mvars = [v for v in bc.VARS if v.get('month', True) and v.get('agg') != 'dir' and v['key'] in df]
    cols = []
    for v in mvars:
        if v.get('agg') == 'sum':
            cols.append((f'{v["key"]}_total', f'{v["label"]} total', v))
        else:
            cols.append((f'{v["key"]}_mean', f'{v["label"]} avg', v))
            if v.get('month_range', True):
                cols += [(f'{v["key"]}_min', 'low', v), (f'{v["key"]}_max', 'high', v)]
    cols = [c for c in cols if c[0] in mo]
    mhead = '<th>Month</th><th>Days</th>' + ''.join(f'<th>{esc(l)}</th>' for _, l, _ in cols)
    mrows = ''.join('<tr><td><b>' + esc(r['label']) + f'</b></td><td>{int(r["days_with_data"])}/{int(r["days_in_month"])}</td>'
                    + ''.join(f'<td>{cv(r.get(c, np.nan), v)}</td>' for c, _, v in cols) + '</tr>'
                    for r in mo.to_dict('records')[::-1])

    stale = ''
    if bc.CFG.get('status_note') and age_h > 3:
        stale = f'<div class="banner">{esc(bc.CFG["status_note"])} Last reading: <b>{st["last"]:%b %d, %Y}</b>.</div>'
    elif age_h > 3:
        stale = (f'<div class="banner">📡 This station hasn\'t reported since <b>{st["last"]:%b %d, %Y %I:%M %p}</b> '
                 f'({age_h / 24:.1f} days). It may be down for maintenance — this page catches up automatically once readings resume.</div>')
    if notice:
        stale += ('<div class="banner">⚠️ Part of the latest hourly update didn\'t come through, so the newest readings may be '
                  'missing for a little while. It usually sorts itself out on the next update.</div>')
    dl = ''
    if downloads:
        dl = '<div class="chips" style="margin-top:12px">' + ''.join(
            f'<a class="chip dl" href="{esc(h)}" download>{esc(lbl)}</a>' for lbl, h in downloads) + '</div>'
    rows = [('📍 Position', f'{bc.CFG["mooring_lat"]:.5f}° N, {abs(bc.CFG["mooring_lon"]):.5f}° W'),
            ('🔧 Measures', ', '.join(dict.fromkeys(v['label'].lower() for v in bc.VARS if v['key'] in df and v.get('agg') != 'dir'))),
            ('🕒 Reports', 'every 5 minutes'),
            ('🚀 Data since', f'{st["first"]:%B %d, %Y}')]
    if source_url:
        rows.append(('🔗 Live source', f'<a href="{esc(source_url)}">LI-COR station dashboard</a>'))
    if archive_url:
        rows.append(('🗄️ Full archive', f'<a href="{esc(archive_url)}">daily files on UNE Box</a>'))
    where = ''.join(f'<div class="kv"><span>{k}</span><b>{v}</b></div>' for k, v in rows)
    me = dict(lat=bc.CFG['mooring_lat'], lon=bc.CFG['mooring_lon'], kind=bc.CFG.get('kind', 'wx'), label=bc.SITE_SHORT,
              sub=bc.CFG.get('station_desc', 'UNE monitoring station'))
    mapdata = mapjs.mapdata(me, bc.SISTER_SITES, zoom=11)
    here = {}
    for v in bc.VARS:
        k, ek = v['key'], explain.FOR_KEY.get(v['key'])
        if ek and k in st and 'median' in st[k] and ek not in here and ek != 'solar':
            here[ek] = f'typically {bc.fmt(st[k]["median"], k).split(" (")[0]}; {bc.fmt(st[k]["min"], k).split(" (")[0]} to {bc.fmt(st[k]["max"], k).split(" (")[0]} so far.'
    if 'solar_wm2' in st:
        here['solar'] = f'brightest so far {st["solar_wm2"]["max"]:.0f} W/m².'
    if 'rain_mm' in st:
        here['rain'] = f'{bc.fmt(st["rain_mm"]["total"], "rain_mm")} since {st["first"]:%b %Y}.'
    exp_keys = [explain.FOR_KEY[v['key']] for v in bc.VARS if v['key'] in df and v['key'] in explain.FOR_KEY]
    explain_html = explain.SECTION.format(cards=explain.cards(exp_keys, here))
    emoji = bc.CFG.get('emoji', '🌦️')
    page = TEMPLATE
    has = lambda k: k in figs  # noqa: E731
    for k, val in {
        '%%PLOTLY_TAG%%': f'<script src="{plotly_src}"></script>', '%%FIGS%%': json.dumps(figs, default=str, ensure_ascii=False),
        '%%MAPHEAD%%': mapjs.HEAD, '%%MAPCSS%%': mapjs.CSS, '%%MAPJS%%': mapjs.JS.replace('%%MAPDATA%%', mapdata), '%%LEGEND%%': mapjs.LEGEND,
        '%%EXCSS%%': explain.CSS, '%%EXPLAIN%%': explain_html, '%%WHERE%%': where, '%%SISTERS%%': mapjs.nav_buttons(bc.SISTER_SITES),
        '%%DOWNLOADS%%': dl, '%%NOW_TILES%%': now_tiles, '%%CARDS%%': cards, '%%MHEAD%%': mhead, '%%MROWS%%': mrows, '%%STALE%%': stale,
        '%%DAYS%%': ('<section><h2>📅 Day by day</h2><p class="lede">Each day\'s range (shaded) and average (line); bars are daily totals.</p>'
                     '<div class="card"><div id="days" class="chart"></div></div></section>') if has('days') else '',
        '%%ROSE%%': ('<section><h2>🧭 Where the wind comes from</h2><p class="lede">Each wedge shows how often the wind blows from that '
                     'direction; colours show how strong. Distance from the centre = % of the time.</p>'
                     '<div class="card"><div id="rose" class="chart"></div></div></section>') if has('rose') else '',
        '%%HOWTO%%': ('<li>This page updates itself <b>every hour</b> from the UNE monitoring data service (the same data behind UNE\'s '
                      'ArcGIS dashboards). All times are US Eastern.</li><li>Use the download buttons at the top for CSV files and a spreadsheet. '
                      'Google Sheets: <code>=IMPORTDATA("' + bc.SITE_URL + 'data/daily.csv")</code></li>'
                      + (f'<li>The complete raw archive (one file per day) is on <a href="{esc(archive_url)}">UNE Box</a>.</li>' if archive_url else '')
                      + ''.join(f'<li>{esc(n)}</li>' for n in bc.CFG.get('notes', []))),
        '%%FOOTSRC%%': f'from <a href="{bc.REPO_URL}">{bc.GITHUB_USER}/{bc.GITHUB_REPO}</a> on GitHub',
        '%%SHORT%%': esc(bc.SITE_SHORT), '%%TITLE%%': esc(bc.CFG.get('page_title', f'The {bc.SITE_SHORT} Station')),
        '%%SITE%%': esc(bc.SITE_PHRASE), '%%EMOJI%%': emoji, '%%KINDTXT%%': esc(bc.CFG.get('station_desc', '')),
        '%%LATEST%%': f'{st["last"]:%A, %b %d %Y at %I:%M %p}', '%%GENERATED%%': f'{now:%b %d, %Y %I:%M %p %Z}',
    }.items():
        page = page.replace(k, val)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(page)


def mapjs_compass(deg):
    comp = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    return comp[int((deg % 360 + 11.25) // 22.5) % 16]


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%%SHORT%% Station</title>
<script>/* one units choice for the whole site */
try{const u=localStorage.getItem('une-units'); if(u){ const m=u==='metric'; localStorage.setItem('buoy-unit', m?'m':'ft'); localStorage.setItem('wq-unit', m?'si':'us'); localStorage.setItem('net-unit', m?'si':'us'); }}catch(e){}
document.addEventListener('click',e=>{ const b=e.target.closest&&e.target.closest('#u-si,#u-m,#u-us,#u-ft'); if(b){ try{localStorage.setItem('une-units',(b.id==='u-si'||b.id==='u-m')?'metric':'imperial')}catch(_){} } },true);</script>

%%MAPHEAD%%
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>%%EMOJI%%</text></svg>">
<style>
:root{--bg:#f5f8fa;--card:#ffffff;--ink:#0b0b0b;--ink2:#52514e;--muted:#8a8984;--line:#e3e8ec;--accent:#1c5cab;
--hero1:#24425e;--hero2:#3c7a6a;--chip:#eef4fb;--chip2:#b7d3f6;--warn:#fff4e0;--warnline:#eda100;--grid:#e8ecef}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#111213;--card:#1a1a19;--ink:#ffffff;--ink2:#c3c2b7;
--muted:#8f8e86;--line:#2c2d2e;--accent:#86b6ef;--hero1:#162a3c;--hero2:#24564a;--chip:#23282e;--chip2:#1c5cab;--warn:#2d2616;--warnline:#c98500;--grid:#2a2b2c}}
:root[data-theme="dark"]{--bg:#111213;--card:#1a1a19;--ink:#ffffff;--ink2:#c3c2b7;--muted:#8f8e86;--line:#2c2d2e;--accent:#86b6ef;
--hero1:#162a3c;--hero2:#24564a;--chip:#23282e;--chip2:#1c5cab;--warn:#2d2616;--warnline:#c98500;--grid:#2a2b2c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:0 16px 48px}
header.hero{background:linear-gradient(135deg,var(--hero1),var(--hero2));color:#fff;padding:36px 16px 70px;position:relative;overflow:hidden}
header.hero .wrap{padding-bottom:0}
header h1{margin:0;font-size:clamp(26px,4vw,40px);letter-spacing:-.5px}
header p{margin:6px 0 0;opacity:.88}
.waves{position:absolute;left:0;right:0;bottom:-2px;height:60px}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.btn{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.35);color:#fff;border-radius:999px;padding:6px 14px;cursor:pointer;font:inherit;font-size:14px}
a.btn{text-decoration:none;display:inline-block}
.btn[aria-pressed="true"]{background:#fff;color:#24425e;font-weight:600}
.maptools{display:flex;gap:6px;flex-wrap:wrap;padding:10px 12px}
.seg{background:var(--chip);color:var(--ink);border:1px solid var(--line);border-radius:999px;padding:5px 12px;cursor:pointer;font:inherit;font-size:13px}
.seg[aria-pressed="true"]{background:var(--accent);color:#fff;border-color:var(--accent)}
.kv{display:flex;justify-content:space-between;gap:12px;padding:9px 0;border-bottom:1px solid var(--line);font-size:14px}
.kv span{color:var(--ink2);white-space:nowrap}.kv b{text-align:right}
.mapcard{display:flex;flex-direction:column}
section{margin-top:28px}
h2{font-size:22px;margin:0 0 4px}
.lede{color:var(--ink2);margin:0 0 14px}
.grid{display:grid;gap:12px}
.tiles{grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}
.tile,.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.now{margin-top:-52px;position:relative}
.t-emoji{font-size:26px;line-height:1.1}
.t-label{color:var(--ink2);font-size:13px;margin-top:6px}
.t-value{font-size:28px;font-weight:700;letter-spacing:-.5px}
.t-sub{color:var(--muted);font-size:13px}
a.ti{text-decoration:none;font-size:12px;opacity:.75;margin-left:2px}a.ti:hover{opacity:1}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
a.chip.dl{background:rgba(255,255,255,.14);color:#fff;text-decoration:none;border:1px solid rgba(255,255,255,.35)}
.chip{background:var(--chip);border-radius:999px;padding:3px 10px;font-size:13px;color:var(--ink2)}
.insights{grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr))}
.insight{display:flex;gap:12px}.i-emoji{font-size:28px}
.insight h4{margin:0 0 4px;font-size:15px}.insight p{margin:0;color:var(--ink2);font-size:14px}
.chart{width:100%;min-height:260px}
.two{grid-template-columns:repeat(auto-fit,minmax(min(100%,460px),1fr))}
.banner{background:var(--warn);border-left:4px solid var(--warnline);border-radius:10px;padding:10px 14px;margin-top:16px;color:var(--ink)}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{text-align:left;padding:6px 7px;border-bottom:1px solid var(--line);white-space:nowrap}
th{color:var(--ink2);font-weight:600;font-size:13px;white-space:normal;vertical-align:bottom;line-height:1.25}
.tablewrap{overflow-x:auto}
details{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 16px;margin-top:12px}
summary{cursor:pointer;font-weight:600}
details li{color:var(--ink2);margin:6px 0;font-size:14px}
footer{color:var(--muted);font-size:13px;margin-top:36px}
a{color:var(--accent)}
code{background:var(--chip);padding:1px 5px;border-radius:5px;word-break:break-all}
%%MAPCSS%%
%%EXCSS%%
@media (max-width:560px){.t-value{font-size:24px}.kv{flex-direction:column;gap:2px}.kv b{text-align:left}}
.seggrp{display:inline-flex;align-items:center;gap:8px;margin-right:10px}
.seglbl{font-size:12px;font-weight:700;letter-spacing:.7px;text-transform:uppercase;opacity:.75}
.segctl{position:relative;display:inline-flex;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.3);border-radius:999px;padding:3px}
.segctl button{position:relative;z-index:1;background:none;border:0;color:#fff;font:inherit;font-size:14px;font-weight:600;padding:5px 15px;border-radius:999px;cursor:pointer;opacity:.85;transition:color .2s}
.segctl button[aria-pressed="true"]{color:#14304d;opacity:1}
.segctl .knob{position:absolute;z-index:0;top:3px;bottom:3px;border-radius:999px;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.25);transition:left .25s ease,width .25s ease}
@media (prefers-reduced-motion:reduce){.segctl .knob{transition:none}}
</style></head>
<body>
<header class="hero"><div class="wrap">
  <h1>%%EMOJI%% %%TITLE%%</h1>
  <p>Live conditions %%SITE%% · %%KINDTXT%%</p>
  <div class="toolbar">%%SISTERS%%</div>
  <div class="toolbar">
    <div class="seggrp"><span class="seglbl">Units:</span><div class="segctl" role="group" aria-label="Units"><span class="knob"></span><button id="u-si" aria-pressed="false">Metric</button><button id="u-us" aria-pressed="true">Imperial</button></div></div>
    <div class="seggrp"><span class="seglbl">Theme:</span><div class="segctl" role="group" aria-label="Theme"><span class="knob"></span><button id="th-light" aria-pressed="true">Light</button><button id="th-dark" aria-pressed="false">Dark</button></div></div>
  </div>
  %%DOWNLOADS%%
</div>
<svg class="waves" viewBox="0 0 1200 60" preserveAspectRatio="none" aria-hidden="true">
<path d="M0,30 C150,60 300,0 450,30 C600,60 750,0 900,30 C1050,60 1150,15 1200,30 L1200,60 L0,60 Z" fill="var(--bg)"/></svg>
</header>
<div class="wrap">
  <section class="now" style="margin-top:-44px">
    <div class="grid tiles">%%NOW_TILES%%</div>
    <p class="lede" style="margin-top:10px">🕒 Latest reading: <b>%%LATEST%%</b>. Tap ⓘ on any box to learn what it means.</p>
    %%STALE%%
  </section>

  <section><h2>📍 Where is the station?</h2><p class="lede">This station is highlighted in orange. Hover over any other icon for its name, or click it to visit UNE's nearby buoys and stations.</p>
    <div class="grid two"><div class="card mapcard" style="padding:0;overflow:hidden">
      <div class="maptools"><button class="seg" data-map="street" aria-pressed="true">🗺️ Map</button><button class="seg" data-map="chart" aria-pressed="false">⚓ Nautical chart</button></div>
      <div id="map"></div>%%LEGEND%%</div>
    <div class="card">%%WHERE%%</div></div></section>

  <section><h2>💡 What the data says</h2><p class="lede">Written automatically from the numbers — it changes as new data arrives.</p>
    <div class="grid insights">%%CARDS%%</div></section>

  %%EXPLAIN%%

  <section><h2>📈 Every reading</h2><p class="lede">All measurements on one shared timeline. Use the buttons to zoom to the last day, week or month, or drag across any panel. Click a name in the legend to hide or show it. The bottom strip shows where the wind came from each day: one column per day, one row per compass direction, darker = more of that day.</p>
    <div class="card"><div id="timeline" class="chart"></div></div></section>

  %%DAYS%%
  %%ROSE%%

  <section><h2>🗓️ Month by month</h2><p class="lede">Averages, lows and highs for each month (newest first).</p>
    <div class="card tablewrap"><table><thead><tr>%%MHEAD%%</tr></thead><tbody>%%MROWS%%</tbody></table></div></section>

  <section><details><summary>ℹ️ About this data</summary><ul>%%HOWTO%%</ul></details></section>
  <footer>Generated %%GENERATED%% %%FOOTSRC%%. Data: University of New England School of Marine and Environmental Programs.</footer>
</div>
%%PLOTLY_TAG%%
<script>
const FIGS = %%FIGS%%;
let unit = 'us';
try { unit = localStorage.getItem('wq-unit') || 'us'; } catch (e) {}
const ORIG = JSON.parse(JSON.stringify(FIGS));
const CONV = {temp:c=>c*9/5+32, speed:v=>v*2.23694, rain:v=>v/25.4, len:v=>v*3.28084};
const UNITS = {us:{temp:'°F', speed:'mph', rain:'in', len:'ft'}, si:{temp:'°C', speed:'m/s', rain:'mm', len:'m'}};
function unitKey(){ return unit==='si' ? 'metric' : 'us'; }
function css(v){return getComputedStyle(document.documentElement).getPropertyValue(v).trim();}
function sub(s){ if (typeof s!=='string') return s; const u=UNITS[unit]; return s.replaceAll('TUNIT',u.temp).replaceAll('SUNIT',u.speed).replaceAll('RUNIT',u.rain).replaceAll('LUNIT',u.len); }
function conv(a,f){return Array.isArray(a)? a.map(x=>Array.isArray(x)? conv(x,f) : (x==null? null: f(x))) : a;}
function themed(layout){
  const ink=css('--ink2'), grid=css('--grid');
  const L = Object.assign({}, layout, {paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
    font:{family:'system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif', color:ink, size:13}, hoverlabel:{font:{size:13}}});
  for (const k of Object.keys(L)) if (/^[xy]axis\d*$/.test(k)) {
    L[k]=Object.assign({gridcolor:grid, zerolinecolor:grid, linecolor:grid}, L[k]);
    if (typeof L[k].title === 'string') L[k].title = {text: L[k].title, standoff: 10};
    if (L[k].title) L[k].title.font = Object.assign({size: 12, color: ink}, L[k].title.font || {});
  }
  if (L.polar){L.polar=Object.assign({bgcolor:'rgba(0,0,0,0)'},L.polar); L.polar.angularaxis=Object.assign({gridcolor:grid,linecolor:grid},L.polar.angularaxis); L.polar.radialaxis=Object.assign({gridcolor:grid,linecolor:grid},L.polar.radialaxis);}
  if (L.xaxis && L.xaxis.rangeselector) L.xaxis.rangeselector=Object.assign({bgcolor:css('--chip'),activecolor:css('--chip2'),font:{color:ink}},L.xaxis.rangeselector);
  if (L.legend) L.legend=Object.assign({font:{color:ink}},L.legend);
  return L;
}
%%MAPJS%%
let mapMode='street';
try{ mapMode = localStorage.getItem('buoy-map') || 'street'; }catch(e){}
function render(){
  for (const id of Object.keys(ORIG)){
    const el=document.getElementById(id); if(!el) continue;
    const f=JSON.parse(JSON.stringify(ORIG[id]));
    for (const t of f.data){
      const fn = unit==='us' ? CONV[t.meta] : null;
      if (fn){ t.y=conv(t.y,fn); if (t.customdata) t.customdata=conv(t.customdata,fn); }
      t.hovertemplate=sub(t.hovertemplate); if (t.name) t.name=sub(t.name);
      if (t.type==='heatmap' && t.name==='Wind from' && curTheme()==='dark') t.colorscale=[[0,'rgba(0,0,0,0)'],[0.15,'#1d3a5c'],[0.5,'#3f7fd0'],[1,'#b9d8ff']];
    }
    const L=themed(JSON.parse(sub(JSON.stringify(f.layout))));
    if (L.polar && el.clientWidth < 560){ L.height=600; L.polar.domain={x:[0,1],y:[0.42,1]}; L.legend=Object.assign({},L.legend,{x:0,y:0,yanchor:'bottom'}); }
    try { Plotly.react(el,f.data,L,{responsive:true,displaylogo:false,modeBarButtonsToRemove:['lasso2d','select2d']}); } catch(e){ console.error(id,e); }
  }
  document.querySelectorAll('.cv').forEach(el=>{ const v=parseFloat(el.dataset.v), c=el.dataset.c, d=+(el.dataset.d||1); if(isNaN(v)) return;
    if (unit==='us' && CONV[c]) el.textContent = CONV[c](v).toFixed(c==='rain'? 2 : (c==='len'? 1 : d)) + ' ' + UNITS.us[c];
    else el.textContent = v.toFixed(d) + ' ' + (UNITS.si[c] || el.dataset.u); });
  document.querySelectorAll('[data-map]').forEach(b=>b.setAttribute('aria-pressed', b.dataset.map===mapMode));
  try { renderMap(); } catch(e){ console.error('map', e); }
  document.getElementById('u-us').setAttribute('aria-pressed', unit==='us');
  document.getElementById('u-si').setAttribute('aria-pressed', unit==='si');
}
document.getElementById('u-us').onclick=()=>{unit='us'; try{localStorage.setItem('wq-unit',unit)}catch(e){} render();};
document.getElementById('u-si').onclick=()=>{unit='si'; try{localStorage.setItem('wq-unit',unit)}catch(e){} render();};
function curTheme(){ const r=document.documentElement; return r.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); }
function slideKnobs(){ document.querySelectorAll('.segctl').forEach(g=>{ const on=g.querySelector('button[aria-pressed="true"]'), k=g.querySelector('.knob');
  if(on&&k){ k.style.left=on.offsetLeft+'px'; k.style.width=on.offsetWidth+'px'; } }); }
function syncTheme(){ const t=curTheme(); document.getElementById('th-light').setAttribute('aria-pressed', t==='light'); document.getElementById('th-dark').setAttribute('aria-pressed', t==='dark'); slideKnobs(); }
function setTheme(t){ document.documentElement.dataset.theme=t; try{localStorage.setItem('buoy-theme',t)}catch(e){} syncTheme(); render(); }
document.getElementById('th-light').onclick=()=>setTheme('light');
document.getElementById('th-dark').onclick=()=>setTheme('dark');
new MutationObserver(slideKnobs).observe(document.body,{subtree:true,attributes:true,attributeFilter:['aria-pressed']});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',syncTheme);
window.addEventListener('resize',slideKnobs);
setTimeout(syncTheme,0);
try{const t=localStorage.getItem('buoy-theme'); if(t) document.documentElement.dataset.theme=t;}catch(e){}
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',render);
document.querySelectorAll('[data-map]').forEach(b=>b.onclick=()=>{mapMode=b.dataset.map; try{localStorage.setItem('buoy-map',mapMode)}catch(e){} render();});
render();
</script>
</body></html>
"""
