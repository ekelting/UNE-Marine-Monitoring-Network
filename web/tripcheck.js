/* UNE trip check: shared by the main page's "On the water today" panel and the trip-check page.
   Rules come from the UNE boat captain (in this order): NOAA alerts, the local wave buoy against the PI's limit,
   wave direction, wind direction. The wind numbers and the "close to the limit" margin are drafts to be confirmed.
   The boat captain makes the final call. */
(function (G) {
  'use strict';
  const LAUNCH = [43.460385, -70.386006];                       // where the boats launch during the school year
  const KX = Math.cos(LAUNCH[0] * Math.PI / 180);
  const RINGS = [0, 1, 3, 6, 9, 12, 15, 18, 21, 24];             // nautical miles from the launch
  const BANDS = RINGS.slice(1);
  const ZONES = { ANZ154: 'Cape Elizabeth to Merrimack River', ANZ153: 'Casco Bay', ANZ152: 'Port Clyde to Cape Elizabeth',
                  MEZ023: 'Coastal York County', MEZ024: 'Coastal Cumberland County' };
  const MARINE = ['ANZ154', 'ANZ153', 'ANZ152'];
  // land-zone alerts that matter on the water or at the shore
  const SHORE_EVENTS = /Coastal Flood|High Surf|Rip Current|Dense Fog|Storm Surge|Tsunami|Hurricane|Tropical Storm|High Wind|Wind Advisory|Extreme Wind|Severe Thunderstorm Warning|Tornado Warning|Special Weather Statement/i;
  // marine alerts at or above Small Craft Advisory strength: UNE policy is no trips in open water
  const STRONGER = /Gale Warning|Storm Warning|Hurricane Force Wind Warning|Hurricane Warning|Tropical Storm Warning|Hazardous Seas Warning|Special Marine Warning|Storm Surge Warning/i;
  const STATE = ['Looks OK', "Captain's call", 'Stay ashore'];

  const pt = (nmi, brg) => [LAUNCH[0] + nmi * Math.cos(brg * Math.PI / 180) / 60, LAUNCH[1] + nmi * Math.sin(brg * Math.PI / 180) / (60 * KX)];
  const arc = (r, b0 = 0, b1 = 180) => { const a = []; for (let b = b0; b <= b1 + 1e-9; b += 2) a.push(pt(r, b)); return a; };
  // compass groups the captain uses
  const waveFrom = d => d == null ? null : (d = ((d % 360) + 360) % 360, d >= 67.5 && d < 157.5 ? 'E' : d >= 157.5 && d < 247.5 ? 'S' : d >= 247.5 && d < 337.5 ? 'W' : 'N');
  const windFrom = d => d == null ? null : (d = ((d % 360) + 360) % 360, d >= 22.5 && d < 157.5 ? 'E' : d >= 157.5 && d < 247.5 ? 'S' : d >= 247.5 && d < 337.5 ? 'W' : 'N');
  const COMP = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
  const compass = d => d == null ? '' : COMP[Math.round((((d % 360) + 360) % 360) / 22.5) % 16];

  // ---------- NOAA alerts ----------
  async function fetchAlerts() {
    const r = await fetch('https://api.weather.gov/alerts/active?zone=' + Object.keys(ZONES).join(','), { headers: { Accept: 'application/geo+json' } });
    if (!r.ok) throw new Error('NWS ' + r.status);
    const j = await r.json(), seen = new Set(), out = [];
    for (const f of j.features || []) {
      const p = f.properties || {}, ugc = ((p.geocode || {}).UGC || []).filter(z => ZONES[z]);
      if (seen.has(p.id) || !ugc.length) continue;
      const marine = ugc.some(z => MARINE.includes(z));
      if (!marine && !SHORE_EVENTS.test(p.event || '')) continue;
      seen.add(p.id);
      out.push({ event: p.event, headline: p.headline || '', desc: p.description || '', ends: p.ends || p.expires, onset: p.onset, severity: p.severity,
                 zones: ugc, marine, url: marine ? 'https://forecast.weather.gov/shmrn.php?mz=' + ugc.find(z => MARINE.includes(z)).toLowerCase()
                                                  : 'https://forecast.weather.gov/MapClick.php?lat=43.46&lon=-70.39' });
    }
    const rank = a => STRONGER.test(a.event) ? 0 : /Small Craft/i.test(a.event) ? 1 : /Warning/i.test(a.event) ? 2 : /Advisory/i.test(a.event) ? 3 : 4;
    return out.sort((a, b) => rank(a) - rank(b));
  }
  // what the alerts mean for UNE trips: 'gale' (stronger than a Small Craft Advisory), 'sca', or 'none' for our zone,
  // and the same for the zones north of Cape Elizabeth
  function alertLevel(alerts, zones) {
    let lvl = 'none';
    for (const a of alerts || []) {
      if (!a.zones.some(z => zones.includes(z))) continue;
      if (STRONGER.test(a.event)) return 'gale';
      if (/Small Craft/i.test(a.event)) lvl = 'sca';
    }
    return lvl;
  }
  const extraAlerts = alerts => (alerts || []).filter(a => a.zones.includes('ANZ154') && /Dense Fog|Freezing Spray/i.test(a.event)).map(a => a.event);

  // ---------- tide predictions (NOAA, Camp Ellis 8418606) ----------
  async function fetchTides(station = '8418606') {
    const d = new Date(Date.now() - 864e5), ymd = d.getFullYear() + String(d.getMonth() + 1).padStart(2, '0') + String(d.getDate()).padStart(2, '0');
    const r = await fetch(`https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=predictions&application=UNE_buoy&begin_date=${ymd}&range=96&datum=MLLW&station=${station}&time_zone=lst_ldt&units=english&interval=hilo&format=json`);
    const j = await r.json(); if (!j.predictions) throw new Error('no tide predictions');
    return j.predictions.map(e => ({ t: new Date(e.t.replace(' ', 'T')), v: +e.v, type: e.type }));   // local clock time
  }
  // smooth cosine curve between highs and lows; level and rising/falling at a moment
  function tideAt(ev, t) {
    for (let i = 0; i < ev.length - 1; i++) { const a = ev[i], b = ev[i + 1];
      if (a.t <= t && t < b.t) { const f = (t - a.t) / (b.t - a.t); return { v: a.v + (b.v - a.v) * (1 - Math.cos(Math.PI * f)) / 2, rising: b.type === 'H', next: b }; } }
    return null;
  }

  // ---------- live readings -> trip-check inputs ----------
  // data: {local: latest.json of the local wave buoy, wind: latest.json of the weather station, ndbc: ndbc-44007.json}
  function liveInputs({ local, wind, ndbc, alerts, tides, limit = 2.5 }) {
    const M2FT = 3.28084, MS2KT = 1.94384, now = new Date(), age = iso => iso ? (now - new Date(iso)) / 36e5 : Infinity;
    const L = local && age(local.last_obs) < 6 ? local.now || {} : {}, W = wind && age(wind.last_obs) < 6 ? wind.now || {} : {};
    const N = ndbc && age(ndbc.time) < 6 ? ndbc : {};
    const t = tides ? tideAt(tides, now) : null;
    const num = v => (v == null || !isFinite(v)) ? null : +v;
    const inp = {
      alert: alertLevel(alerts, ['ANZ154']), alertNorth: alertLevel(alerts, ['ANZ153', 'ANZ152']), extra: extraAlerts(alerts), limit,
      bay: num(L.hs_m) != null ? +(L.hs_m * M2FT).toFixed(1) : null,
      off: num(N.wvht_m) != null ? +(N.wvht_m * M2FT).toFixed(1) : null,
      waveDir: waveFrom(num(L.wave_dir_deg) ?? num(N.mwd_deg)),
      wind: num(W.wind_ms) != null ? Math.round(W.wind_ms * MS2KT) : null, gust: num(W.gust_ms) != null ? Math.round(W.gust_ms * MS2KT) : null,
      windDir: windFrom(num(W.wind_dir)), tide: t ? (t.rising ? 'rise' : 'fall') : 'rise'
    };
    if (inp.off == null && inp.bay != null) inp.offMissing = true;
    const src = {
      bay: L.hs_m != null ? `Camp Ellis wave buoy, ${(L.hs_m * M2FT).toFixed(1)} ft from the ${L.wave_dir || compass(L.wave_dir_deg)}` : 'Camp Ellis wave buoy: no recent reading',
      off: N.wvht_m != null ? `NOAA buoy 44007, ${(N.wvht_m * M2FT).toFixed(1)} ft` : 'NOAA buoy 44007: no recent reading',
      wind: W.wind_ms != null ? `Ram Island, ${Math.round(W.wind_ms * MS2KT)} kt gusting ${Math.round((W.gust_ms ?? W.wind_ms) * MS2KT)} from the ${compass(W.wind_dir)}` : 'Ram Island: no recent wind reading',
      tide: t ? `Camp Ellis tide ${t.rising ? 'rising' : 'falling'}` : 'tide unknown'
    };
    return { inp, src };
  }

  // ---------- the rules ----------
  function rate(inp) {
    const lim = +inp.limit || 2.5, w = +inp.wind || 0, g = +(inp.gust ?? inp.wind) || 0, dir = inp.windDir, wd = inp.waveDir;
    const bands = BANDS.map((k, i) => {
      const inner = i < 2; let lvl = 0; const why = []; const up = (n, t) => { if (n > lvl) lvl = n; why.push(t); };
      if (inp.alert === 'sca') { up(2, 'Small Craft Advisory in effect: UNE policy is no trips in open water'); return { lvl, why }; }
      if (inp.alert === 'gale') { up(2, 'Gale Warning or stronger in effect'); return { lvl, why }; }
      if (inp.alertNorth !== 'none' && RINGS[i] >= 9) up(1, 'Small Craft Advisory or stronger north of Cape Elizabeth: no trips into Casco Bay or beyond');
      (inp.extra || []).forEach(e => up(1, `NWS ${e} in effect`));
      const wave = inner ? inp.bay : (inp.off ?? inp.bay), src = inner ? 'local buoy' : (inp.off != null ? 'NOAA offshore buoy' : 'local buoy (no offshore reading)');
      if (wave == null) up(1, 'no recent wave reading: check conditions before leaving');
      else {
        const shelter = inner && (wd === 'N' || wd === 'W');
        if (wave > lim) up(shelter ? 1 : 2, `${wave} ft waves at the ${src}, over the PI's ${lim} ft limit` + (shelter ? ' (shelter may be possible behind land)' : ''));
        else if (wave > lim - 0.5) up(1, `${wave} ft waves at the ${src}, close to the ${lim} ft limit`);
        if (wd === 'E' && wave >= lim - 1) why.push('waves from the E/ESE/SE: no protection anywhere');
      }
      const capt = dir === 'E' ? 12 : 15, stay = (dir === 'W' && inner) ? 25 : 20;
      if (w >= stay || g >= stay + 5) up(2, `wind ${w} kt, gusts ${g} kt`);
      else if (w >= capt || g >= capt + 5) up(dir === 'W' && inner && w < 20 ? 0 : 1, dir === 'E' ? `east wind ${w} kt: nothing blocks it`
        : dir === 'W' && inner ? `west wind ${w} kt is blocked by the coast near shore` : dir === 'W' ? `west wind ${w} kt: blocked near shore, but it builds waves out here and pushes you away from land` : `wind ${w} kt, gusts ${g} kt`);
      if (i === 0 && dir === 'E' && w >= 10 && inp.tide === 'fall') up(1, 'onshore wind against the falling tide: steep waves at the river mouth');
      if (!why.length) why.push('nothing over the draft limits');
      return { lvl, why };
    });
    // the Saco River estuary, mouth to the Biddeford dams: OK during a Small Craft Advisory
    const river = (() => { let lvl = 0; const why = []; const up = (n, t) => { if (n > lvl) lvl = n; why.push(t); };
      if (inp.alert === 'sca') why.push('Small Craft Advisory in effect, but the estuary is OK to work in');
      if (inp.alert === 'gale') up(1, 'Gale Warning or stronger in effect');
      if (w >= 25 || g >= 30) up(2, `wind ${w} kt, gusts ${g} kt`); else if (w >= 20 || g >= 25) up(1, `wind ${w} kt, gusts ${g} kt`);
      if (dir === 'E' && w >= 10 && inp.tide === 'fall') up(1, 'onshore wind against the falling tide: steep waves at the river mouth');
      if (!why.length) why.push('sheltered from ocean waves; nothing over the draft limits');
      return { lvl, why }; })();
    // neighbouring bands with the same rating and reasons share one card
    const groups = [];
    bands.forEach((b, i) => { const key = b.lvl + '|' + b.why.join('|').replace(/at the (local buoy|NOAA offshore buoy)[^,]*/g, ''), last = groups[groups.length - 1];
      if (last && last.key === key) last.to = i; else groups.push({ key, from: i, to: i, lvl: b.lvl, why: b.why }); });
    groups.forEach(gp => { gp.range = `${RINGS[gp.from]}–${RINGS[gp.to + 1]} nm`;
      gp.where = gp.to <= 1 ? (gp.from === 0 ? (gp.to === 0 ? 'off the river mouth' : 'the river mouth and Saco Bay') : 'Saco Bay') : gp.from === 0 ? 'everywhere out to 24 nm' : gp.from === 1 ? 'Saco Bay and open water' : 'open water'; });
    return { bands, river, groups };
  }

  // ---------- map ----------
  const COL = dark => dark ? ['#4fc98a', '#f0b44a', '#f07a6f'] : ['#1a9b5f', '#d98a00', '#d4473f'];
  function baseLayer(mode, dark) {
    if (mode === 'chart') return L.tileLayer.wms('https://gis.charttools.noaa.gov/arcgis/rest/services/MCS/NOAAChartDisplay/MapServer/exts/MaritimeChartService/WMSServer',
      { layers: '0,1,2,3,4,5,6,7', format: 'image/png', transparent: false, version: '1.3.0', maxZoom: 18, attribution: 'NOAA Office of Coast Survey — not for navigation' });
    return dark
      ? L.layerGroup([L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', { maxZoom: 16, attribution: 'Esri, HERE, Garmin, &copy; OpenStreetMap contributors' }),
                      L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}', { maxZoom: 16 })])
      : L.layerGroup([L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}', { maxZoom: 16, attribution: 'Esri, GEBCO, NOAA, Garmin, HERE, &copy; OpenStreetMap contributors' }),
                      L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/{z}/{y}/{x}', { maxZoom: 16 })]);
  }
  // el: map element; river: {outer, inner, dams} in [lat, lon]; mini: the small main-page version
  function makeMap(el, { river, mini = false, dark = false, mode = 'map' } = {}) {
    const m = L.map(el, { zoomControl: false, scrollWheelZoom: false, minZoom: 7, maxZoom: 15, zoomSnap: 0.25 });
    L.control.zoom({ position: mini ? 'bottomright' : 'topleft' }).addTo(m);
    el.addEventListener('click', () => m.scrollWheelZoom.enable()); el.addEventListener('mouseleave', () => m.scrollWheelZoom.disable());
    const g = { m, dark, mode, base: null, bands: [], st: [], last: null };
    g.setBase = (mode_, dark_) => { g.mode = mode_ ?? g.mode; g.dark = dark_ ?? g.dark; if (g.base) g.base.remove(); g.base = baseLayer(g.mode, g.dark).addTo(m); g.base.bringToBack && g.base.bringToBack(); if (g.last) g.paint(g.last); };
    BANDS.forEach((r, i) => { const ll = i === 0 ? [LAUNCH, ...arc(1)] : [...arc(RINGS[i + 1]), ...arc(RINGS[i]).reverse()];
      g.bands.push(L.polygon(ll, { stroke: false, fillOpacity: .3, interactive: false }).addTo(m)); });
    BANDS.forEach(r => { L.polyline(arc(r), { color: '#3c4650', weight: mini ? 1 : 1.3, opacity: .75, dashArray: mini ? '3 3' : '6 5', interactive: false }).addTo(m);
      if (!mini || r === 1 || r % 6 === 0) L.marker(pt(r, 22), { icon: L.divIcon({ className: 'tc-lbl tc-ring', html: r + ' nm', iconSize: null }), interactive: false }).addTo(m); });
    if (river) {
      g.river = L.polygon([...river.outer, ...river.inner], { color: '#3c4650', weight: .8, fillOpacity: .75 }).addTo(m).bindTooltip('Saco River estuary, mouth to the Biddeford dams');
      if (!mini) river.dams.forEach(d => L.polyline(d, { color: '#111', weight: 4, interactive: false }).addTo(m));
    }
    L.circleMarker(LAUNCH, { radius: mini ? 4 : 6, color: '#fff', weight: 1.5, fillColor: '#f28f16', fillOpacity: 1 }).bindTooltip('UNE boat launch').addTo(m);
    if (!mini) {
      L.circleMarker([43.4727, -70.3605], { radius: 5, color: '#fff', weight: 1.5, fillColor: '#1c5cab', fillOpacity: 1 }).bindTooltip('Camp Ellis wave buoy (local waves)').addTo(m);
      L.circleMarker([43.525, -70.141], { radius: 5, color: '#fff', weight: 1.5, fillColor: '#1c5cab', fillOpacity: 1 }).bindTooltip('NOAA buoy 44007 (offshore waves)').addTo(m);
      L.circleMarker([43.467126, -70.356328], { radius: 5, color: '#fff', weight: 1.5, fillColor: '#5a6b7d', fillOpacity: 1 }).bindTooltip('Ram Island weather station (wind)').addTo(m);
    }
    const home = mini ? [[LAUNCH[0] - 20 / 60, LAUNCH[1] - 1 / (60 * KX)], [LAUNCH[0] + 20 / 60, LAUNCH[1] + 24.8 / (60 * KX)]]
                      : [[LAUNCH[0] - 24.6 / 60, LAUNCH[1] - 6 / (60 * KX)], [LAUNCH[0] + 24.6 / 60, LAUNCH[1] + 24.8 / (60 * KX)]];
    g.home = () => { m.fitBounds(home, { padding: [4, 4] }); const q = m.latLngToContainerPoint(LAUNCH); m.panBy([q.x - (mini ? 14 : 110), 0], { animate: false }); };
    g.river && (g.toRiver = () => m.fitBounds(g.river.getBounds(), { padding: [20, 20] }));
    g.paint = res => { g.last = res; const c = COL(g.dark);
      g.bands.forEach((b, i) => b.setStyle({ fillColor: c[res.bands[i].lvl] }));
      if (g.river) g.river.setStyle({ fillColor: c[res.river.lvl] });
      g.st.forEach(x => x.remove()); g.st = [];
      if (!mini) res.groups.forEach(gp => { const r = (RINGS[gp.from] + RINGS[gp.to + 1]) / 2;
        g.st.push(L.marker(pt(r, gp.from === 0 ? 135 : 115), { icon: L.divIcon({ className: 'tc-lbl tc-st', html: `<span style="color:${c[gp.lvl]}">${STATE[gp.lvl]}</span>`, iconSize: null, iconAnchor: [34, 8] }), interactive: false }).addTo(m)); }); };
    g.setBase(mode, dark); g.home();
    return g;
  }

  G.TC = { LAUNCH, RINGS, ZONES, STATE, COL, fetchAlerts, fetchTides, tideAt, liveInputs, rate, makeMap, compass };
})(window);
