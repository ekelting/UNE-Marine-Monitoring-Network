"""
chartfit.py — one small piece of JavaScript shared by every station page: it adjusts each Plotly chart's layout to
the width it is drawn at, so the same figure reads well on a phone and on a laptop.

  chartFit(el, f, L)   call just before Plotly.react(el, f.data, L, cfg); changes f.data / L in place and returns cfg

What it does on narrow screens (chart narrower than 600 px):
  - hides Plotly's floating toolbar, which otherwise sits on top of legends, buttons and colour-bar titles
  - puts a wind/wave/current rose's legend directly under the rose and sizes the chart to fit, with no empty gap
  - single legends become a compact horizontal block above the plot; faint "(hourly)" lines drop out of the legend
  - month-by-month bar/box charts label every few months with a short name, written flat instead of sideways
  - axes with a long list of tick labels (e.g. times of day) keep every other label, written flat
  - calendars drop the sideways "Month" title that overlapped the month names
On every screen:
  - storm shading on the wave timeline only shows once you zoom in to three months or less, so the full-year view
    isn't covered in stripes
"""

JS = r"""
function chartFit(el, f, L){
  const W = el.clientWidth || window.innerWidth, narrow = W < 600;
  const cfg = {responsive:true, displaylogo:false, modeBarButtonsToRemove:['lasso2d','select2d']};
  if (narrow) cfg.displayModeBar = false;
  const axes = Object.keys(L).filter(k=>/^[xy]axis\d*$/.test(k));
  // rose charts: legend right under the rose, chart only as tall as it needs to be
  if (L.polar){
    const n = f.data.filter(t=>t.showlegend!==false).length;
    if (W < 560){
      const legPx = 26 + 19*n, rose = Math.min(W - 40, 420), H = rose + legPx + 72;
      L.height = H; el.style.height = H + 'px';
      L.margin = Object.assign({}, L.margin, {t:20, b:10, l:30, r:30});
      L.polar.domain = {x:[0,1], y:[(legPx+52)/(H-30), 1]};
      L.legend = Object.assign({}, L.legend, {orientation:'v', x:0.5, xanchor:'center', y:0, yanchor:'bottom'});
    }
    return cfg;
  }
  // a single, plain legend (panel charts with legend2, legend3… are laid out by the page itself)
  const panelLegends = Object.keys(L).some(k=>/^legend\d+$/.test(k));
  if (narrow && !panelLegends && L.showlegend !== false){
    for (const t of f.data) if (/\((hourly|every reading)\)/i.test(String(t.name||''))) t.showlegend = false;
    let shown = f.data.filter(t=>t.showlegend!==false && t.name);
    if (shown.length===1){ shown[0].showlegend = false; shown = []; }   // one line: the axis title already names it
    if (shown.length){
      L.legend = Object.assign({}, L.legend, {orientation:'h', x:0, xanchor:'left', y:1.02, yanchor:'bottom',
                               font:{size:10.5}, itemwidth:30, tracegroupgap:0, bgcolor:'rgba(0,0,0,0)'});
      if (L.legend.title) delete L.legend.title;
      // room above the plot for the wrapped legend rows
      let rows=1, used=0; const avail = W - 40;
      for (const t of shown){ const w = 50 + String(t.name).length*6.2; if (used && used + w > avail){ rows++; used = 0; } used += w; }
      const hasSel = axes.some(k=>L[k] && L[k].rangeselector);
      const need = rows*18 + 8 + (hasSel ? 30 : 0), m = Object.assign({t:30, b:40}, L.margin);
      const extra = Math.max(0, need - (m.t||0) + 6);
      m.t = (m.t||0) + extra; L.margin = m;
      if (L.height) { L.height += extra; el.style.height = L.height + 'px'; }
      // range buttons sit on the left above the plot; put them on their own row above the legend
      const plotH = Math.max(150, (L.height || el.clientHeight || 450) - m.t - m.b);
      for (const k of axes) if (L[k].rangeselector) L[k].rangeselector = Object.assign({}, L[k].rangeselector, {x:0, xanchor:'left', y:1.02 + (rows*18+6)/plotH, yanchor:'bottom', font:{size:11}});
    }
  }
  if (narrow){
    for (const k of axes){
      const a = L[k] || {};
      if (k[0]==='x'){
        // category axes holding month labels like "Nov 2025": short labels, every few months, flat
        const cats = [...new Set(f.data.filter(t=>(t.xaxis||'x')===('x'+k.slice(5)) || (k==='xaxis' && !t.xaxis))
                       .flatMap(t=>Array.isArray(t.x)? t.x : []))];
        if (cats.length > 6 && cats.every(c=>typeof c==='string' && /^[A-Z][a-z]{2} \d{4}$/.test(c))){
          const step = Math.ceil(cats.length/5);
          a.tickvals = cats.filter((c,i)=>i%step===0);
          a.ticktext = a.tickvals.map((c,i)=> c.slice(0,3) + (i===0 || c.startsWith('Jan') ? '<br>' + c.slice(4) : ''));
          a.tickangle = 0;
        } else if (Array.isArray(a.tickvals) && a.tickvals.length > 6){
          const keep = a.tickvals.map((v,i)=>i%2===0);
          a.tickvals = a.tickvals.filter((v,i)=>keep[i]);
          if (Array.isArray(a.ticktext)) a.ticktext = a.ticktext.filter((v,i)=>keep[i]);
          a.tickangle = 0;
        } else if (a.type==='date' || a.tickangle===undefined){
          a.nticks = Math.min(a.nticks||99, 5); a.tickangle = 0;
        }
        a.tickfont = Object.assign({size:10.5}, a.tickfont);
      } else {
        // calendars: the month names explain themselves
        if (a.title && /^Month$/i.test(String(a.title.text||a.title))) a.title = {text:''};
      }
      L[k] = a;
    }
    for (const t of f.data) if (t.colorbar){ t.colorbar = Object.assign({}, t.colorbar, {thickness:10, title:Object.assign({}, t.colorbar.title, {side:'right', font:{size:10.5}})}); }
  }
  return cfg;
}
// storm shading only once zoomed in to three months or less (the full-year view would be all stripes).
// Call before Plotly.react: sets each shape's visibility from the range currently shown, and follows later zooms.
function shadeByZoom(el, L){
  if (!L.shapes || !L.shapes.length) return;
  const spanOf = r => (new Date(r[1]) - new Date(r[0]))/864e5;
  const xa = el._fullLayout && el._fullLayout.xaxis;
  const on = xa && xa.range && !xa.autorange ? spanOf(xa.range) <= 95 : false;
  L.shapes = L.shapes.map(s=>Object.assign({}, s, {visible:on})); el._shadeOn = on;
  const hook = ()=>{ if (el._shadeHook) return; if (!el.on) return setTimeout(hook, 200); el._shadeHook = true;
  el.on('plotly_relayout', ev=>{
    if (Object.keys(ev).some(k=>k.startsWith('shapes'))) return;
    const r = el._fullLayout.xaxis.range, want = !el._fullLayout.xaxis.autorange && spanOf(r) <= 95;
    if (want === el._shadeOn) return; el._shadeOn = want;
    const upd = {}; el.layout.shapes.forEach((s,i)=>upd[`shapes[${i}].visible`]=want); Plotly.relayout(el, upd); }); };
  setTimeout(hook, 0);
}
"""
