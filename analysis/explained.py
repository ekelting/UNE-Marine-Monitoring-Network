"""explained.py: builds "Saco Bay, explained" (site/saco-bay/index.html), the public-friendly companion to the Analysis page.

Run by build.py with the same analysis results R (already JSON-clean) and the shared chart code in page.js:
    runpy.run_path('explained.py', init_globals={'R': R, 'JS': page_js, 'PLOTLY': plotly_src, 'HERE': this_dir})['page']
Seven question chapters; each opens in a quick look and has an Explore button for the charts and the math.
The drawings are in explained_illus.py and the styles in explained.css.
"""
import json, math, os, sys
sys.path.insert(0, HERE)

def L(m): return f'<span data-len="{m:.3f}"></span>'
def dT(c): return f'<span data-dtemp="{c:.2f}"></span>'
def T(c): return f'<span data-temp="{c:.2f}"></span>'

m, a, s, h, f, d, sh = R['msl'], R['amax'], R['sst'], R['head'], R['flow'], R['drift'], R['shields']
ch, mr, so, cu, od, an, sg, ai, st = R['chl'], R['marsh'], R['soil'], R['currents'], R['ode'], R['anova'], R['surge'], R['air'], R['strat']
W, J = ch['Wood Island'], ch['Jordan Point']
DIRS = ['north','north-northeast','northeast','east-northeast','east','east-southeast','southeast','south-southeast','south','south-southwest','southwest','west-southwest','west','west-northwest','northwest','north-northwest']



def chap(cid, emoji, color, q, answer, sub, illus, facts, lvl2, lvl3):
    facts_html = ''.join(f'<li>{x}</li>' for x in facts)
    return f'''<section class="chap" id="{cid}" style="--c:var({color})">
  <div class="chap-top">
    <div class="chap-txt">
      <div class="chap-q"><span class="bubble">{emoji}</span><h2>{q}</h2></div>
      <p class="answer">{answer}</p>
      <p class="sub">{sub}</p>
      <ul class="facts">{facts_html}</ul>
    </div>
    <figure class="illus">{illus}</figure>
  </div>
  <div class="xbar">
    <button type="button" class="xbtn" aria-expanded="false" aria-controls="{cid}-x"><span class="xi">🔍</span><span><b>Explore</b><small>the data, the math and the caveats</small></span><span class="chev" aria-hidden="true"></span></button>
  </div>
  <div class="more" id="{cid}-x">
  <div class="lvl2" id="{cid}-x2">{lvl2}</div>
  <div class="lvl3" id="{cid}-x3"><div class="deep-h"><span>🧪</span> The math and the caveats</div>{lvl3}</div>
  </div>
</section>'''

def chart(cid, title, how, cls=''):
    return f'<div class="chart-card"><h3>{title}</h3><p class="how"><b>How to read it:</b> {how}</p><div id="{cid}" class="plot {cls}"></div></div>'

def math_box(title, body):
    return f'<details class="mathbox"><summary>{title}</summary><div>{body}</div></details>'

# ---------------------------------------------------------------- illustrations
STORM_LEVELS = [('Ordinary high tide', a['mhhw']), (f'This year\'s highest ({h["hw_t"].split(",")[0]})', h['hw']),
                ('1-in-10-year storm', a['rl']['10']), ('1-in-100-year storm', a['rl']['100']), (f'Record ({a["top"][0][0]})', a['top'][0][1])]
# Estuary scene: a real 48 h of hourly salinity at Jordan Point drives where the ocean/river boundary sits.
from datetime import datetime, timedelta
_rt, _rv = od['rawt'], od['raw']
def _win():
    for i in range(len(_rv) - 49, -1, -1):
        w = _rv[i:i + 49]; ts = [datetime.fromisoformat(x) for x in _rt[i:i + 49]]
        if all(x is not None for x in w) and all((ts[k + 1] - ts[k]) == timedelta(hours=1) for k in range(48)):
            return i
    return max(0, len(_rv) - 49)
EST_I = _win()
EST_LO, EST_HI = min(_rv[EST_I:EST_I + 49]), max(_rv[EST_I:EST_I + 49])
rise_pct = mr['rise'] / (mr['rise'] + mr['fall']) * 100

lag = so['peak']
exec(open(os.path.join(HERE, 'explained_illus.py')).read())

# ---------------------------------------------------------------- chapters
topstorm = d['ranking'][0]
chs = [
 chap('c-sea', '🌊', '--sea', 'Is the sea rising?', f'Yes: about {L(m["rise"])} since 1912.',
      f'And it\'s speeding up. Over the last 30 years it rose about {m["slope30"]/m["slope"]:.1f}× faster than the century average.',
      SEA_SVG,
      ['NOAA has measured the tide in Portland every month since 1912. That long record makes this one of our surest answers.',
       'Every high tide and every storm now starts from higher water, which is a big reason beaches and dunes erode.',
       f'The 2024 record storm beat the Blizzard of \'78 by about 5 inches, and roughly {R["msl"]["slope"]*(2024.04-1978.10)/((14.57-14.17)*0.3048)*100:.0f}% of that was just the higher sea.',
       f'At 12 ft, the National Weather Service\'s minor flood level, low wharves and side streets near Portland Pier start to flood. Before 1950 that happened {"less than one day" if R["flood"]["first"]<1 else str(round(R["flood"]["first"]))+" days"} a year; over the last ten years it averaged about {R["flood"]["last"]:.0f} days a year.'],
      chart('pmsl', 'Sea level at Portland, 1912 to today', 'each dot is one year\'s average, measured as how much higher it was than in 1912. The orange line is the long-term trend.')
      + chart('pflood', 'Flooding is becoming routine', 'each bar is a year: the days the water reached 12 ft, the level at which low wharves near Portland Pier start to flood. Orange steps are decade averages.') + chart('psame', 'Same storm, higher sea: 1978 vs 2024', 'the 2024 record beat the Blizzard of \'78 by this much. Blue is how much the sea itself rose in between.', 'xs'),
      math_box('How we measured it', f'<p>Yearly averages of NOAA monthly mean sea level at Portland (station 8418150), with a straight-line trend: {m["slope"]*1000:.2f} ± {m["ci"]*1000:.2f} mm per year (95% range, widened because one year is related to the next). Last 30 years: {m["slope30"]*1000:.1f} ± {m["ci30"]*1000:.1f} mm per year.</p>')),
 chap('c-storm', '⛈️', '--accent', 'How high can the water get?', f'The record is {L(a["top"][0][1])}, in {a["top"][0][0]}.',
      f'That\'s {L(a["top"][0][1]-a["mhhw"])} above an ordinary high tide. Tap the buttons to see how high different events reach.',
      STORM_SVG,
      [f'Surprise: this year\'s highest water ({h["hw_t"]}) wasn\'t a storm. It was mostly a <b>king tide</b>, when the Moon and Sun line up, plus a few inches of extra water.',
       f'The biggest storm surge this year was {L(sg["max"])} of extra water, on {sg["tmax"]}.'],
      chart('pamax', 'Highest water each year since 1912', 'each dot is one year\'s highest water, adjusted to today\'s sea level. Big orange dots reached the "1-in-10-year" level.'),
      chart('psurge', 'Storm surge over the past year', 'how far above or below the tide tables the water ran (daily average). Orange bands are storms at Camp Ellis.')
      + math_box('How we measured it', f'<p>Generalized extreme value fit to the highest water of each year at Portland, shifted to today\'s sea level. "1-in-100-year" means a 1% chance in any year, not once a century. 100-year level {a["rl"]["100"]:.2f} m above MLLW (likely range {a["ci100"][0]:.2f}–{a["ci100"][1]:.2f}). Surge = measured water minus NOAA\'s predicted tide.</p>')),
 chap('c-temp', '🌡️', '--accent', 'Was it a warm year or a cold one?', f'The sea ran a little warm: about {dT(s["meanan"])} above normal.',
      f'Off Portland, the warmest months compared with normal were {s["warm"][0][0]} and {s["warm"][1][0]}. The Gulf of Maine has warmed about {dT(s["slope"]*10)} per decade since 1990.',
      LAYER_SVG,
      [f'🏊 <b>{h["swim"]} swim days</b> at Camp Ellis (water at least {T(18.3)}), from {h["swim_first"]} to {h["swim_last"]}.',
       f'🦞 <b>{h["lob"]} hours</b> warm enough to stress lobsters (above {T(20)}).',
       f'In summer the sea forms layers, warm on top and cold below, like oil on vinegar. Pick a month above to see it.'],
      chart('psst', 'Sea temperature vs normal', 'the grey band is a normal range for each date. Above the band means unusually warm.'),
      chart('psstyr', 'The Gulf of Maine is warming', 'one stripe per year at NOAA buoy 44007: blue cooler and red warmer than the 1991–2020 average. Gaps are years with too little data.', 'xs')
      + chart('pair', 'Air temperature vs normal', 'each bar is a week: red was warmer than normal, blue colder.')
      + chart('pstrat', 'Layers in the sea at Camp Ellis', 'the shaded area is how much warmer the top is than the bottom. Big gap = layered; near zero = mixed.')
      + math_box('How we measured it', '<p>Normal = 1991–2020 average for each date at NOAA buoy 44007 (±5 days, smoothed); band = 10th–90th percentile. Marine heatwave test: Hobday et al. (2016). Layers from the three sensors on the Camp Ellis mooring.</p>')),
 chap('c-sand', '🏖️', '--sand', 'Where does the sand go?', 'North, away from Camp Ellis.',
      'Waves at Camp Ellis roll in from the east and southeast, a little south of straight on for this beach, so they push sand north along the shore like a slow conveyor belt. The jetty blocks new sand from the Saco River, so Camp Ellis loses sand while beaches to the north gain it.',
      SAND_SVG,
      [f'This matches decades of geology in Saco Bay: Pine Point has grown while Camp Ellis has eroded.',
       f'Storms do most of the work: they were only {d["storm_hours"]:.0f}% of the hours but moved about {d["storm_share_k"]:.0f}% of the sand.',
       f'The busiest single storm ({topstorm[0]}) moved about {topstorm[1]/d["total"]*100:.0f}% of the whole year\'s sand by itself.',
       f'Out on the seabed near the buoy, the sand only moves about {sh["move"]:.0f}% of the time, mostly in winter storms.'],
      '<div class="chart-card"><h3>Camp Ellis through time</h3><p class="how">Why the sand matters here: the jetty cut the beach off from the river\'s sand, and waves keep carrying sand north.</p><ol class="timeline">'+''.join(f'<li><span class="tl-when">{e["when"]}</span><span class="tl-what">{e["what"]}</span></li>' for e in R['events']['camp_ellis'])+'</ol><p class="how" style="margin-top:10px">Sources: <a href="https://seagrant.umaine.edu/resource/brief-history-of-camp-ellis-2019">UMaine Sea Grant</a>, <a href="https://themainemonitor.org/unstoppable-ocean-saco">Maine Monitor</a>, <a href="https://gsa.confex.com/gsa/2006NE/webprogram/Paper100969.html">Kelley et al. 2006</a>.</p></div>' +       chart('pdrose', 'Where the wave energy comes from', 'the yellow line is the beach. Dark petals show where waves come from; petals in the blue half push sand north.', 'tall'),
      chart('pdmonth', 'Sand pushed along the beach, month by month', 'bars above the line are sand pushed north (thousands of cubic metres).')
      + chart('pdstorm', 'Which storms moved the most sand', 'storms ranked by how much sand they pushed north; the share of the year is on each bar.')
      + chart('p13', 'Running total of sand moved', 'the line climbs in steps; each step is a storm (orange bands).', 'sm')
      + chart('p14', 'When does the seabed move?', 'each bar is a month: the share of hours waves were strong enough to roll fine sand on the seabed 12 m down.')
      + chart('p15', 'Where the bottom water drifts', 'the path a drop of dye would take if carried by the measured bottom current, out where the buoy sits (offshore of the surf zone). Near the bottom the water drifts slowly south, the opposite of the sand near shore: in a bay, deep water often returns the other way.')
      + chart('p13b', 'Why the beach angle matters', 'the yearly amount for different beach directions (above zero = north). The dotted line is Camp Ellis; the answer flips if the beach faced east or further south.', 'sm')
      + math_box('How we measured it', f'<p>Each hour, waves from the Camp Ellis buoy are bent and steepened toward shore (linear wave theory, straight depth contours) until they break, then fed into two standard sand-transport formulas (CERC and Kamphuis). The beach from the jetty to Ferry Beach faces about {R["cfg"]["normal"]}° (east-northeast). Potential transport there: about {abs(d["k_here"])/1000:.0f} thousand m³ per year to the north (Kamphuis). The direction would flip for a beach facing more than {d["flip"]:.0f}°, so farther north, where the shore turns toward the east-southeast, this single buoy can\'t say. Seabed movement uses the Shields number for 0.2 mm sand.</p>')),
 chap('c-river', '🏞️', '--sea', 'Where does the river meet the sea?', 'Right at our Jordan Point buoy, and the meeting place moves twice a day.',
      'Every rising tide pushes ocean water up the Saco; every falling tide the river pushes it back out. Press play to watch two real days at Jordan Point.',
      RIVER_SVG,
      [f'In those two days the water at the buoy went from about {EST_LO/od["S_ocean"]*100:.0f}% ocean water to {EST_HI/od["S_ocean"]*100:.0f}%, and back, every tide.',
       f'A typical tide swings the saltiness by about {od["med_swing"]:.0f} units: from half river water to nearly pure ocean in about six hours.',
       f'The bigger the tide, the further the ocean reaches: tides explain {od["r_sc"]**2*100:.0f}% of how big each day\'s swing is.',
       f'The Saco has been running low, about {f["last60"]:.0f}% of normal lately, and less river water lets the sea reach further upstream.'],
      chart('pflow', 'Saco River flow vs normal', 'the dashed line at 100% is normal for the date. The shaded strip is less than half of normal.')
      + chart('pmap', 'Where is the water salty?', 'each buoy is coloured by its average saltiness over the last 30 days: darker = saltier ocean water.', 'map') + chart('p3', 'Tide clock: salinity hour by hour', 'each row is a day. Dark = salty ocean water. The dark bands slide right because high tide comes ~50 minutes later each day.', 'tall'),
      chart('p10b', 'Saltiness at Jordan Point, day by day', 'daily average. It drops when the river rises after rain.', 'sm')
      + chart('p10q', 'Saco River flow', 'daily flow at Cornish (USGS).', 'xs')
      + chart('p18', 'Bigger tides, bigger swings', 'each dot is a day; bigger tides slide saltier water past the sensor.')
      + chart('p17', 'A simple salinity model', 'dotted line: a one-equation model driven by river flow and tides.')
      + '<div class="chart-card"><h3>Are the four water-quality buoys really different?</h3><p class="how"><b>How to read it:</b> each dot is how different two buoys are on average; its line is the range we are confident in. Lines crossing the dark zero line mean we can\'t say they differ yet.</p><div class="tabs" role="group" aria-label="Measurement"><button type="button" data-v="sal_psu" aria-pressed="true">Salinity</button><button type="button" data-v="temp_c" aria-pressed="false">Temperature</button><button type="button" data-v="do_mgl" aria-pressed="false">Oxygen</button></div><div id="p8" class="plot"></div><div class="tblwrap"><table class="stats" id="t8"></table></div></div>'
      + f'''<div class="chart-card"><h3>Estuary mixing calculator</h3><p class="how"><b>How to use it:</b> green values are measured; orange are guesses until the channel is surveyed.</p><div class="calc" id="calc">
    <label for="c-w">Channel width (m) <span class="tag">guess</span></label><input id="c-w" type="number" value="150" step="10" min="1">
    <label for="c-h">Mean depth (m) <span class="tag">guess</span></label><input id="c-h" type="number" value="3" step="0.5" min="0.1">
    <label for="c-u">Peak tidal current (m/s) <span class="tag">guess</span></label><input id="c-u" type="number" value="0.5" step="0.05" min="0.01">
    <label for="c-q">River flow at the mouth (m³/s) <span class="tag m">USGS × 1.3</span></label><input id="c-q" type="number" value="{od["Q30"]*1.3:.1f}" step="1" min="0.1">
    <label for="c-s">Average salinity at Jordan Point <span class="tag m">measured</span></label><input id="c-s" type="number" value="{od["S_mean"]:.1f}" step="0.5">
    <label for="c-ds">Salinity swing per tide <span class="tag m">measured</span></label><input id="c-ds" type="number" value="{od["med_swing"]:.1f}" step="0.5">
    <label for="c-so">Ocean salinity <span class="tag m">Wood Island</span></label><input id="c-so" type="number" value="{od["S_ocean"]:.1f}" step="0.5">
  </div><div class="tblwrap"><table class="stats" id="calcout"></table></div></div>'''
      + '<ul id="odelist" class="mathlist"></ul>'),
 chap('c-algae', '🦠', '--kelp', 'Is there algae in the water?', 'A little, and it\'s at healthy, low levels.',
      'Our sensors measure chlorophyll, the green pigment in microscopic algae. One fun twist: in bright sun, algae "squint" and glow less, so the sensor reads low at noon.',
      ALGAE_SVG,
      [f'At midday the reading drops to about {W["ratio"]*100:.0f}% of the night-time value at Wood Island. The algae haven\'t gone anywhere.',
       f'Night-time levels were "low" on NOAA\'s scale on {W["cls"][0]} of {W["nn"]} nights at Wood Island and {J["cls"][0]} of {J["nn"]} at Jordan Point; never high.',
       'At Jordan Point the saltiest water carried the most algae, so this fall the algae rode in from the bay.'],
      chart('pchlday', 'The midday "dip"', 'typical chlorophyll for each hour of the day. The yellow band is midday sun.'),
      chart('pchlnight', 'Algae night by night', 'one dot per night. Green strip = NOAA "low", yellow = "medium".') + chart('pchlsal', 'Ocean water or river water?', 'each box is Jordan Point\'s night-time chlorophyll for water of a given saltiness; boxes further right are saltier.')),
 chap('c-land', '🌾', '--kelp', 'What about the marsh, the woods and the wind?', 'The marsh breathes with the tide, and the forest soil breathes with the sun.',
      f'Water floods into Biddeford Pool Marsh faster than it drains out, which helps the marsh trap mud and keep up with rising seas. In the woods, each day\'s warmth sinks into the soil and fades.',
      '<div class="pair">' + MARSH_SVG + SOIL_SVG + '</div>',
      [f'The tide explains {mr["r2"]*100:.0f}% of the marsh\'s water level; the rest is weather.',
       f'A day\'s warmth takes about {so["lag10"]:.1f} hours to sink each 10 cm into the soil, and is almost gone by 45 cm.'],
      chart('p1', 'The marsh\'s tide, measured vs predicted', 'solid = measured water; dotted = the tide predicted from Moon and Sun alone.') + chart('p5', 'The daily heat pulse in the soil', 'each row is a depth. Red = warmer than that depth\'s daily average. Follow a red patch down: it fades and arrives later.'),
      chart('p1b', 'The tide\'s "beats"', 'how strong each regular tidal rhythm is in the marsh.', 'sm') + chart('pwrose', 'Where does the wind come from?', 'each petal points to where the wind comes from; longer = more often, darker = stronger.')
      + chart('p11', 'Does the radar agree with the wind?', 'grey dots are single scans; the orange line is the typical roughness at each wind speed.')),
]

TILES = [('c-sea', '🌊', 'Is the sea rising?', f'+{L(m["rise"])} since 1912'), ('c-storm', '⛈️', 'How high can the water get?', f'Record {L(a["top"][0][1])}'),
         ('c-temp', '🌡️', 'Warm year or cold?', f'Sea {dT(s["meanan"])} warmer'), ('c-sand', '🏖️', 'Where does the sand go?', 'North, away from Camp Ellis'),
         ('c-river', '🏞️', 'Where river meets sea', 'The ocean flows in twice a day'), ('c-algae', '🦠', 'Is there algae?', 'Low, healthy levels'),
         ('c-land', '🌾', 'Marsh, woods & wind', 'Breathing with tide & sun')]
tiles = ''.join(f'<a class="qtile" href="#{c}"><span class="qe">{e}</span><span class="qq">{q}</span><span class="qa">{ans}</span></a>' for c, e, q, ans in TILES)

CSS = open(os.path.join(HERE, 'explained.css')).read()
EXTRA_JS = r'''
// ---------- one shared day clock for every scene with a sun (algae and soil): 10 s = 24 h, starting at midnight.
// Sun, sky, stars, the algae glow and sensor bar, and the soil thermometers are all computed from the same moment,
// so they cannot drift apart. Sun times are the averages for the sensor record (Sep 12 - Oct 13) at 43.46 N.
const DAY_MS=10000, SOLAR_NOON=12.54, HM=R.chl['Wood Island'].h_med, HMX=Math.max(...HM);
let dayT0=performance.now();
const daySvgs=[...document.querySelectorAll('svg.il')].filter(s=>s.querySelector('.jsun'));
const dayVisible=new Set(daySvgs);
const hex=c=>{ c=c.trim(); if(c.startsWith('#')){ const n=c.length===4? c.slice(1).split('').map(x=>x+x).join('') : c.slice(1); return [0,2,4].map(i=>parseInt(n.slice(i,i+2),16)); }
  const m=c.match(/[\d.]+/g); return m? m.slice(0,3).map(Number) : [0,0,0]; };
const mixc=(a,b,k)=>`rgb(${a.map((v,i)=>Math.round(v+(b[i]-v)*k)).join(',')})`;
function drawDay(sv, h){
  const cs=getComputedStyle(sv), day=hex(cs.getPropertyValue('--pp-sky')), night=hex(cs.getPropertyValue('--pp-night'));
  const ang=2*Math.PI*((h-SOLAR_NOON)/24+0.5), elev=-Math.cos(ang), k=Math.max(0,Math.min(1,(elev+0.1)/0.2));
  const sun=sv.querySelector('.jsun'), [cx,cy,rx,ry]=sun.dataset.orbit.split(' ').map(Number);
  sun.setAttribute('transform',`translate(${(cx-rx*Math.sin(ang)).toFixed(1)} ${(cy+ry*Math.cos(ang)).toFixed(1)})`);
  sv.querySelector('.jsky').setAttribute('fill',mixc(night,day,k));
  sv.querySelector('.jstars').setAttribute('opacity',(0.9*(1-k)).toFixed(2));
  const gl=sv.querySelector('.jglow');
  if(gl){ const i=Math.floor(h)%24, fr=h-Math.floor(h), v=HM[i]+(HM[(i+1)%24]-HM[i])*fr;
    gl.setAttribute('opacity',(0.3+0.7*v/HMX).toFixed(3)); sv.querySelector('.jmeter').style.transform=`scaleX(${(v/HMX).toFixed(3)})`; }
  sv.querySelectorAll('.jtherm').forEach(t=>{ const hw=+t.dataset.hw, pk=+t.dataset.pk; t.style.transform=`scaleX(${(0.5+hw*Math.cos(2*Math.PI*(h-pk)/24)).toFixed(3)})`; });
}
if(window.matchMedia('(prefers-reduced-motion: reduce)').matches){ daySvgs.forEach(s=>drawDay(s,13)); }
else { (function tick(now){ const h=((now-dayT0)/DAY_MS%1)*24; dayVisible.forEach(s=>drawDay(s,h)); requestAnimationFrame(tick); })(performance.now()); }

// ---------- pause drawings that are off screen (both CSS and SMIL, so scenes stay in step)
if('IntersectionObserver' in window){ const io=new IntersectionObserver(es=>es.forEach(e=>{ const sv=e.target;
    if(e.isIntersecting){ sv.classList.remove('paused'); sv.unpauseAnimations&&sv.unpauseAnimations(); if(daySvgs.includes(sv)) dayVisible.add(sv); } else { sv.classList.add('paused'); sv.pauseAnimations&&sv.pauseAnimations(); dayVisible.delete(sv); } }),{rootMargin:'120px'});
  document.querySelectorAll('svg.il').forEach(s=>io.observe(s)); }

// ---------- per-chapter Explore
document.querySelectorAll('.xbtn').forEach(b=>b.onclick=()=>{ const ch=b.closest('.chap'), on=!ch.classList.contains('open');
  ch.classList.toggle('open',on); b.setAttribute('aria-expanded',on);
  if(on) requestAnimationFrame(()=>{ if(!window.Plotly) return; drawAll();
    ch.querySelectorAll('.plot').forEach(d=>{ if(d.offsetParent && d.data) Plotly.Plots.resize(d); }); }); });


// ---------- estuary: real hourly salinity at Jordan Point
const EST_I=%%ESTI%%, ER=R.ode.raw.slice(EST_I,EST_I+49), ET=R.ode.rawt.slice(EST_I,EST_I+49), SO=R.ode.S_ocean;
let estTimer=null;
function estDraw(){ const k=+document.getElementById('estr').value, S=ER[k], fr=Math.max(0,Math.min(1,S/SO));
  const fx=Math.max(12,Math.min(306,106+(0.72-fr)*420));   // schematic: where the river/ocean boundary sits
  document.getElementById('es1').setAttribute('offset',Math.max(0,(fx-26)/320)); document.getElementById('es2').setAttribute('offset',Math.min(1,(fx+26)/320));
  document.getElementById('estfront').setAttribute('d',`M${fx} 30 L${fx} 192`);
  { const hh=new Date(ET[k]).getHours(); const hc=document.getElementById('estclock'); if(hc) hc.style.transform=`rotate(${(hh%12)*30}deg)`; }
  document.querySelectorAll('.estwaves').forEach(e=>e.setAttribute('transform',`translate(${fx.toFixed(1)} 0)`));
  const lo=Math.min(...ER), hi=Math.max(...ER), X=i=>8+i*(240/48), Y=v=>40-(v-lo)/(hi-lo||1)*30;
  document.getElementById('estline').setAttribute('d',ER.map((v,i)=>(i?'L':'M')+X(i).toFixed(1)+' '+Y(v).toFixed(1)).join(' '));
  const c=document.getElementById('estcur'); c.setAttribute('x1',X(k)); c.setAttribute('x2',X(k));
  const d=document.getElementById('estdot'); d.setAttribute('cx',X(k)); d.setAttribute('cy',Y(S));
  const when=new Date(ET[k]).toLocaleString([],{weekday:'short',hour:'numeric'}), trend=k? (S>ER[k-1]+0.3?'Tide coming in ↑':S<ER[k-1]-0.3?'Tide going out ↓':'Tide turning'):'';
  document.getElementById('estflow').dataset.dir = k? (S>ER[k-1]+0.3?'in':S<ER[k-1]-0.3?'out':'slack') : 'slack';
  document.getElementById('estread').innerHTML=`<b>${when}</b>: the water at the buoy is <b>${Math.round(fr*100)}% ocean</b>, ${Math.round((1-fr)*100)}% river (salinity ${S.toFixed(1)}). ${trend}`; }
document.getElementById('estr').addEventListener('input',()=>{ estStop(); estDraw(); });
function estStop(){ if(estTimer){ clearInterval(estTimer); estTimer=null; document.getElementById('estplay').textContent='▶'; document.getElementById('estplay').setAttribute('aria-label','Play the two days'); } }
document.getElementById('estplay').onclick=()=>{ if(estTimer){ estStop(); return; } const r=document.getElementById('estr'); if(+r.value>=48) r.value=0;
  document.getElementById('estplay').textContent='❚❚'; document.getElementById('estplay').setAttribute('aria-label','Pause');
  const reduce=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  estTimer=setInterval(()=>{ r.value=Math.min(48,+r.value+1); estDraw(); if(+r.value>=48) estStop(); }, reduce?600:220); };

// ---------- sea-level slider
const MSL=R.msl, base1912=MSL.inter+MSL.slope*1912;
function slDraw(){ const y=+document.getElementById('slr').value; const i=MSL.yr.indexOf(y); const trend=MSL.inter+MSL.slope*y;
  const v=(i>=0?MSL.v[i]:trend); const rise=v-base1912; const px=rise*600;   // 600 px per metre (exaggerated 6×, see note)
  const y0=222, ys=y0-px; document.getElementById('slsurf').setAttribute('transform',`translate(0 ${ys.toFixed(1)})`);
  const L1=document.getElementById('sl1912'); L1.setAttribute('y1',y0); L1.setAttribute('y2',y0); document.getElementById('sl1912t').setAttribute('y',y0-6);
  document.getElementById('slyear').textContent=y;
  const amt = unit==='us' ? (rise*39.37).toFixed(1)+' inches' : (rise*100).toFixed(0)+' cm';
  const EV={1912:'The Portland tide gauge starts recording.',1978:"The Blizzard of '78 sets a record: 14.17 ft.",2018:'Jan 4: a "bomb cyclone" floods the waterfront.',2022:'Dec 23: the third-highest water on record.',2024:'Jan 13: a new record, 14.57 ft.'};
  const evn = Object.keys(EV).map(Number).find(e=>Math.abs(e-y)<=1);
    document.getElementById('slread').innerHTML = i>=0 ? `In <b>${y}</b> the average sea level was <b>${rise>=0?'+':''}${amt}</b> compared with 1912.` : `No full year of data for ${y}.`;
  if(evn) document.getElementById('slread').innerHTML += `<br>📌 <b>${evn}:</b> ${EV[evn]}`;
  let g=''; for(let k=-4;k<=26;k++){ const step=unit==='us'? 0.0254 : 0.02, yy=y0-k*step*600; if(yy<8||yy>258) continue; const major=unit==='us'? k%4===0 : k%5===0;
    g+=`<line x1="172" x2="${major?196:k%2?181:186}" y1="${yy.toFixed(1)}" y2="${yy.toFixed(1)}" stroke="var(--il-ink)" stroke-width="${major?1.2:.7}"/>`+(major?`<text x="166" y="${(yy+3.5).toFixed(1)}" class="il-s il-h" text-anchor="end">${k>0?'+':''}${unit==='us'? k+' in' : k*2+' cm'}</text>`:''); }
  document.getElementById('ruler').innerHTML=g; }
document.getElementById('slr').addEventListener('input',slDraw);

// ---------- storm-tide stacker
const STORM=%%STORM%%; let stSel=STORM.length-1;
function stDraw(){ const lo=0.6, hi=6.1, yOf=v=>240-(v-lo)/(hi-lo)*220;
  document.getElementById('stbtns').innerHTML=STORM.map((s,i)=>`<button type="button" aria-pressed="${i===stSel}" data-i="${i}">${s[0]}</button>`).join('');
  document.querySelectorAll('#stbtns button').forEach(b=>b.onclick=()=>{ stSel=+b.dataset.i; stDraw(); });
  const v=STORM[stSel][1]; document.getElementById('stsurf').setAttribute('transform',`translate(0 ${yOf(v).toFixed(1)})`);
  const ys=STORM.map((s,i)=>({i,y:yOf(s[1])})).sort((p,q)=>p.y-q.y); for(let k=1;k<ys.length;k++) if(ys[k].y-ys[k-1].y<13) ys[k].y=ys[k-1].y+13;
  const ly={}; ys.forEach(o=>ly[o.i]=o.y);
  document.getElementById('stticks').innerHTML=STORM.map((s,i)=>{ const y=yOf(s[1]), on=i===stSel, t=ly[i]-3;
    return `<line x1="${on?0:160}" x2="320" y1="${y}" y2="${y}" stroke="${on?'var(--accent)':'var(--il-ink)'}" stroke-width="${on?1.6:.7}" stroke-dasharray="${on?'':'2 3'}" opacity="${on?1:.6}"/>`+
      `<text x="314" y="${t}" text-anchor="end" class="il-s il-h" style="font-weight:${on?700:500}">${s[0]} · ${Lm(s[1]).toFixed(1)} ${Lu()}</text>`; }).join('');
  const above=v-STORM[0][1];
  document.getElementById('stread').innerHTML=`<b>${STORM[stSel][0]}:</b> ${(Lm(v)).toFixed(1)} ${Lu()} above the low-tide datum` + (stSel? `, or <b>${Lm(above).toFixed(1)} ${Lu()} above an ordinary high tide</b>.` : '.'); }

// ---------- layer cake
const months={}; R.strat.t.forEach((t,i)=>{ const k=t.slice(0,7); (months[k]=months[k]||[[],[],[]]); ['t1','t2','t3'].forEach((c,j)=>{ if(R.strat[c][i]!=null) months[k][j].push(R.strat[c][i]); }); });
const MK=Object.keys(months).filter(k=>months[k][0].length>10); let lySel=MK.findIndex(k=>k.endsWith('-07')); if(lySel<0) lySel=MK.length-1;
const tcol=c=>{ const x=Math.max(0,Math.min(1,(c-2)/18)); const a=[74,140,190], b=[236,128,84]; return `rgb(${a.map((v,i)=>Math.round(v+(b[i]-v)*x)).join(',')})`; };
function lyDraw(){ const pick=[MK.findIndex(k=>k.endsWith('-01')),MK.findIndex(k=>k.endsWith('-04')),MK.findIndex(k=>k.endsWith('-07')),MK.findIndex(k=>k.endsWith('-10'))].filter(i=>i>=0);
  document.getElementById('lybtns').innerHTML=pick.map(i=>`<button type="button" aria-pressed="${i===lySel}" data-i="${i}">${new Date(MK[i]+'-15').toLocaleDateString([],{month:'long'})}</button>`).join('');
  document.querySelectorAll('#lybtns button').forEach(b=>b.onclick=()=>{ lySel=+b.dataset.i; lyDraw(); });
  const m=months[MK[lySel]].map(a=>a.reduce((p,c)=>p+c,0)/a.length), nm=['Near the top','Middle depth','Near the bottom'];
  m.forEach((v,j)=>{ { const b=document.getElementById('lyb'+(j+1)); if(b) b.setAttribute('fill',tcol(v)); } document.getElementById('lyt'+(j+1)).textContent=nm[j]+': '+T(v).toFixed(1)+' '+Tu(); });
  const diff=m[0]-m[2]; document.getElementById('lyread').innerHTML = diff>1.5 ? `<b>Layered:</b> the top is ${dT(diff).toFixed(1)} ${Tu()} warmer than the bottom.` : `<b>Mixed:</b> top and bottom within ${dT(Math.abs(diff)).toFixed(1)} ${Tu()}.`; }

const _drawAll=drawAll; drawAll=function(){ _drawAll(); try{ slDraw(); stDraw(); lyDraw(); estDraw(); }catch(e){ console.warn(e); } };
'''

STORM_JS = json.dumps([[n, v] for n, v in STORM_LEVELS])
js = JS.replace('%%DATA%%', json.dumps(R, separators=(',', ':')))
js = js.replace("if (window.Plotly) drawAll(); else window.addEventListener('load',()=>window.Plotly&&drawAll());", EXTRA_JS.replace('%%STORM%%', STORM_JS).replace('%%ESTI%%', str(EST_I)) + "\nif (window.Plotly) drawAll(); else window.addEventListener('load',()=>window.Plotly&&drawAll());")

HOME = 'https://ekelting.github.io/UNE-Marine-Monitoring-Network/'
page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Saco Bay, explained · UNE Marine Monitoring Network</title>
<meta name="description" content="Seven questions about Saco Bay, Maine, answered with UNE's buoys, radar and weather stations and more than a century of NOAA and USGS records.">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🌊</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&family=Nunito:ital,wght@0,400;0,600;0,700;0,800;0,900;1,400&display=swap">
<script src="{PLOTLY}"></script>
<style>{CSS}</style></head><body>
<header class="hero">
  <svg class="hero-waves" viewBox="0 0 1200 120" preserveAspectRatio="none" aria-hidden="true">
    <path class="hw1" d="M0 70 C150 40 300 100 450 70 C600 40 750 100 900 70 C1050 40 1150 90 1200 70 L1200 120 L0 120 Z"/>
    <path class="hw2" d="M0 85 C200 60 350 110 600 85 C800 60 950 110 1200 85 L1200 120 L0 120 Z"/>
  </svg>
  <div class="wrap hero-in">
    <nav class="hnav"><a href="{HOME}">🗺️ All UNE stations</a><a href="{HOME}analysis/">📊 Full technical analyses</a></nav>
    <p class="kicker">UNE Marine Monitoring Network</p>
    <h1>Saco Bay, explained</h1>
    <p class="lede">Seven questions about our coast, answered with UNE's buoys, radar and weather stations, plus more than a century of NOAA and USGS records.</p>
    <div class="toolbar"><span>Units</span><div class="segctl" role="group" aria-label="Units"><button id="u-si" type="button">Metric</button><button id="u-us" type="button">Imperial</button></div>
      <span>Theme</span><div class="segctl" role="group" aria-label="Theme"><button id="th-light" type="button">Light</button><button id="th-dark" type="button">Dark</button></div></div>
  </div>
</header>
<main class="wrap">
  {ILL_DEFS}
  <nav class="qgrid" aria-label="Questions">{tiles}</nav>
  {''.join(chs)}
  <section class="more-cta"><div><h2>Want every number?</h2><p>The full technical page has all {len(R) - 3} analyses with their methods, assumptions and uncertainty.</p></div><a href="{HOME}analysis/">📊 See the full analyses</a></section>
  <footer>Data: UNE stations (updated hourly); NOAA tide gauge 8418150 (Portland, since 1912); NOAA buoy 44007; NOAA Portland Jetport weather; USGS Saco River at Cornish (since 1916); map © OpenStreetMap contributors. Recent NOAA/USGS values are provisional. Not for navigation. Updated {R["_built"]}. <a href="{HOME}">UNE Marine Monitoring Network</a></footer>
</main>
<script>{js}</script>
</body></html>'''
