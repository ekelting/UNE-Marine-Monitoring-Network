"""
build.py — builds the Analysis page (site/analysis/index.html) from the station pages already built in
site/ plus the outside records in analysis/ext/.    Usage:  python analysis/build.py --site site
"""
import argparse
import html
import json
import math
import os
import runpy
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cards as CARDS  # noqa: E402
import compute  # noqa: E402

HOME = 'https://ekelting.github.io/UNE-Marine-Monitoring-Network/'


def clean(o):
    if isinstance(o, float):
        return None if not math.isfinite(o) else round(o, 6)
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if hasattr(o, 'item'):
        return clean(o.item())
    return o


def card_html(c, n):
    chips = ''.join(f'<span class="chip">{x}</span>' for x in c['c'])
    found = ('<div class="find"><b class="k">What we found</b><ul>' + ''.join(f'<li>{f}</li>' for f in c['found']) + '</ul></div>') if c['found'] else ''
    if c.get('odelist'):
        found += '<div class="find"><b class="k">Fitted numbers for a model</b><ul id="odelist"></ul></div>'
    read = f'<div class="read"><b class="k">👀 How to read the chart</b>{c["read"]}</div>' if c['read'] else ''
    vk, vl = c['v']
    txt = f'''<div class="txt"><div class="hd"><span class="num">{n}</span><div><h3>{c["t"]}</h3><div class="where">{c["w"]}</div></div></div>
  <div class="chips">{chips}</div><div class="plain"><b class="k">In plain words</b>{c["plain"]}</div>{read}{found}
  <details class="sound"><summary><span class="verdict {vk}">{vl}</span><span>Is this sound?</span></summary><div class="body">{c["math"]}</div></details></div>'''
    viz = ''
    if c.get('timeline'):
        viz += '<ol class="timeline">' + ''.join(f'<li><span class="tl-when">{e["when"]}</span><span class="tl-what">{e["what"]}</span></li>' for e in c['timeline']) + '</ol>'
    if c.get('tiles'):
        viz += '<div class="tiles">' + ''.join(f'<div class="tile"><div class="l">{a}</div><div class="v">{b}</div><div class="s">{s}</div></div>' for a, b, s in c['tiles']) + '</div>'
    if c.get('tabs'):
        viz += ('<div class="tabs" role="group" aria-label="Measurement"><button type="button" data-v="sal_psu" aria-pressed="true">Salinity</button>'
                '<button type="button" data-v="temp_c" aria-pressed="false">Temperature</button><button type="button" data-v="do_mgl" aria-pressed="false">Oxygen</button></div>')
    for cid, cls in c['charts']:
        viz += f'<div id="{cid}" class="plot {cls}"></div>'
    if c.get('table'):
        viz += f'<div class="tblwrap"><table class="stats" id="{c["table"]}"></table></div>'
    if c.get('calc'):
        k = c['calc']
        viz += f'''<div class="calc" id="calc">
    <label for="c-w">Channel width (m) <span class="tag">guess</span></label><input id="c-w" type="number" value="150" step="10" min="1">
    <label for="c-h">Mean depth (m) <span class="tag">guess</span></label><input id="c-h" type="number" value="3" step="0.5" min="0.1">
    <label for="c-u">Peak tidal current (m/s) <span class="tag">guess</span></label><input id="c-u" type="number" value="0.5" step="0.05" min="0.01">
    <label for="c-q">River flow at the mouth (m³/s) <span class="tag m">USGS × 1.3</span></label><input id="c-q" type="number" value="{k["q"]:.1f}" step="1" min="0.1">
    <label for="c-s">Average salinity at Jordan Point (PSU) <span class="tag m">measured</span></label><input id="c-s" type="number" value="{k["s"]:.1f}" step="0.5">
    <label for="c-ds">Salinity swing per tide (PSU) <span class="tag m">measured</span></label><input id="c-ds" type="number" value="{k["ds"]:.1f}" step="0.5">
    <label for="c-so">Ocean salinity (PSU) <span class="tag m">Wood Island</span></label><input id="c-so" type="number" value="{k["so"]:.1f}" step="0.5">
  </div><div class="tblwrap"><table class="stats" id="calcout"></table></div>'''
    if c['cap']:
        viz += f'<p class="cap">{c["cap"]}</p>'
    if c.get('src'):
        viz += f'<p class="src">Data: {c["src"]}</p>'
    return f'<article class="opt" id="a{n}">{txt}<div class="viz">{viz}</div></article>'


GLOSSARY = [('PSU', 'Practical salinity units: about grams of salt per kilogram of water. The ocean here is about 32; river water is 0.'),
            ('MLLW', 'Mean lower low water: the average lowest tide of each day. Water levels are measured up from it.'),
            ('Correlation (r)', 'How closely two things rise and fall together: 1 = in perfect step, 0 = unrelated, −1 = opposite.'),
            ('p-value', 'How surprising a difference would be if there were no real difference. Small (under 0.05) suggests a real difference, but only if the test\'s assumptions hold.'),
            ('Autocorrelation', 'When each reading is similar to the one before it. It makes data look like more evidence than they are.'),
            ('Return period', '"1-in-10-year" means a 10% chance in any given year, not once every 10 years like clockwork.'),
            ('Tidal constituent', 'One of the regular "beats" (M2 = main lunar, twice a day; K1 = daily) that add up to the tide.'),
            ('Littoral drift', 'Sand carried along the shore by waves that arrive at an angle.'),
            ('Shields number', 'The push of moving water on a sand grain compared with the grain\'s weight. Above a critical value, sand moves.'),
            ('Storm surge', 'Extra water height caused by wind and low pressure, on top of the predicted tide.'),
            ('Significant wave height', 'The average height of the biggest third of waves, close to what an observer would call "the wave height".'),
            ('Stratification', 'Layering: lighter (warmer or fresher) water floating on heavier water below.'),
            ('Chlorophyll', 'The green pigment in algae. More chlorophyll means more microscopic algae (phytoplankton) in the water.')]


def page(R, plotly_src):
    cards = CARDS.build(R)
    body, audit, n = [], [], 0
    for gk, gname, gnote in CARDS.GROUPS:
        grp = [c for c in cards if c['g'] == gk]
        if not grp:
            continue
        body.append(f'<h2 class="group" id="g-{gk}">{gname}</h2>' + (f'<p class="lede">{gnote}</p>' if gnote else ''))
        audit.append(f'<tr class="grp"><th colspan="3"><a href="#g-{gk}">{gname}</a></th></tr>')
        for c in grp:
            n += 1
            body.append(card_html(c, n))
            vk, vl = c['v']
            audit.append(f'<tr><td>{n}</td><td><a href="#a{n}">{c["t"]}</a></td><td><span class="verdict {vk}">{vl}</span></td></tr>')
    css = open(os.path.join(HERE, 'style.css')).read()
    js = open(os.path.join(HERE, 'page.js')).read().replace('%%DATA%%', json.dumps(clean(R), separators=(',', ':'), allow_nan=False))
    skipped = R.get('_errors') or {}
    note = (f'<p class="src">Not shown this update (data unavailable): {html.escape(", ".join(skipped))}.</p>' if skipped else '')
    gloss = ''.join(f'<div><b>{a}</b>{b}</div>' for a, b in GLOSSARY)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Analysis · UNE Marine Monitoring Network</title>
<meta name="description" content="Plain-language analyses of UNE's ocean, estuary, weather and soil stations in Saco Bay, compared with long NOAA and USGS records.">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📊</text></svg>">
<script src="{plotly_src}"></script>
<style>{css}
.hdr-nav{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}}
.hdr-nav a{{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.35);color:#fff;border-radius:999px;padding:5px 13px;font-size:14px;text-decoration:none}}
</style></head><body>
<header><div class="wrap">
  <nav class="hdr-nav"><a href="{HOME}">🗺️ All UNE stations</a><a href="{HOME}saco-bay/">🌊 Saco Bay, explained</a></nav>
  <h1>📊 What the data say</h1>
  <p>Analyses of the network's stations, side by side with long public records from NOAA and USGS. Every card starts in plain words, with a tip on how to read the chart; the math and its assumptions are under "Is this sound?". Updated daily.</p>
  <div class="toolbar">
    <span>Units:</span><div class="segctl" role="group" aria-label="Units"><button id="u-si" type="button">Metric</button><button id="u-us" type="button">Imperial</button></div>
    <span>Theme:</span><div class="segctl" role="group" aria-label="Theme"><button id="th-light" type="button">Light</button><button id="th-dark" type="button">Dark</button></div>
  </div>
</div></header>
<main class="wrap">
<section class="overview">
 <div><h2>How sure are we?</h2>
  <p>Each card has a badge:</p>
  <ul><li><span class="verdict ok">✓ Solid</span> the method fits the data and the result holds up.</li>
   <li><span class="verdict care">⚠ Use with care</span> fine to look at, but it rests on an assumption or a short record. The card says which.</li></ul>
  <p style="margin-top:10px">Our own stations started between late 2025 and 2026, so most of their results cover months, not years. They will firm up as records grow.</p>
  {note}
 </div>
 <div><h2>All {n} analyses</h2><div class="tblwrap"><table class="audit">{"".join(audit)}</table></div></div>
</section>
{"".join(body)}
<h2 class="group">Words used on this page</h2><div class="gloss">{gloss}</div>
<footer>Updated {R.get("_built", "")} (US Eastern). Sources: UNE stations (this website); NOAA CO-OPS tide gauge 8418150 (Portland); NOAA NDBC buoy 44007; NOAA GHCN-Daily, Portland Jetport; USGS 01066000 (Saco River at Cornish). Recent NOAA and USGS values are provisional. Not for navigation.</footer>
</main>
<script>{js}</script>
</body></html>'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', default=os.path.join(compute.ROOT, 'site'))
    a = ap.parse_args()
    print('📊 Building the Analysis page')
    R = compute.run(a.site)
    try:
        import plotly
        src = f'https://cdn.jsdelivr.net/npm/plotly.js-dist-min@{plotly.__version__ and __import__("plotly.offline").offline.get_plotlyjs_version()}/plotly.min.js'
    except Exception:  # noqa: BLE001
        src = 'https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js'
    out = os.path.join(a.site, 'analysis')
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'index.html'), 'w').write(page(R, src))
    print(f'✅ Analysis page built ({len(R) - 3} analyses, {len(R.get("_errors") or {})} skipped)')
    # Saco Bay, explained: the public-friendly companion, built from the same results
    try:
        Rj = json.loads(json.dumps(clean(R), allow_nan=False))
        js = open(os.path.join(HERE, 'page.js')).read()
        html_out = runpy.run_path(os.path.join(HERE, 'explained.py'), init_globals={'R': Rj, 'JS': js, 'PLOTLY': src, 'HERE': HERE})['page']
        out2 = os.path.join(a.site, 'saco-bay')
        os.makedirs(out2, exist_ok=True)
        open(os.path.join(out2, 'index.html'), 'w').write(html_out)
        print('✅ Saco Bay, explained built')
    except Exception:  # noqa: BLE001  (never let it take down the Analysis page)
        traceback.print_exc()
        print('::warning::Saco Bay, explained failed to build; its previous version is not updated this hour')


if __name__ == '__main__':
    main()
