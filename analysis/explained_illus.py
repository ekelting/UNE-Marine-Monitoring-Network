# illus.py: the chapter illustrations in a paper cut-out style: layered paper shapes with soft shadows,
# paper waves that slide at different speeds, and paper label tabs.
# exec()'d inside explained.py, so it can use R, a, h, mr, so, od, rise_pct, lag, EST_I, STORM_LEVELS.
import math, json

SH = 'filter="url(#sh)"'


def wv(y, amp, wl):
    """A repeating sine edge wider than the canvas (CSS slides it one wavelength for a seamless loop)."""
    k = math.ceil((320 + 2 * wl) / wl) + 1
    return f'M{-wl} {y}' + ''.join(f' q{wl/4:g} {-amp:g} {wl/2:g} 0 q{wl/4:g} {amp:g} {wl/2:g} 0' for _ in range(k))


def paperwave(y, amp, wl, fill, speed=6, depth=400, extra=''):
    """A sliding paper wave. Its shadow is a plain offset copy, not a blur filter, so the animation stays cheap to draw."""
    d = f'{wv(y, amp, wl)} V{y+depth} H{-wl} Z'
    sty = f'--wl:{wl}px;animation-duration:{speed}s'
    return (f'<g transform="translate(0 2.6)"><path class="swell" style="{sty}" d="{d}" fill="var(--pp-shadow)" opacity=".14"/></g>'
            f'<path class="swell" style="{sty}" d="{d}" fill="{fill}" {extra}/>')


def tab(x, y, w, text, anchor='middle', h=22, cls='il-l il-b', tid=''):
    """A paper label tab: a rounded card with a shadow and centred text."""
    x0 = x - w / 2 if anchor == 'middle' else x
    tx = x if anchor == 'middle' else x + 10
    idattr = f' id="{tid}"' if tid else ''
    return (f'<g {SH}><rect x="{x0:.1f}" y="{y - h/2:.1f}" width="{w}" height="{h}" rx="{h/2}" fill="var(--pp-pill)"/></g>'
            f'<text{idattr} x="{tx:.1f}" y="{y + 4:.1f}" text-anchor="{anchor}" class="{cls}" style="fill:var(--pp-pillink)">{text}</text>')


def cloud(x, y, s=1, delay=0):
    return (f'<g class="drift" style="animation-delay:-{delay}s" {SH}><path transform="translate({x} {y}) scale({s})" '
            f'd="M0 12 a10 10 0 0 1 18 -6 a12 12 0 0 1 22 2 a9 9 0 0 1 2 16 h-40 a7 7 0 0 1 -2 -12z" fill="var(--pp-cloud)"/></g>')


def arrow(x1, y1, x2, y2, w=7, head=16, hw=10):
    """A filled paper arrow (no stroke marker, so a shadow filter can't clip its head)."""
    L = math.hypot(x2 - x1, y2 - y1); ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
    p = f'M0 {-w/2} H{L-head} V{-hw} L{L} 0 L{L-head} {hw} V{w/2} H0 Z'
    return f'<g {SH}><path transform="translate({x1} {y1}) rotate({ang:.2f})" d="{p}" fill="var(--pp-accent)" stroke-linejoin="round"/></g>'


def clock(cx, cy, r, kind, dur=None, start=180, hid='', label=''):
    """A paper clock. kind: 'day' (24 h dial, noon at top), 'tide' (one tide per turn), 'hour' (12 h dial).
    With dur, CSS spins the hand once per dur seconds starting at angle start; with hid, script sets it."""
    n = 24 if kind == 'day' else 12
    ticks = ''.join(f'<line x1="{cx + (r-3)*math.sin(2*math.pi*i/n):.1f}" y1="{cy - (r-3)*math.cos(2*math.pi*i/n):.1f}" '
                    f'x2="{cx + (r-(6 if i % (n//4) == 0 else 4.5))*math.sin(2*math.pi*i/n):.1f}" y2="{cy - (r-(6 if i % (n//4) == 0 else 4.5))*math.cos(2*math.pi*i/n):.1f}" '
                    f'stroke="var(--pp-pillink)" stroke-width="{1.4 if i % (n//4) == 0 else .7}" stroke-linecap="round"/>' for i in range(n))
    deco = ''
    if kind == 'day':
        deco = (f'<circle cx="{cx}" cy="{cy - r*.48:.1f}" r="{r*.13:.1f}" fill="var(--pp-sun)"/>'
                f'<path d="M{cx - r*.1:.1f} {cy + r*.36:.1f} a{r*.14:.1f} {r*.14:.1f} 0 1 0 {r*.2:.1f} {r*.2:.1f} a{r*.1:.1f} {r*.1:.1f} 0 1 1 {-r*.2:.1f} {-r*.2:.1f}z" fill="var(--pp-ink2)"/>')
    elif kind == 'tide':
        hi = 2 * math.pi * (start/360 + rise_pct/100)          # where high water falls on the dial
        deco = (f'<text x="{cx}" y="{cy + r*.62:.1f}" text-anchor="middle" class="il-s" style="fill:var(--pp-pillink);font-size:{r*.32:.1f}px">low</text>'
                f'<circle cx="{cx + (r-6)*math.sin(hi):.1f}" cy="{cy - (r-6)*math.cos(hi):.1f}" r="{r*.13:.1f}" fill="var(--pp-w2)"/>'
                f'<text x="{cx + (r+4)*math.sin(hi):.1f}" y="{cy - (r+4)*math.cos(hi):.1f}" text-anchor="{'end' if math.sin(hi) < 0 else 'start'}" class="il-s il-b il-h">high</text>')
    if dur:
        hand_attr = f'class="hand" style="transform-origin:{cx}px {cy}px;--r0:{start}deg;animation-duration:{dur}s"'
    else:
        hand_attr = f'id="{hid}" style="transform-origin:{cx}px {cy}px"'
    lab = f'<text x="{cx}" y="{cy + r + 12}" text-anchor="middle" class="il-s il-b il-h">{label}</text>' if label else ''
    return (f'<g {SH}><circle cx="{cx}" cy="{cy}" r="{r}" fill="var(--pp-pill)"/></g>{ticks}{deco}'
            f'<g {hand_attr}><line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy - r*.72:.1f}" stroke="var(--pp-accent)" stroke-width="2.4" stroke-linecap="round"/></g>'
            f'<circle cx="{cx}" cy="{cy}" r="2.4" fill="var(--pp-pillink)"/>{lab}')


ILL_DEFS = '''<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>
  <filter id="sh" x="-15%" y="-15%" width="130%" height="140%"><feDropShadow dx="0" dy="2.4" stdDeviation="2.1" style="flood-color:var(--pp-shadow);flood-opacity:var(--pp-shadowop)"/></filter>
  <filter id="sh2" x="-15%" y="-15%" width="130%" height="140%"><feDropShadow dx="0" dy="1.2" stdDeviation="1" style="flood-color:var(--pp-shadow);flood-opacity:var(--pp-shadowop)"/></filter>
  <marker id="m-acc" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 Z" fill="var(--pp-accent)"/></marker>
</defs></svg>'''

FRAME = 'class="svg il"'

# ------------------------------------------------------------------ 1. sea level: paper staff on a piling
SEA_SVG = f'''<div class="sl-wrap">
<svg viewBox="0 0 320 260" {FRAME} role="img" aria-label="A tide staff on a pier piling; the water climbs the staff as you drag the year slider. Height is exaggerated six times.">
  <rect width="320" height="260" fill="var(--pp-sky)"/>
  {cloud(28, 24, 1.1)}{cloud(240, 44, .8, 4)}
  <g {SH}><path d="M0 128 C40 104 90 108 130 122 C160 110 190 108 220 122 V150 H0Z" fill="var(--pp-g1)"/>
    <path d="M0 136 C50 120 110 126 170 136 V150 H0Z" fill="var(--pp-g2)"/></g>
  <g {SH}><rect x="198" y="-6" width="34" height="272" rx="3" fill="var(--pp-wood)"/><rect x="172" y="6" width="24" height="260" rx="2" fill="var(--pp-card)"/></g>
  <g id="slsurf">
    <rect id="slwater" x="0" y="300" width="1" height="1" fill="none"/>
    {paperwave(0, 4, 40, 'var(--pp-w1)', 6, extra='opacity=".93"')}{paperwave(10, 4, 52, 'var(--pp-w2)', 8)}{paperwave(24, 3, 34, 'var(--pp-w3)', 5)}
  </g>
  <g id="ruler"></g>
  <line id="sl1912" x1="34" x2="140" y1="0" y2="0" stroke="var(--il-ink)" stroke-dasharray="5 4" stroke-width="1.2"/>
  <text id="sl1912t" x="36" y="0" class="il-l il-b il-h">1912 water level</text>
</svg>
<label class="slider"><span>Year: <b id="slyear">2025</b></span><input id="slr" type="range" min="1912" max="2025" step="1" value="2025" list="slpins"><datalist id="slpins"><option value="1912"></option><option value="1978"></option><option value="2018"></option><option value="2022"></option><option value="2024"></option></datalist></label>
<p class="sl-read" id="slread"></p></div>'''

# ------------------------------------------------------------------ 2. storm tide: Old Orchard Beach Pier
# Vertical scale: 0.6 to 6.1 m above MLLW over 220 px (same mapping as stDraw in gen.py). The pier deck height is approximate
# (about 18 ft above MLLW, roughly 12 to 15 ft above the sand); the sand line slopes from about 7 ft at the shore to 2 ft offshore.
def _yo(m): return 240 - (m - 0.6) / 5.5 * 220
_deck = _yo(18 * 0.3048)
def _sand(x): return _yo(7 * 0.3048) + (_yo(2 * 0.3048) - _yo(7 * 0.3048)) * x / 320
STORM_SVG = f'''<div class="st-wrap">
<svg viewBox="0 0 320 260" {FRAME} role="img" aria-label="The Old Orchard Beach Pier on its pilings over the beach. The water rises to the level you pick; even the record storm tide stays below the deck, though storm waves on top of it reach the pier.">
  <rect width="320" height="260" fill="var(--pp-sky)"/>
  {cloud(200, 12, .9)}{cloud(40, 70, .7, 4)}
  <g {SH}>
    {''.join(f'<rect x="{x}" y="{_deck}" width="7" height="{_sand(x)-_deck+6:.1f}" rx="2" fill="var(--pp-wood2)"/>' for x in range(14, 320, 30))}
    <path d="{' '.join(f'M{x} {_deck+4} L{x+30} {_sand(x+30)-4:.1f} M{x+30} {_deck+4} L{x} {_sand(x)-4:.1f}' for x in range(17, 290, 60))}" stroke="var(--pp-wood2)" stroke-width="2" opacity=".7"/>
    <rect x="-4" y="{_deck-5}" width="330" height="10" rx="2" fill="var(--pp-wood)"/>
    <path d="{' '.join(f'M{x} {_deck-5} v-30' for x in range(10, 320, 30))} M0 {_deck-35} H320 M0 {_deck-22} H320" stroke="var(--pp-wood2)" stroke-width="2.4" stroke-linecap="round" fill="none"/>
  </g>
  <g id="stsurf">
    <rect id="stwater" x="0" y="300" width="1" height="1" fill="none"/>
    {paperwave(0, 4, 40, 'var(--pp-w1)', 6, extra='opacity=".8"')}{paperwave(10, 4, 52, 'var(--pp-w2)', 8, extra='opacity=".75"')}{paperwave(24, 3, 34, 'var(--pp-w3)', 5, extra='opacity=".75"')}
  </g>
  <g {SH}><path d="M0 {_sand(0):.1f} L320 {_sand(320):.1f} V262 H0Z" fill="var(--pp-sand)"/></g>
  <g id="stticks"></g>
  {tab(8, 247, 262, 'Old Orchard Beach Pier (deck height approx.)', anchor='start', h=18, cls='il-s il-b')}
</svg>
<div class="st-btns" id="stbtns"></div><p class="sl-read" id="stread"></p></div>'''

# ------------------------------------------------------------------ 3. sand: Saco Bay from Camp Ellis to Old Orchard Beach
# Real shoreline (OpenStreetMap coastline, jetties and pier; built by sandmap.py), north up, about 34 px per km.
# OSM closes the coastline across the river mouth, so the Saco River channel inside the jetties is hand-traced.
import sandmap as _sandmap  # noqa: E402
_SM = _sandmap.build()
_cx = {int(k): v for k, v in _SM['coast_x'].items()}
_bands = ''.join(f'<path d="M{130+k*30} -40 q-7 11 0 22 t0 22 t0 22 t0 22 t0 22 t0 22 t0 22 t0 22 t0 22 t0 22 t0 22 t0 22 t0 22 t0 22 t0 22 t0 22 V360 H700 V-40Z" fill="var(--pp-{"w2" if k%2 else "w3"})"/>' for k in range(0, 12))
_pt = _SM['pts']
SAND_SVG = f'''<svg viewBox="0 0 320 282" {FRAME} role="img" aria-label="Map of Saco Bay from Biddeford Pool and Camp Ellis north to Old Orchard Beach. Waves arrive from the east and southeast and push sand north along the beach, away from the Camp Ellis jetties.">
  <rect width="320" height="282" fill="var(--pp-w3)"/>
  <g class="crests"><g transform="skewX(14)">{_bands}</g></g>
  <path d="{_SM['beach']}" fill="none" stroke="var(--pp-w1)" stroke-width="16" stroke-linejoin="round" opacity=".9"/>
  <path d="{_SM['beach']}" fill="none" stroke="var(--pp-sand)" stroke-width="7" stroke-linejoin="round"/>
  <g {SH}><path d="{_SM['land']}" fill="var(--pp-g1)"/>{''.join(f'<path d="{p}" fill="var(--pp-g1)"/>' for p in _SM['islands'])}</g>
  <path d="{_SM['river']}" fill="var(--pp-river)"/>
  <g {SH}>{''.join(f'<path d="{p}" fill="var(--pp-rock)" stroke="var(--pp-rock)" stroke-width="3.2" stroke-linejoin="round"/>' for p in _SM['jetties'])}{''.join(f'<path d="{p}" fill="var(--pp-wood)" stroke="var(--pp-wood2)" stroke-width="1.6"/>' for p in _SM['pier'])}</g>
  <g>{''.join(f'<circle r="2.1" fill="var(--pp-grain)"><animateMotion dur="12s" begin="-{i*1:.2f}s" repeatCount="indefinite" path="{_SM['grains']}"/></circle>' for i in range(12))}</g>
  {''.join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.4" fill="var(--pp-buoy)" stroke="var(--pp-ink2)" stroke-width=".8"/>' for x, y in (_SM['buoy'], _pt['wibuoy']))}
  {arrow(_cx[170] + 20, 172, _cx[110] + 18, 110)}
  {arrow(306, 92, 248, 92)}
  {arrow(306, 172, 256, 132)}
  {tab(258, 68, 128, 'waves from E and SE', h=20, cls='il-s il-b')}
  {tab(_cx[140] + 30, 142, 112, 'Sand drifts north', anchor='start', h=20)}
  {tab(124, 174, 148, 'Camp Ellis: loses sand', anchor='start', h=20)}<path d="M128 184 L{_pt['campellis'][0]+2:.1f} {_pt['campellis'][1]:.1f}" stroke="var(--pp-card)" stroke-width="1.5" stroke-dasharray="2 3"/>
  {tab(8, 96, 74, 'Ferry Beach', anchor='start', h=18, cls='il-s il-b')}
  {tab(8, 22, 104, 'Old Orchard Beach', anchor='start', h=18, cls='il-s il-b')}<path d="M112 22 L{_pt['oob'][0]:.1f} {_pt['oob'][1]+4:.1f}" stroke="var(--pp-card)" stroke-width="1.5" stroke-dasharray="2 3"/>
  {tab(8, 152, 70, 'Saco River', anchor='start', h=18, cls='il-s il-b')}
  {tab(8, 222, 66, 'UNE buoy', anchor='start', h=18, cls='il-s il-b')}<path d="M52 213 L{_SM['buoy'][0]-2:.1f} {_SM['buoy'][1]+3:.1f}" stroke="var(--pp-card)" stroke-width="1.5" stroke-dasharray="2 3"/>
  {tab(176, 272, 86, 'Biddeford Pool', h=18, cls='il-s il-b')}
  {tab(270, 190, 74, 'Wood Island', h=18, cls='il-s il-b')}<path d="M250 198 L222 205" stroke="var(--pp-card)" stroke-width="1.5" stroke-dasharray="2 3"/>
  <g transform="translate(294 22)" {SH}><circle r="13" fill="var(--pp-pill)"/><path d="M0 -10 L4 3 L0 1 L-4 3Z" fill="var(--pp-accent)"/><text y="11" text-anchor="middle" class="il-s" style="fill:var(--pp-pillink);font-size:8px">N</text></g>
  <g transform="translate(244 246)"><path d="M0 0 H{_SM['K']*0.0090:.1f}" stroke="var(--pp-card)" stroke-width="3" stroke-linecap="round"/><text x="{_SM['K']*0.0045:.1f}" y="-5" text-anchor="middle" class="il-s il-b il-h">1 km</text></g>
</svg>'''

# ------------------------------------------------------------------ 4. layers: the Camp Ellis mooring in paper bands
_ly = [(50, 112), (112, 168), (168, 226)]
LAYER_SVG = f'''<div class="ly-wrap"><svg viewBox="0 0 320 240" {FRAME} role="img" aria-label="The Camp Ellis mooring with three temperature sensors; each paper band is coloured by that month's average temperature at its depth">
  <defs><linearGradient id="lyg"><stop id="lys1"/><stop id="lys2"/><stop id="lys3"/></linearGradient></defs>
  <rect width="320" height="240" fill="var(--pp-sky)"/>
  <g {SH}><circle cx="150" cy="22" r="11" fill="var(--pp-sun)"/></g>{cloud(30, 10, .9)}
  {''.join(f'<g {SH}><path id="lyb{j+1}" class="lyb" d="{wv(y0, 3 if j == 0 else 2, 44 if j == 0 else 60)} V{y1+6} H-60 Z" style="--wl:{44 if j == 0 else 60}px"/></g>' for j, (y0, y1) in enumerate(_ly))}
  <g {SH}><path d="M0 226 C60 222 120 228 180 224 C240 220 290 226 320 224 V240 H0Z" fill="var(--pp-sand)"/></g>
  <path d="M246 56 V218" stroke="var(--pp-ink2)" stroke-width="1.4"/>
  <g class="bob"><g transform="translate(246 55) scale(1.25) translate(-246 -50)">
    <g {SH}>
      <path d="M239 45 L244 22 M253 45 L248 22 M240.5 36 H251.5" stroke="var(--pp-ink2)" stroke-width="2.4" stroke-linecap="round" fill="none"/>
      <path d="M226 50 C226 40 266 40 266 50 C266 59 226 59 226 50Z" fill="var(--pp-buoy)"/>
      <path d="M227 50 C238 53 254 53 265 50" stroke="var(--pp-accent)" stroke-width="3.4" fill="none"/>
      <rect x="241" y="17" width="10" height="6" rx="2.5" fill="var(--pp-ink2)"/>
    </g>
    <circle class="blink" cx="246" cy="14" r="5" fill="var(--pp-sun)" opacity=".35"/><circle class="blink" cx="246" cy="14" r="3" fill="var(--pp-sun)"/>
  </g></g>
  </g>
  <g {SH}><rect x="237" y="216" width="18" height="10" rx="3" fill="var(--pp-rock)"/>{''.join(f'<rect x="240.5" y="{y-7}" width="11" height="14" rx="4" fill="var(--pp-card)"/>' for y in (82, 138, 194))}</g>
  {''.join(tab(22, y, 196, '', anchor='start', tid=f'lyt{j+1}') for j, y in enumerate((82, 138, 194)))}
</svg><div class="st-btns" id="lybtns"></div><p class="sl-read" id="lyread"></p></div>'''

# ------------------------------------------------------------------ 5. estuary: ocean paper waves slide up the river
# Shoreline traced from a map of the Saco River mouth (north up, about 1 px = 6 m): the river enters from the
# northwest, widens into the basin and leaves past the Camp Ellis jetty; the buoy sits in the cove west of Jordan Point.
_south = 'M0 86 L53 90 L64 102 L90 112 L99 133 L112 131 L121 116 L118 103 L123 100 L127 104 L126 115 L136 114 L160 125 L184 128 L200 126 L216 118 L240 117 L256 115 L288 112 L312 124 L320 127 V204 H0 Z'
_north = 'M50 -2 C66 10 80 22 100 34 C116 40 132 44 150 50 L158 52 L162 47 L167 52 L185 56 L190 52 L198 43 L206 42 L210 52 L214 64 L219 82 L223 84 L240 68 L272 67 L262 54 L232 22 L218 -2 Z'
_west = 'M0 -2 H10 L24 52 L0 62 Z'
_ow = ''.join(f'<path d="M{dx} -10 q-10 12 0 24 t0 24 t0 24 t0 24 t0 24 t0 24 t0 24 t0 24 t0 24 V240 H520 V-10Z" fill="var(--pp-{c})"/>' for dx, c in ((0, 'w1'), (18, 'w2'), (40, 'w3')))
RIVER_SVG = f'''<div class="sl-wrap"><svg viewBox="0 0 320 250" {FRAME} role="img" aria-label="Paper map of the Saco River mouth, north up: the river enters from the northwest, widens past Jordan Point and leaves past the Camp Ellis jetty. Ocean water slides upriver on the rising tide and back out on the falling tide; drag the time slider to play two real days at the UNE buoy in the cove west of Jordan Point.">
  <defs><linearGradient id="estg"><stop id="es1"/><stop id="es2"/></linearGradient></defs>
  <rect width="320" height="204" fill="var(--pp-river)"/>
  <g class="estwaves" {SH}>{_ow}</g>
  <g id="estflow" class="estflow" fill="none" stroke="var(--pp-foam)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity=".8">{''.join(f'<path d="M{x} {y} l6 4.5 l-6 4.5"/>' for x, y in [(150,80),(176,82),(202,92),(232,88),(262,84),(292,86)])}</g>
  <path id="estfront" d="M0 0" stroke="none" fill="none"/>
  <g {SH}>
    <path d="{_south}" fill="var(--pp-g1)"/>
    <path d="M0 120 C40 118 70 130 92 140 L104 150 C150 146 200 140 250 136 C280 134 300 140 320 146 V204 H0Z" fill="var(--pp-g2)"/>
    <path d="{_north}" fill="var(--pp-g1)"/>
    <path d="M232 22 L262 54 L272 67 L264 68 L254 56 L226 24 L214 -2 H220Z" fill="var(--pp-sand)"/>
    <path d="M70 -2 C86 8 104 20 124 28 C150 36 180 34 206 30 L214 -2Z" fill="var(--pp-g2)"/>
    <path d="{_west}" fill="var(--pp-g1)"/>
  </g>
  <g {SH}><rect x="268" y="62" width="30" height="8" rx="4" transform="rotate(-14 268 66)" fill="var(--pp-rock)"/></g>
  <path d="{' '.join(f'M{x} {y} l2 -6 l2 6' for x, y in [(84,20),(96,26),(110,30),(126,34),(140,38),(116,24),(132,28),(150,32),(166,40),(180,36)])}" fill="var(--pp-g1)"/>
  <g class="bob" {SH}><circle cx="106" cy="122" r="6" fill="var(--pp-buoy)" stroke="var(--pp-ink2)" stroke-width=".8"/><circle cx="106" cy="122" r="2" fill="var(--pp-accent)"/></g>
  {tab(54, 172, 72, 'UNE buoy', h=18, cls='il-s il-b')}<path d="M70 163 L102 127" stroke="var(--pp-card)" stroke-width="1.5" stroke-dasharray="2 3"/>
  {tab(160, 146, 74, 'Jordan Point', h=18, cls='il-s il-b')}<path d="M150 137 L126 108" stroke="var(--pp-card)" stroke-width="1.5" stroke-dasharray="2 3"/>
  {tab(46, 70, 66, 'Saco River', h=18, cls='il-s il-b')}
  {tab(232, 12, 64, 'Camp Ellis', h=18, cls='il-s il-b')}
  {tab(296, 36, 46, 'Saco Bay', h=18, cls='il-s il-b')}
  {tab(250, 176, 78, 'UNE campus', h=18, cls='il-s il-b')}
  <g transform="translate(300 186)" {SH}><circle r="11" fill="var(--pp-pill)"/><path d="M0 -8 L3.2 2.4 L0 .8 L-3.2 2.4Z" fill="var(--pp-accent)"/></g>
  <g transform="translate(0 204)"><rect width="320" height="46" fill="var(--pp-pill)"/>
    <text x="312" y="12" text-anchor="end" class="il-s" style="fill:var(--pp-pillink)">more ocean</text><text x="312" y="42" text-anchor="end" class="il-s" style="fill:var(--pp-pillink)">more river</text>
    <path id="estline" fill="none" stroke="var(--pp-w3)" stroke-width="1.8"/>
    <line id="estcur" y1="3" y2="43" stroke="var(--pp-accent)" stroke-width="1.6"/><circle id="estdot" r="4" fill="var(--pp-accent)"/></g>
</svg>
<div class="sl-row"><button type="button" class="playbtn" id="estplay" aria-label="Play the two days">▶</button><label class="slider"><span>Time</span><input id="estr" type="range" min="0" max="48" value="0" step="1"></label></div>
<p class="sl-read" id="estread"></p></div>'''

# ------------------------------------------------------------------ 6. algae: paper plankton dim under the noon sun
def _halton(i, b):
    f, r = 1, 0
    while i > 0:
        f /= b; r += f * (i % b); i //= b
    return r
def _cell(i):
    r = _halton(i + 1, 5)
    x, y = 16 + 288 * _halton(i + 1, 2), 140 + 64 * _halton(i + 1, 3)
    if i % 3 == 0:
        return ''.join(f'<circle cx="{x + k*6.5:.1f}" cy="{y + k*1.5:.1f}" r="3"/>' for k in range(3))
    if i % 3 == 1:
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{3.2 + r*2:.1f}"/>'
    return f'<path d="M{x-6:.1f} {y:.1f} q6 -5 12 0 q-6 5 -12 0 z"/>'
# Algae timing. One loop = one day (10 s), starting at local midnight. Glow and the sensor bar follow the median
# chlorophyll for each hour at Wood Island; the sun follows the average sunrise (6:34), solar noon (12:32) and
# sunset (6:31 pm, EDT) for the sensor record, Sep 12 to Oct 13, at 43.46 N.
_hm = R['chl']['Wood Island']['h_med']; _mx = max(_hm)
_KF = ('@keyframes glowWI{' + ' '.join(f'{h/24*100:.2f}%{{opacity:{0.3+0.7*v/_mx:.3f}}}' for h, v in enumerate(_hm)) + f' 100%{{opacity:{0.3+0.7*_hm[0]/_mx:.3f}}}}}'
       '@keyframes meterWI{' + ' '.join(f'{h/24*100:.2f}%{{transform:scaleX({v/_mx:.3f})}}' for h, v in enumerate(_hm)) + f' 100%{{transform:scaleX({_hm[0]/_mx:.3f})}}}}'
       '.glow{animation-name:glowWI}.meter{animation-name:meterWI}')
_SUN_BEGIN = -(10 - 12.54 / 24 * 10 + 5)   # puts the top of the orbit (noon) at 12:32
ALGAE_SVG = f'''<svg viewBox="0 0 320 240" {FRAME} role="img" aria-label="As the sun crosses the sky, the algae's glow (what the sensor reads) dims at midday and recovers by evening">
  <rect width="320" height="122" class="jsky" fill="var(--pp-sky)"/>
  <g class="jstars" fill="#fff" opacity="0">{''.join(f'<circle cx="{x}" cy="{y}" r="{r}"/>' for x, y, r in [(30,14,1),(80,40,.8),(120,12,1.1),(176,30,.8),(210,8,1),(262,44,.9),(300,20,1),(150,58,.7),(60,70,.7),(240,74,.8)])}</g>
  {cloud(40, 30, .8)}{cloud(220, 18, .7, 5)}
  <g {SH}><g class="jsun" data-orbit="160 124 142 104" transform="translate(160 20)"><circle r="11" fill="var(--pp-sun)"/></g></g>
  <g>{paperwave(118, 3, 40, 'var(--pp-w1)', 6)}{paperwave(126, 3, 52, 'var(--pp-w2)', 8)}{paperwave(140, 2, 34, 'var(--pp-w3)', 5)}</g>
  <g class="jglow" fill="var(--pp-chl)" filter="url(#sh2)">{''.join(_cell(i) for i in range(22))}</g>
  <g {SH}><rect x="8" y="212" width="304" height="22" rx="11" fill="var(--pp-pill)"/></g>
  <text x="20" y="227" class="il-s il-b" style="fill:var(--pp-pillink)">Wood Island sensor</text>
  <rect x="136" y="220" width="164" height="6" rx="3" fill="var(--pp-track)"/><rect x="136" y="220" width="164" height="6" rx="3" fill="var(--pp-chl2)" class="jmeter"/>
</svg>'''

# ------------------------------------------------------------------ 7. marsh: floods in fast, drains slowly
_mud = 'M0 132 C40 130 80 134 108 138 C120 152 126 170 140 176 C152 180 168 180 180 176 C194 170 200 152 212 138 C240 134 280 130 320 132 L320 200 L0 200 Z'
MARSH_SVG = f'''<svg viewBox="0 0 320 200" {FRAME} role="img" aria-label="Paper cross-section of a marsh creek: the tide floods in over {mr['rise']:.1f} hours and drains out over {mr['fall']:.1f} hours">
  <rect width="320" height="200" fill="var(--pp-sky)"/>
  <g class="marshwater">{paperwave(120, 3, 40, 'var(--pp-w1)', 6, 90, 'opacity=".95"')}{paperwave(128, 3, 52, 'var(--pp-w2)', 8, 90)}</g>
  <g {SH}><path d="{_mud}" fill="var(--pp-s1)"/>
    <path d="M0 152 C60 150 100 156 116 162 C126 178 150 190 160 190 C176 190 196 178 206 162 C222 156 260 150 320 152 V200 H0Z" fill="var(--pp-s2)"/>
    <path d="M0 132 C40 130 80 134 108 138 L104 126 C80 120 40 121 0 123Z M212 138 C240 134 280 130 320 132 V123 C280 121 240 120 216 126Z" fill="var(--pp-g2)"/>
    <path d="{' '.join(f'M{x} 130 l3 -12 l3 12' for x in list(range(4, 102, 9)) + list(range(218, 318, 9)))}" fill="var(--pp-g1)"/></g>
  {tab(14, 26, 176, f'Floods in {mr["rise"]:.1f} h · drains {mr["fall"]:.1f} h', anchor='start')}
  <rect x="22" y="44" width="160" height="7" rx="3.5" fill="var(--pp-track)"/><rect x="22" y="44" width="{160*rise_pct/100:.1f}" height="7" rx="3.5" fill="var(--pp-w2)"/>
  <text x="22" y="64" class="il-s il-h">one tide, {mr['rise'] + mr['fall']:.1f} h</text>
  {clock(282, 44, 24, 'tide', dur=12.5, start=180, label='tide clock')}
</svg>'''

# ------------------------------------------------------------------ 8. soil: paper strata with paper thermometers
_A0 = so['amp'][0]
_rows = list(zip([4, 10, 20, 45], [so['amp'][0], so['amp'][1], so['amp'][2], so['amp'][5]], [lag[0], lag[1], lag[2], lag[5]], [72, 106, 142, 196]))
def _therm(y, amp, pk):
    hw = 0.46 * amp / _A0
    delay = ((pk / 24 * 10 - 5) % 10) - 10
    ticks = ''.join(f'<line x1="{x}" y1="{y-5.5}" x2="{x}" y2="{y-3.5}" stroke="var(--pp-pillink)" stroke-width=".7" opacity=".6"/>' for x in range(206, 292, 10))
    return (f'<rect x="192" y="{y-5.5}" width="102" height="11" rx="5.5" fill="var(--pp-card)" stroke="var(--pp-pillink)" stroke-width=".9"/>'
            f'<rect class="jtherm" x="196" y="{y-2.5}" width="94" height="5" rx="2.5" fill="var(--pp-accent)" data-hw="{hw:.3f}" data-pk="{pk:.2f}"/>'
            f'<circle cx="190" cy="{y}" r="8" fill="var(--pp-card)" stroke="var(--pp-pillink)" stroke-width=".9"/><circle cx="190" cy="{y}" r="5.5" fill="var(--pp-accent)"/>'
            f'<rect x="188" y="{y-2.5}" width="10" height="5" fill="var(--pp-accent)"/>' + ticks)
SOIL_SVG = f'''<svg viewBox="0 0 320 230" {FRAME} role="img" aria-label="Paper soil layers: the day's warmth makes the shallow thermometer swing a lot, deeper ones less and later">
  <rect width="320" height="48" class="jsky" fill="var(--pp-sky)"/>
  <g class="jstars" fill="#fff" opacity="0">{''.join(f'<circle cx="{x}" cy="{y}" r="{r}"/>' for x, y, r in [(40,10,1),(96,22,.8),(170,8,1.1),(236,18,.8),(290,9,1),(130,30,.7),(270,34,.7)])}</g>
  <g {SH}><g class="jsun" data-orbit="160 56 142 46" transform="translate(160 12)"><circle r="10" fill="var(--pp-sun)"/></g></g>
  {cloud(150, 6, .7)}
  <g {SH}><rect y="46" width="320" height="184" fill="var(--pp-s1)"/>
    <path d="M0 90 C80 86 160 92 320 88 V230 H0Z" fill="var(--pp-s2)"/><path d="M0 124 C90 120 180 126 320 122 V230 H0Z" fill="var(--pp-s3)"/>
    <path d="M0 170 C80 166 200 172 320 168 V230 H0Z" fill="var(--pp-s4)"/>
    <path d="M0 46 C40 40 80 42 120 44 C180 40 260 42 320 44 V52 H0Z" fill="var(--pp-g2)"/></g>
  {''.join(f'<g {SH}><rect x="14" y="{y-13}" width="292" height="26" rx="13" fill="var(--pp-pill)"/></g>'
           f'<text x="26" y="{y-1}" class="il-l il-b" style="fill:var(--pp-pillink)">{dep} cm</text>'
           f'<text x="26" y="{y+9}" class="il-s" style="fill:var(--pp-pillink);font-size:9px">±<tspan data-dtemp="{amp:.3f}"></tspan> · peaks ~{int(pk)%12 or 12} {"am" if int(pk)%24<12 else "pm"}</text>'
           + _therm(y, amp, pk)
           for dep, amp, pk, y in _rows)}
</svg>'''
