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
  // el: map element; river: {outer, inner, dams} in [lat, lon]; geo: bands.json (the rings trimmed to water);
  // mini: the small main-page version, which opens at 3 nm and steps out ring by ring
  const STEPS = [3, 6, 9, 12, 15, 18, 21, 24];
  const UNE_LOGO = 'data:image/png;base64,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';   // the blue UNE box, marking the boat launch
  function makeMap(el, { river, geo, mini = false, dark = false, mode = 'map' } = {}) {
    const m = L.map(el, { zoomControl: false, scrollWheelZoom: false, doubleClickZoom: !mini, minZoom: 7, maxZoom: 15, zoomSnap: 0.25 }).setView(LAUNCH, 11);
    if (!mini) { L.control.zoom({ position: 'topleft' }).addTo(m);
      el.addEventListener('click', () => m.scrollWheelZoom.enable()); el.addEventListener('mouseleave', () => m.scrollWheelZoom.disable()); }
    const g = { m, dark, mode, base: null, bands: [], rings: [], st: [], last: null, R: mini ? 3 : 24 };
    g.setBase = (mode_, dark_) => { g.mode = mode_ ?? g.mode; g.dark = dark_ ?? g.dark; if (g.base) g.base.remove(); g.base = baseLayer(g.mode, g.dark).addTo(m); g.base.bringToBack && g.base.bringToBack(); if (g.last) g.paint(g.last); };
    BANDS.forEach((r, i) => {
      const shape = geo ? geo.bands[i] : [[i === 0 ? [LAUNCH, ...arc(1)] : [...arc(RINGS[i + 1]), ...arc(RINGS[i]).reverse()]]];
      g.bands.push(L.polygon(shape, { stroke: false, fillOpacity: .3, interactive: false }));
      const lines = geo ? geo.lines[i] : [arc(r)], at = geo && geo.labels[i] ? geo.labels[i] : pt(r, 22);
      const ring = [L.polyline(lines, { color: '#3c4650', weight: mini ? 1 : 1.3, opacity: .75, dashArray: mini ? '3 3' : '6 5', interactive: false })];
      if (mini) ring.push(L.marker(at, { icon: L.divIcon({ className: 'tc-lbl tc-ring', html: r + ' nm', iconSize: null, iconAnchor: [-3, 6] }), interactive: false }));
      else ring.push(L.polyline(lines, { color: '#000', weight: 14, opacity: 0 }).bindTooltip(r + ' nm from the UNE boat launch', { sticky: true }));   // label on hover only
      g.rings.push(L.layerGroup(ring));
    });
    if (river) {
      g.river = L.polygon([...river.outer, ...river.inner], { color: '#3c4650', weight: .8, fillOpacity: .75 }).addTo(m).bindTooltip('Saco River estuary, mouth to the Biddeford dams');
      if (!mini) river.dams.forEach(d => L.polyline(d, { color: '#111', weight: 4, interactive: false }).addTo(m));
    }
    const lw = mini ? 34 : 46, lh = Math.round(lw * 40 / 96);
    g.logo = L.marker(LAUNCH, { icon: L.icon({ iconUrl: UNE_LOGO, iconSize: [lw, lh], iconAnchor: [lw / 2, lh / 2], className: 'tc-logo' }), zIndexOffset: 1000, alt: 'UNE boat launch' })
      .bindTooltip('UNE boat launch').addTo(m);
    if (!mini) {
      L.circleMarker([43.4727, -70.3605], { radius: 5, color: '#fff', weight: 1.5, fillColor: '#1c5cab', fillOpacity: 1 }).bindTooltip('Camp Ellis wave buoy (local waves)').addTo(m);
      L.circleMarker([43.525, -70.141], { radius: 5, color: '#fff', weight: 1.5, fillColor: '#1c5cab', fillOpacity: 1 }).bindTooltip('NOAA buoy 44007 (offshore waves)').addTo(m);
      L.circleMarker([43.467126, -70.356328], { radius: 5, color: '#fff', weight: 1.5, fillColor: '#5a6b7d', fillOpacity: 1 }).bindTooltip('Ram Island weather station (wind)').addTo(m);
    }
    // show the rings out to R nautical miles and frame them
    g.show = R => { g.R = R; BANDS.forEach((r, i) => { const on = r <= R;
        if (on) { g.bands[i].addTo(m); g.rings[i].addTo(m); } else { g.bands[i].remove(); g.rings[i].remove(); } });
      if (g.river) g.river.bringToFront();
      if (g.last) g.paint(g.last);
      if (g.stepLbl) { g.stepLbl.textContent = `Out to ${R} nm`; g.inBtn.disabled = R <= STEPS[0]; g.outBtn.disabled = R >= STEPS[STEPS.length - 1]; } };
    g.frame = R => { const b = L.latLngBounds([]); g.bands.forEach((p, i) => { if (BANDS[i] <= R) b.extend(p.getBounds()); }); b.extend(LAUNCH);
      m.fitBounds(b, { padding: mini ? [26, 10] : [8, 8], animate: !!g.ready }); };
    g.home = () => { g.show(mini ? g.R : 24); g.frame(mini ? g.R : 24); };
    g.river && (g.toRiver = () => m.fitBounds(g.river.getBounds(), { padding: [20, 20] }));
    if (mini) {   // "Closer / Farther" steps instead of free zooming
      const C = L.control({ position: 'bottomright' }); C.onAdd = () => { const d = L.DomUtil.create('div', 'leaflet-bar tc-steps');
        d.innerHTML = '<button type="button" data-d="-1" aria-label="Closer">−</button><span aria-live="polite"></span><button type="button" data-d="1" aria-label="Farther out">+</button>';
        L.DomEvent.disableClickPropagation(d); [g.inBtn, g.stepLbl, g.outBtn] = d.children;
        d.querySelectorAll('button').forEach(bt => bt.onclick = () => { const i = STEPS.indexOf(g.R) + (+bt.dataset.d); if (i < 0 || i >= STEPS.length) return; g.show(STEPS[i]); g.frame(STEPS[i]); });
        return d; }; C.addTo(m);
    }
    g.paint = res => { g.last = res; const c = COL(g.dark);
      g.bands.forEach((b, i) => b.setStyle({ fillColor: c[res.bands[i].lvl] }));
      if (g.river) g.river.setStyle({ fillColor: c[res.river.lvl] });
      g.st.forEach(x => x.remove()); g.st = [];
      if (!mini) res.groups.forEach(gp => { if (RINGS[gp.from] >= g.R) return; const r = (RINGS[gp.from] + Math.min(RINGS[gp.to + 1], g.R)) / 2;
        g.st.push(L.marker(pt(r, gp.from === 0 ? 135 : 115), { icon: L.divIcon({ className: 'tc-lbl tc-st', html: `<i style="background:${COL(false)[gp.lvl]}"></i>${STATE[gp.lvl]}`, iconSize: null, iconAnchor: [44, 11] }), interactive: false }).addTo(m)); }); };
    g.setBase(mode, dark); g.home(); g.ready = true;
    return g;
  }

  G.TC = { LAUNCH, RINGS, ZONES, STATE, COL, fetchAlerts, fetchTides, tideAt, liveInputs, rate, makeMap, compass };
})(window);
