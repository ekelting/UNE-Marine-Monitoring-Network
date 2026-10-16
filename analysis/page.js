const R = %%DATA%%;
let unit='us';
try{ const u=localStorage.getItem('une-units'); if(u) unit = u==='metric' ? 'si' : 'us'; }catch(e){}
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const T=c=>c==null?null:(unit==='us'? c*9/5+32 : c), Tu=()=>unit==='us'?'°F':'°C';
const dT=c=>unit==='us'? c*9/5 : c;
const Lm=m=>m==null?null:(unit==='us'? m*3.28084 : m), Lu=()=>unit==='us'?'ft':'m';
const Rm=mm=>mm==null?null:(unit==='us'? mm/25.4 : mm), Ru=()=>unit==='us'?'in':'mm';
const Wm=v=>v==null?null:(unit==='us'? v*2.23694 : v), Wu=()=>unit==='us'?'mph':'m/s';
const Qc=v=>v==null?null:(unit==='us'? v*35.3147 : v), Qu=()=>unit==='us'?'cfs':'m³/s';
const SITE={'Wood Island':'--wi','Jordan Point':'--jp','Ferry Beach':'--fb','Goose Rocks Beach':'--grb'};
const CFG={displaylogo:false,responsive:true,modeBarButtonsToRemove:['lasso2d','select2d','autoScale2d','toggleSpikelines']};
function base(extra){ const ink=css('--ink2'), grid=css('--grid');
  const L={paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',font:{family:'system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif',color:ink,size:12},
    margin:{l:56,r:12,t:10,b:40},hoverlabel:{font:{family:'system-ui'}},legend:{orientation:'h',y:1.14,x:0},
    xaxis:{gridcolor:grid,linecolor:grid,zerolinecolor:grid},yaxis:{gridcolor:grid,linecolor:grid,zerolinecolor:grid}};
  for(const k in extra){ L[k] = (typeof extra[k]==='object' && !Array.isArray(extra[k]) && L[k]) ? Object.assign({},L[k],extra[k]) : extra[k]; } return L; }
const roll=(a,n)=>a.map((_,i)=>{ const s=a.slice(Math.max(0,i-n+1),i+1).filter(v=>v!=null); return s.length? s.reduce((x,y)=>x+y,0)/s.length:null; });
const doyOf=t=>{ const d=new Date(t+'T12:00'); return Math.floor((d-new Date(d.getFullYear(),0,0))/864e5); };
const bands=(storms)=>(storms||[]).map(s=>({type:'rect',xref:'x',yref:'paper',x0:s[0],x1:s[1],y0:0,y1:1,fillcolor:css('--grb'),opacity:.32,line:{width:0},layer:'below'}));
const P=(id,tr,lay)=>{ if(document.getElementById(id)) Plotly.react(id,tr,lay,CFG); };
const hline=(y,color,dash,label)=>({shape:{type:'line',xref:'paper',x0:0,x1:1,y0:y,y1:y,line:{color,width:1.5,dash:dash||'dash'}},ann:label?{xref:'paper',x:.01,y,yshift:9,xanchor:'left',text:label,showarrow:false,font:{size:11,color:css('--ink2')},bgcolor:css('--card')}:null});

function texts(){
  document.querySelectorAll('[data-temp]').forEach(e=>e.textContent=T(+e.dataset.temp).toFixed(1)+' '+Tu());
  document.querySelectorAll('[data-dtemp]').forEach(e=>e.textContent=dT(+e.dataset.dtemp).toFixed(Math.abs(+e.dataset.dtemp)<0.1?2:1)+' '+Tu());
  document.querySelectorAll('[data-len]').forEach(e=>e.textContent=Lm(+e.dataset.len).toFixed(unit==='us'?1:2)+' '+Lu());
  document.querySelectorAll('[data-rain]').forEach(e=>e.textContent=Rm(+e.dataset.rain).toFixed(unit==='us'?1:0)+' '+Ru());
  document.querySelectorAll('[data-flow]').forEach(e=>e.textContent=Math.round(Qc(+e.dataset.flow)).toLocaleString()+' '+Qu());
  document.querySelectorAll('[data-gdd]').forEach(e=>e.textContent=Math.round(unit==='us'? +e.dataset.gdd*9/5 : +e.dataset.gdd).toLocaleString()+' '+(unit==='us'?'°F·days':'°C·days'));
  document.querySelectorAll('[data-mm]').forEach(e=>e.textContent=unit==='us'? (+e.dataset.mm/25.4*12).toFixed(1)+' inches per century' : (+e.dataset.mm).toFixed(1)+' mm per year');
  document.getElementById('u-us').setAttribute('aria-pressed',unit==='us'); document.getElementById('u-si').setAttribute('aria-pressed',unit==='si');
}

const CH = {};
CH.msl=()=>{ const m=R.msl; if(!m) return; const b=m.inter+m.slope*1912, cv=x=>unit==='us'? x*39.37 : x*100, u=unit==='us'?'inches':'cm';
  P('pmsl',[{x:m.yr,y:m.v.map(v=>cv(v-b)),type:'scatter',mode:'markers',marker:{size:6,color:css('--ce'),opacity:.8},hovertemplate:'%{x}: %{y:+.1f} '+u+' vs 1912<extra>yearly average</extra>'},
    {x:m.yr,y:m.yr.map(y=>cv(m.slope*(y-1912))),type:'scatter',mode:'lines',line:{color:css('--jp'),width:2.4},hoverinfo:'skip'}],
    base({showlegend:false,xaxis:{title:{text:'year'}},yaxis:{title:{text:u+' higher than in 1912'},zeroline:true,zerolinecolor:css('--muted')},
      shapes:[1978,2024].map(y=>({type:'line',x0:y,x1:y,yref:'paper',y0:0,y1:1,line:{color:css('--muted'),width:1,dash:'dot'}})),
      annotations:[[1978,"Blizzard of '78"],[2024,'2024 record']].map(([y,t])=>({x:y,yref:'paper',y:.99,yanchor:'top',xanchor:y>2000?'right':'left',xshift:y>2000?-3:3,text:t,showarrow:false,font:{size:11,color:css('--ink2')}}))})); };
CH.amax=()=>{ const a=R.amax; if(!a) return; const rl=a.rl, H=[hline(Lm(rl['10']),css('--ink2'),'dash','1-in-10-year'),hline(Lm(rl['100']),css('--ink2'),'dash','1-in-100-year'),hline(Lm(a.mhhw),css('--muted'),'dot','ordinary high tide')];
  const ev=((R.events||{}).storms||[]).map(e=>{ const i=a.yr.indexOf(e.year); return i<0?null:{x:e.year,y:Lm(a.v[i]),text:e.label,showarrow:true,arrowhead:0,ax:e.year<2000?-30:(e.year===2018?-60:(e.year===2022?-40:-20)),ay:e.year===2024?-22:(e.year===2018?28:-26),font:{size:10.5,color:css('--ink')},bgcolor:css('--card'),arrowcolor:css('--muted')}; }).filter(Boolean);
    P('pamax',[{x:a.yr,y:a.v.map(Lm),type:'scatter',mode:'markers',marker:{size:a.v.map(v=>v>=rl['10']?11:7),color:a.v.map(v=>v>=rl['10']?css('--jp'):css('--ce')),line:{color:css('--card'),width:1}},hovertemplate:'%{x}: %{y:.2f} '+Lu()+'<extra>highest water</extra>'}],
    base({showlegend:false,xaxis:{title:{text:'year'}},yaxis:{title:{text:'highest water ('+Lu()+' above MLLW)'}},shapes:H.map(h=>h.shape),annotations:H.filter(h=>h.ann).map(h=>h.ann).concat(ev)})); };
CH.surge=()=>{ const s=R.surge; if(!s) return;
  P('psurge',[{x:s.t,y:s.v.map(Lm),type:'scatter',mode:'lines',line:{color:css('--ce'),width:1.6},hovertemplate:'%{x|%b %d}: %{y:+.2f} '+Lu()+'<extra>surge (daily average)</extra>'}],
    base({showlegend:false,xaxis:{type:'date'},yaxis:{title:{text:'storm surge, daily average ('+Lu()+')'},zeroline:true,zerolinecolor:css('--muted')},shapes:bands(s.storms)})); };
CH.sst=()=>{ const s=R.sst; if(!s) return; const di=s.t.map(doyOf);
  const c10=di.map(d=>T(s.p10[d-1])), c90=di.map(d=>T(s.p90[d-1])), c50=di.map(d=>T(s.clim[d-1]));
  P('psst',[{x:s.t,y:c90,type:'scatter',mode:'lines',line:{width:0},hoverinfo:'skip',showlegend:false},
    {x:s.t,y:c10,type:'scatter',mode:'lines',line:{width:0},fill:'tonexty',fillcolor:'rgba(140,140,140,.22)',name:'Normal range',hoverinfo:'skip'},
    {x:s.t,y:c50,type:'scatter',mode:'lines',line:{color:css('--muted'),width:1.4},name:'Normal',hovertemplate:'%{x|%b %d} normal: %{y:.1f} '+Tu()+'<extra></extra>'},
    {x:s.t,y:roll(s.v,3).map(T),type:'scatter',mode:'lines',line:{color:css('--ce'),width:2.4},name:'NOAA buoy 44007',hovertemplate:'%{x|%b %d}: %{y:.1f} '+Tu()+'<extra>44007</extra>'},
    {x:s.ce_t,y:roll(s.ce,3).map(T),type:'scatter',mode:'lines',line:{color:css('--jp'),width:1.6,dash:'dot'},name:'Camp Ellis (near shore)',hovertemplate:'%{x|%b %d}: %{y:.1f} '+Tu()+'<extra>Camp Ellis</extra>'}],
    base({xaxis:{type:'date'},yaxis:{title:{text:'sea temperature ('+Tu()+')'}}}));
  // warming stripes: one band per year, coloured by difference from the 1991-2020 average
  const base9120=s.yr.map((y,i)=>[y,s.yv[i]]).filter(p=>p[0]>=1991&&p[0]<=2020).map(p=>p[1]), ref=base9120.reduce((a,b)=>a+b,0)/base9120.length;
  const yrs=[]; for(let y=s.yr[0]; y<=s.yr[s.yr.length-1]; y++) yrs.push(y);
  const an=yrs.map(y=>{ const i=s.yr.indexOf(y); return i<0?null:s.yv[i]-ref; }), mx=Math.max(...an.filter(v=>v!=null).map(Math.abs));
  P('psstyr',[{z:[an.map(v=>v==null?null:dT(v))],x:yrs,y:['sea'],type:'heatmap',zmin:-dT(mx),zmax:dT(mx),colorscale:[[0,'#2166ac'],[.5,'#f2f2f2'],[1,'#b2182b']],showscale:false,xgap:1,
      hovertemplate:'%{x}: %{z:+.2f} '+Tu()+' vs 1991–2020<extra></extra>'}],
    base({showlegend:false,margin:{l:12,r:12,t:6,b:30},yaxis:{visible:false},xaxis:{dtick:5}})); };
CH.flow=()=>{ const f=R.flow; if(!f) return;
  P('pflow',[{x:f.t,y:f.pct,type:'scatter',mode:'lines',line:{color:css('--jp'),width:2},fill:'tozeroy',fillcolor:'rgba(235,104,52,.12)',customdata:f.rank,
      hovertemplate:'%{x|%b %d}: %{y:.0f}% of normal (%{customdata:.0f}th percentile)<extra></extra>'}],
    base({showlegend:false,xaxis:{type:'date'},yaxis:{title:{text:'% of normal flow for the date'},rangemode:'tozero'},
      shapes:[{type:'line',xref:'paper',x0:0,x1:1,y0:100,y1:100,line:{color:css('--ink2'),width:1.5,dash:'dash'}},{type:'rect',xref:'paper',x0:0,x1:1,y0:0,y1:50,fillcolor:css('--grb'),opacity:.13,line:{width:0},layer:'below'}],
      annotations:[{xref:'paper',x:.01,y:100,yshift:9,xanchor:'left',text:'normal (median since '+f.start+')',showarrow:false,font:{size:11,color:css('--ink2')},bgcolor:css('--card')},
                   {xref:'paper',x:.01,y:25,xanchor:'left',text:'less than half of normal',showarrow:false,font:{size:11,color:css('--ink2')}}]})); };
CH.air=()=>{ const a=R.air; if(!a) return; const wk={}, wr={};
  a.t.forEach((t,i)=>{ if(a.v[i]==null) return; const d=new Date(t+'T12:00'); const k=new Date(d-((d.getDay()+6)%7)*864e5).toISOString().slice(0,10); (wk[k]=wk[k]||[]).push(a.v[i]-a.norm[doyOf(t)-1]); });
  const ks=Object.keys(wk).sort(), av=ks.map(k=>dT(wk[k].reduce((p,c)=>p+c,0)/wk[k].length));
  P('pair',[{x:ks,y:av,type:'bar',marker:{color:av.map(v=>v>=0?'#d6604d':'#4393c3')},hovertemplate:'week of %{x|%b %d}: %{y:+.1f} '+Tu()+' vs normal<extra></extra>'}],
    base({showlegend:false,bargap:.1,xaxis:{type:'date'},yaxis:{title:{text:'warmer (+) or colder (−) than normal ('+Tu()+')'},zeroline:true,zerolinecolor:css('--ink2')}})); };
CH.marsh=()=>{ const m=R.marsh; if(!m) return;
  P('p1',[{x:m.t,y:m.obs.map(Lm),name:'Measured',type:'scatter',mode:'lines',line:{color:css('--ce'),width:2},hovertemplate:'%{y:.2f} '+Lu()+'<extra>measured</extra>'},
    {x:m.t,y:m.fit.map(Lm),name:'Tide-only prediction',type:'scatter',mode:'lines',line:{color:css('--jp'),width:2,dash:'dot'},hovertemplate:'%{y:.2f} '+Lu()+'<extra>tide only</extra>'}],
    base({xaxis:{type:'date'},yaxis:{title:{text:'water level ('+Lu()+')'}}}));
  const names={M2:'M2 main lunar',S2:'S2 main solar',N2:'N2 lunar distance',K1:'K1 daily',O1:'O1 daily lunar',M4:'M4 shallow-water',M6:'M6 shallow-water'}, ks=Object.keys(m.amp);
  P('p1b',[{y:ks.map(k=>names[k]),x:ks.map(k=>Lm(m.amp[k])),type:'bar',orientation:'h',marker:{color:css('--ce')},hovertemplate:'%{x:.2f} '+Lu()+'<extra></extra>'}],
    base({margin:{l:140,r:12,t:6,b:36},showlegend:false,yaxis:{autorange:'reversed'},xaxis:{title:{text:'strength of each beat ('+Lu()+')'}}})); };
CH.tideclock=()=>{ const h=R.tideclock; if(!h) return;
  P('p3',[{z:h.z,x:[...Array(24).keys()].map(i=>new Date(2000,0,1,i).toLocaleTimeString([],{hour:'numeric'})),y:h.dates,type:'heatmap',
    colorscale:[[0,css('--seq0')],[.5,css('--seq1')],[1,css('--seq2')]],colorbar:{title:{text:'PSU',side:'right'},thickness:10,len:.9},hovertemplate:'%{y}, %{x}: %{z:.1f} PSU<extra></extra>',xgap:1,ygap:1}],
    base({margin:{l:84,r:12,t:6,b:44},yaxis:{autorange:'reversed',type:'category',nticks:10},xaxis:{type:'category',tickangle:-45,nticks:12}})); };
CH.strat=()=>{ const s=R.strat; if(!s) return; const dd=s.t1.map((v,i)=>v==null||s.t3[i]==null?null:dT(v-s.t3[i]));
  P('pstrat',[{x:s.t,y:dd,type:'scatter',mode:'lines',line:{color:css('--jp'),width:1.8},fill:'tozeroy',fillcolor:'rgba(235,104,52,.22)',hovertemplate:'%{x|%b %d}: top is %{y:.1f} '+Tu()+' warmer than bottom<extra></extra>'}],
    base({showlegend:false,xaxis:{type:'date'},yaxis:{title:{text:'top minus bottom ('+Tu()+')'},rangemode:'tozero'},
      annotations:[{xref:'paper',yref:'paper',x:.02,y:.95,xanchor:'left',text:'big gap = layered · near zero = mixed',showarrow:false,font:{size:11,color:css('--ink2')}}]})); };
CH.soil=()=>{ const s=R.soil; if(!s||!s.dev) return; const z=s.dev.z.map(r=>r.map(v=>v==null?null:dT(v))), mx=dT(Math.max(...s.dev.z[0].filter(v=>v!=null).map(Math.abs)));
  P('p5',[{z,x:s.wk.t,y:s.dev.depths.map(d=>d+' cm'),type:'heatmap',zmin:-mx,zmax:mx,colorscale:[[0,'#2166ac'],[.5,'#f2f2f2'],[1,'#b2182b']],colorbar:{title:{text:Tu(),side:'right'},thickness:10},
      hovertemplate:'%{y}, %{x|%a %I %p}: %{z:+.2f} '+Tu()+' vs that day\'s average<extra></extra>'}],
    base({margin:{l:56,r:12,t:6,b:40},xaxis:{type:'date'},yaxis:{autorange:'reversed',type:'category',title:{text:'depth'}}})); };
CH.wrose=()=>{ const w=R.wrose; if(!w) return; const dirs=['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'], cols=['#cde2fb','#86b6ef','#2a78d6','#104281'];
  const nm={'0–3':'0–7','3–6':'7–13','6–9':'13–20','9+':'20+'};
  P('pwrose',Object.keys(w.rose).map((k,i)=>({type:'barpolar',r:w.rose[k],theta:dirs,name:unit==='us'?nm[k]+' mph':k+' m/s',marker:{color:cols[i],line:{color:css('--card'),width:1}},hovertemplate:'from %{theta}: %{r:.1f}% of hours<extra>%{fullData.name}</extra>'})),
    base({margin:{l:30,r:30,t:30,b:20},legend:{orientation:'h',y:-0.08},polar:{bgcolor:'rgba(0,0,0,0)',angularaxis:{direction:'clockwise',rotation:90,gridcolor:css('--grid'),color:css('--ink2')},radialaxis:{ticksuffix:'%',gridcolor:css('--grid'),color:css('--muted'),angle:90}}})); };
CH.chl=()=>{ const C=R.chl; if(!C) return; const hl=[...Array(24).keys()].map(h=>new Date(2000,0,1,h).toLocaleTimeString([],{hour:'numeric'}));
  const prof=(n,c,fc)=>[{x:hl,y:C[n].h_q3,type:'scatter',mode:'lines',line:{width:0},hoverinfo:'skip',showlegend:false},{x:hl,y:C[n].h_q1,type:'scatter',mode:'lines',line:{width:0},fill:'tonexty',fillcolor:fc,hoverinfo:'skip',showlegend:false},
    {x:hl,y:C[n].h_med,type:'scatter',mode:'lines+markers',name:n,line:{color:css(c),width:2.4},marker:{size:5},hovertemplate:'%{x}: %{y:.1f} µg/L (typical)<extra>'+n+'</extra>'}];
  P('pchlday',[...prof('Wood Island','--wi','rgba(27,175,122,.15)'),...prof('Jordan Point','--jp','rgba(235,104,52,.15)')],
    base({xaxis:{type:'category',nticks:12},yaxis:{title:{text:'chlorophyll (µg/L)'},rangemode:'tozero'},shapes:[{type:'rect',x0:'10 AM',x1:'2 PM',xref:'x',yref:'paper',y0:0,y1:1,fillcolor:css('--grb'),opacity:.15,line:{width:0},layer:'below'}],
      annotations:[{x:'12 PM',yref:'paper',y:.98,text:'midday sun',showarrow:false,font:{size:11,color:css('--ink2')}}]}));
  const nb=(n,c)=>({x:C[n].night.t,y:C[n].night.v,name:n,type:'scatter',mode:'lines+markers',line:{color:css(c),width:2},marker:{size:6},hovertemplate:'%{x|%b %d}: %{y:.1f} µg/L<extra>'+n+' (night)</extra>'});
  const top=Math.max(22,...C['Jordan Point'].night.v.filter(v=>v!=null),...C['Wood Island'].night.v.filter(v=>v!=null));
  P('pchlnight',[nb('Wood Island','--wi'),nb('Jordan Point','--jp')],
    base({xaxis:{type:'date'},yaxis:{title:{text:'night-time chlorophyll (µg/L)'},range:[0,top*1.05]},
      shapes:[[0,5],[5,20],[20,60]].map(([a,b],i)=>({type:'rect',xref:'paper',x0:0,x1:1,y0:a,y1:b,fillcolor:[css('--wi'),css('--grb'),css('--jp')][i],opacity:.08,line:{width:0},layer:'below'})),
      annotations:[[2.5,'low (under 5)'],[12.5,'medium (5–20)']].map(([y,t])=>({xref:'paper',x:.99,xanchor:'right',y,text:t,showarrow:false,font:{size:11,color:css('--ink2')}}))}));
  const sc=C['Jordan Point'].sc, edges=[[0,15,'under 15'],[15,20,'15–20'],[20,25,'20–25'],[25,30,'25–30'],[30,40,'over 30']];
  P('pchlsal',edges.map(([lo,hi,l])=>({y:sc.c.filter((c,i)=>sc.s[i]!=null&&sc.s[i]>=lo&&sc.s[i]<hi),name:l,type:'box',boxpoints:false,marker:{color:css('--jp')},line:{color:css('--jp'),width:1.6},fillcolor:'rgba(235,104,52,.18)',
      hovertemplate:'%{y:.1f} µg/L<extra>salinity '+l+'</extra>'})),
    base({showlegend:false,xaxis:{title:{text:'salinity (PSU) → saltier, more ocean water'},type:'category'},yaxis:{title:{text:'night-time chlorophyll (µg/L)'},rangemode:'tozero'}})); };
let v8='sal_psu';
CH.anova=()=>{ const A=R.anova&&R.anova[v8]; if(!A) return; const u=v8==='temp_c'?Tu():v8==='sal_psu'?'PSU':'mg/L', cv=v8==='temp_c'?dT:(x=>x);
  const pr=A.pairs.slice().sort((a,b)=>Math.abs(b[2])-Math.abs(a[2])), lab=pr.map(p=>p[0]+' − '+p[1]), sig=pr.map(p=>p[4]<0.05);
  P('p8',[{x:pr.map(p=>cv(p[2])),y:lab,type:'scatter',mode:'markers',marker:{size:11,color:sig.map(s=>s?css('--jp'):css('--muted'))},
      error_x:{type:'data',array:pr.map(p=>cv(p[5]||0)),color:css('--ink2'),thickness:1.6,width:6},
      customdata:pr.map(p=>p[4]<0.001?'< 0.001':p[4].toFixed(3)),hovertemplate:'%{y}: %{x:+.2f} '+u+' (p = %{customdata})<extra></extra>'}],
    base({showlegend:false,margin:{l:230,r:16,t:10,b:40},yaxis:{autorange:'reversed',type:'category'},xaxis:{title:{text:'average difference ('+u+')'},zeroline:true,zerolinecolor:css('--ink'),zerolinewidth:2}}));
  const t8=document.getElementById('t8'); if(t8) t8.innerHTML='';
  document.querySelectorAll('.tabs button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.v===v8)); };
CH.rain=()=>{ const r=R.rain; if(!r) return; const rng=[r.t[0],r.t[r.t.length-1]];
  P('p10a',[{x:r.t,y:r.rain.map(Rm),type:'bar',marker:{color:css('--ce')},hovertemplate:'%{x|%b %d}: %{y:.2f} '+Ru()+'<extra>rain</extra>'}],base({showlegend:false,margin:{l:56,r:12,t:6,b:24},xaxis:{type:'date',range:rng},yaxis:{title:{text:'rain ('+Ru()+')'}}}));
  P('p10q',[{x:r.qt,y:r.q.map(Qc),type:'scatter',mode:'lines+markers',line:{color:css('--wi'),width:2},marker:{size:5},hovertemplate:'%{x|%b %d}: %{y:,.0f} '+Qu()+'<extra>Saco River</extra>'}],base({showlegend:false,margin:{l:56,r:12,t:6,b:24},xaxis:{type:'date',range:rng},yaxis:{title:{text:'river ('+Qu()+')'}}}));
  P('p10b',[{x:r.st,y:r.s,type:'scatter',mode:'lines+markers',line:{color:css('--jp'),width:2},marker:{size:6},hovertemplate:'%{x|%b %d}: %{y:.1f} PSU<extra>Jordan Point</extra>'}],base({showlegend:false,margin:{l:56,r:12,t:6,b:30},xaxis:{type:'date',range:rng},yaxis:{title:{text:'salinity (PSU)'}}})); };
CH.radar=()=>{ const r=R.radar; if(!r) return; const bins={}; r.x.forEach((x,i)=>{ if(x==null||r.y[i]==null) return; const k=Math.floor(x); (bins[k]=bins[k]||[]).push(r.y[i]); });
  const ks=Object.keys(bins).map(Number).filter(k=>bins[k].length>=8).sort((a,b)=>a-b), med=ks.map(k=>{ const a=bins[k].slice().sort((p,q)=>p-q); return a[Math.floor(a.length/2)]; });
  P('p11',[{x:r.x.map(Wm),y:r.y,type:'scattergl',mode:'markers',marker:{size:5,color:css('--ri'),opacity:.35},hovertemplate:'wind %{x:.1f} '+Wu()+', roughness %{y:.1f}%<extra></extra>',name:'one radar scan'},
    {x:ks.map(k=>Wm(k+.5)),y:med,type:'scatter',mode:'lines+markers',line:{color:css('--jp'),width:3},marker:{size:6},name:'typical (median)',hovertemplate:'wind ≈ %{x:.0f} '+Wu()+': typical roughness %{y:.1f}%<extra></extra>'}],
    base({xaxis:{title:{text:'wind at Ram Island ('+Wu()+')'}},yaxis:{title:{text:'surface roughness (% echoing)'}}})); };
CH.drift=()=>{ const d=R.drift; if(!d) return; const ND=d.net_dir, OD=d.other_dir;
  const dirs=['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'], ang=dirs.map((_,i)=>i*22.5), N=R.cfg.normal;
  const rel=a=>((a-N+540)%360)-180, rmax=Math.max(...d.erose)*1.12;   // rel>0: south of straight-on -> pushes north
  P('pdrose',[{type:'barpolar',r:ang.map(a=>rel(a)>0&&rel(a)<90?rmax:0),theta:ang,width:22.5,marker:{color:'rgba(42,120,214,.12)'},hoverinfo:'skip',showlegend:false},
    {type:'barpolar',r:ang.map(a=>rel(a)<0&&rel(a)>-90?rmax:0),theta:ang,width:22.5,marker:{color:'rgba(235,104,52,.12)'},hoverinfo:'skip',showlegend:false},
    {type:'barpolar',r:d.erose,theta:ang,width:20,name:'wave energy',customdata:dirs,marker:{color:css('--ink2'),line:{color:css('--card'),width:1}},hovertemplate:'from %{customdata}: %{r:.1f}% of wave energy<extra></extra>'},
    {type:'scatterpolar',r:[rmax,rmax],theta:[N-90,N+90],mode:'lines',line:{color:css('--grb'),width:5},name:'beach line',hoverinfo:'skip'},
    {type:'scatterpolar',r:[0,rmax*.85],theta:[N,N],mode:'lines+markers',marker:{symbol:'arrow',size:12,angleref:'previous',color:css('--ink2')},line:{color:css('--ink2'),width:2,dash:'dot'},name:'straight onto the beach',hoverinfo:'skip'}],
    base({margin:{l:30,r:30,t:30,b:30},legend:{orientation:'h',y:-0.06},polar:{barmode:'overlay',bgcolor:'rgba(0,0,0,0)',angularaxis:{direction:'clockwise',rotation:90,tickvals:ang,ticktext:dirs,gridcolor:css('--grid'),color:css('--ink2')},radialaxis:{range:[0,rmax],gridcolor:css('--grid'),showticklabels:false}},
      annotations:[{x:1,xanchor:'right',y:.02,xref:'paper',yref:'paper',text:'waves from the blue side<br>push sand <b>north</b>',showarrow:false,font:{size:11,color:css('--ink2')}},{x:0,xanchor:'left',y:.98,xref:'paper',yref:'paper',text:'waves from the orange side<br>push sand <b>south</b>',showarrow:false,font:{size:11,color:css('--ink2')}}]}));
  P('p13',[{x:d.cum.t,y:d.cum.k,name:'Kamphuis',type:'scatter',mode:'lines',line:{color:css('--ce'),width:2.4},hovertemplate:'%{x|%b %d}: %{y:,.0f} thousand m³<extra>Kamphuis</extra>'},
    {x:d.cum.t,y:d.cum.c,name:'CERC',type:'scatter',mode:'lines',line:{color:css('--jp'),width:2,dash:'dot'},hovertemplate:'%{x|%b %d}: %{y:,.0f} thousand m³<extra>CERC</extra>'}],
    base({xaxis:{type:'date'},yaxis:{title:{text:'thousand m³ moved '+ND}},shapes:bands(d.storms)}));
  const ml=d.month.m.map(m=>new Date(m+'-15').toLocaleDateString([],{month:'short'})+' ’'+m.slice(2,4)), cw=ND==='north'?css('--ce'):css('--jp'), ca=ND==='north'?css('--jp'):css('--ce');
  P('pdmonth',[{x:ml,y:d.month.w,name:'pushed '+ND,type:'bar',marker:{color:cw},hovertemplate:'%{x}: %{y:.1f} thousand m³ '+ND+'<extra></extra>'},{x:ml,y:d.month.a,name:'pushed '+OD,type:'bar',marker:{color:ca},hovertemplate:'%{x}: %{y:.2f} thousand m³ '+OD+'<extra></extra>'}],
    base({barmode:'relative',bargap:.25,xaxis:{type:'category'},yaxis:{title:{text:'thousand m³ (+ '+ND+', − '+OD+')'},zeroline:true,zerolinecolor:css('--ink2')}}));
  const top=d.ranking.slice(0,8), rest=d.ranking.slice(8).reduce((a,r)=>a+r[1],0), labs=[...top.map(r=>r[0]),(d.ranking.length-top.length)+' smaller storms','All other days'], vals=[...top.map(r=>r[1]),rest,d.nonstorm];
  P('pdstorm',[{y:labs,x:vals,type:'bar',orientation:'h',marker:{color:labs.map((l,i)=>i>=top.length?css('--muted'):cw)},text:vals.map(v=>(v/d.total*100).toFixed(0)+'%'),textposition:'outside',cliponaxis:false,textfont:{color:css('--ink'),size:12},hovertemplate:'%{y}: %{x:.1f} thousand m³<extra></extra>'}],
    base({showlegend:false,margin:{l:120,r:40,t:6,b:40},yaxis:{autorange:'reversed',type:'category'},xaxis:{title:{text:'sand pushed '+ND+' (thousand m³)'},rangemode:'tozero'}}));
  P('p13b',[{x:d.sens.map(r=>r[0]),y:d.sens.map(r=>r[2]/1000),name:'Kamphuis',type:'scatter',mode:'lines+markers',line:{color:css('--ce'),width:2},marker:{size:7},hovertemplate:'%{x}°: %{y:+,.0f} thousand m³/yr<extra>Kamphuis (+ north)</extra>'},
    {x:d.sens.map(r=>r[0]),y:d.sens.map(r=>r[1]/1000),name:'CERC',type:'scatter',mode:'lines+markers',line:{color:css('--jp'),width:2,dash:'dot'},marker:{size:7},hovertemplate:'%{x}°: %{y:+,.0f} thousand m³/yr<extra>CERC (+ north)</extra>'}],
    base({margin:{l:56,r:12,t:24,b:40},xaxis:{title:{text:'direction the beach faces (°)'}},yaxis:{title:{text:'thousand m³/yr (+ north, − south)'},zeroline:true,zerolinecolor:css('--ink2')},
      shapes:[{type:'line',x0:N,x1:N,yref:'paper',y0:0,y1:1,line:{color:css('--grb'),width:2,dash:'dot'}}],annotations:[{x:N,yref:'paper',y:.04,xanchor:'left',xshift:4,text:'Camp Ellis beach (est.)',showarrow:false,font:{size:11,color:css('--ink2')},bgcolor:css('--card')}]})); };
CH.shields=()=>{ const s=R.shields; if(!s) return; const m=s.month||{m:[],pct:[]}, ml=m.m.map(x=>new Date(x+'-15').toLocaleDateString([],{month:'short'})+' ’'+x.slice(2,4));
  P('p14',[{x:ml,y:m.pct,type:'bar',marker:{color:css('--ce')},text:m.pct.map(v=>v==null?'':v.toFixed(0)+'%'),textposition:'outside',cliponaxis:false,textfont:{color:css('--ink'),size:11},hovertemplate:'%{x}: sand moving %{y:.0f}% of hours<extra></extra>'}],
    base({showlegend:false,margin:{l:56,r:12,t:18,b:40},xaxis:{type:'category'},yaxis:{title:{text:'% of hours sand moves'},rangemode:'tozero'}})); };
CH.currents=()=>{ const c=R.currents; if(!c) return; const dirs=['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'], tot=c.rose.reduce((a,b)=>a+b,0);
  P('p15',[{x:c.x,y:c.y,text:c.t,type:'scatter',mode:'lines',line:{color:css('--ce'),width:2.2},hovertemplate:'%{text}: %{x:.0f} km E, %{y:.0f} km N<extra></extra>'},
    {x:[0],y:[0],type:'scatter',mode:'markers+text',text:['start'],textposition:'middle right',marker:{size:9,color:css('--ink2')},textfont:{color:css('--ink2')},hoverinfo:'skip'}],
    base({showlegend:false,xaxis:{title:{text:'km east'},scaleanchor:'y',scaleratio:1},yaxis:{title:{text:'km north'}}}));
  P('p15b',[{type:'barpolar',r:c.rose.map(v=>v/tot*100),theta:dirs,marker:{color:css('--ce'),line:{color:css('--card'),width:2}},hovertemplate:'toward %{theta}: %{r:.1f}% of hours<extra></extra>'}],
    base({showlegend:false,margin:{l:30,r:30,t:20,b:20},polar:{bgcolor:'rgba(0,0,0,0)',angularaxis:{direction:'clockwise',rotation:90,gridcolor:css('--grid'),color:css('--ink2')},radialaxis:{ticksuffix:'%',gridcolor:css('--grid'),color:css('--muted'),angle:90}}}));
  P('p15c',[{x:c.cw.w.map(Wm),y:c.cw.c,text:c.cw.t,type:'scatter',mode:'markers',marker:{size:7,color:css('--ce'),opacity:.6},hovertemplate:'%{text}: wind %{x:.1f} '+Wu()+', current %{y:.1f} cm/s<extra></extra>'}],
    base({showlegend:false,margin:{l:56,r:12,t:6,b:40},xaxis:{title:{text:'along-shore wind toward NNE ('+Wu()+')'},zeroline:true,zerolinecolor:css('--muted')},yaxis:{title:{text:'bottom current (cm/s)'},zeroline:true,zerolinecolor:css('--muted')}})); };
CH.ode=()=>{ const o=R.ode; if(!o) return; const rng=[o.t[0],o.t[o.t.length-1]];
  P('p17',[{x:o.rawt,y:o.raw,name:'Hourly',type:'scatter',mode:'lines',line:{color:css('--jp'),width:1},opacity:.3,hovertemplate:'%{y:.1f} PSU<extra>hourly</extra>'},
    {x:o.t,y:o.obs,name:'Tides averaged out',type:'scatter',mode:'lines',line:{color:css('--jp'),width:2.6},hovertemplate:'%{y:.1f} PSU<extra>tide-averaged</extra>'},
    {x:o.t,y:o.mod,name:'Model',type:'scatter',mode:'lines',line:{color:css('--ce'),width:2.2,dash:'dot'},hovertemplate:'%{y:.1f} PSU<extra>model</extra>'}],
    base({xaxis:{type:'date',range:rng},yaxis:{title:{text:'salinity (PSU)'}}}));
  P('p17b',[{x:o.qd.t,y:o.qd.v.map(Qc),type:'scatter',mode:'lines+markers',line:{color:css('--ce'),width:2},marker:{size:5},hovertemplate:'%{x|%b %d}: %{y:,.0f} '+Qu()+'<extra>Saco River</extra>'}],base({showlegend:false,margin:{l:56,r:12,t:6,b:24},xaxis:{type:'date',range:rng},yaxis:{title:{text:'river ('+Qu()+')'}}}));
  P('p17c',[{x:o.t,y:o.tr.map(Lm),type:'scatter',mode:'lines',line:{color:css('--ri'),width:2},hovertemplate:'%{x|%b %d}: %{y:.1f} '+Lu()+'<extra>tidal range</extra>'}],base({showlegend:false,margin:{l:56,r:12,t:6,b:30},xaxis:{type:'date',range:rng},yaxis:{title:{text:'tidal range ('+Lu()+')'}}}));
  const sc=o.sc, xs=sc.tr.map(Lm), n=xs.length, mx=xs.reduce((a,b)=>a+b)/n, my=sc.sr.reduce((a,b)=>a+b)/n;
  const b1=xs.reduce((a,x,i)=>a+(x-mx)*(sc.sr[i]-my),0)/xs.reduce((a,x)=>a+(x-mx)**2,0), b0=my-b1*mx, xr=[Math.min(...xs),Math.max(...xs)];
  P('p18',[{x:xs,y:sc.sr,text:sc.d,type:'scatter',mode:'markers',marker:{size:9,color:css('--jp'),line:{color:css('--card'),width:2}},hovertemplate:'%{text}: tidal range %{x:.1f} '+Lu()+', swing %{y:.1f} PSU<extra></extra>'},
    {x:xr,y:xr.map(x=>b0+b1*x),type:'scatter',mode:'lines',line:{color:css('--ink2'),width:1.5,dash:'dash'},hoverinfo:'skip'}],
    base({showlegend:false,xaxis:{title:{text:'tidal range ('+Lu()+')'}},yaxis:{title:{text:'salinity swing per tide (PSU)'}},annotations:[{xref:'paper',yref:'paper',x:.02,y:.98,xanchor:'left',showarrow:false,text:`slope ${b1.toFixed(1)} PSU per ${Lu()}`,font:{size:12,color:css('--ink2')}}]}));
  const p=o.par, se=p.se, li=document.getElementById('odelist');
  if(li) li.innerHTML=[`τ = <b>${p.tau.toFixed(1)} ± ${se[0].toFixed(1)} days</b> (how fast salinity adjusts)`,`S_eq = <b>${p.Seq.toFixed(1)} ± ${se[1].toFixed(1)} PSU</b> at average flow and tide`,
    `b_Q = <b>${p.bq.toFixed(2)} ± ${se[2].toFixed(2)} PSU per m³/s</b> of Cornish flow (Q̄ = ${p.Q0.toFixed(1)} m³/s)`,`b_T = <b>${p.bt>=0?'+':''}${p.bt.toFixed(1)} ± ${se[3].toFixed(1)} PSU per m</b> of tidal range (T̄R = ${p.TR0.toFixed(2)} m)`,
    `Fit: R² = ${p.R2.toFixed(2)}, typical error ${p.rmse.toFixed(1)} PSU. The ± values are honest error bars, widened because each step is so similar to the last.`].map(x=>'<li>'+x+'</li>').join(''); };
CH.same=()=>{ const e=R.events, m=R.msl; if(!e||!m||!document.getElementById('psame')) return; const r=e.records;
  const gap=(r.ft2024-r.ft1978)*0.3048, slr=m.slope*(r.y2024-r.y1978), rest=gap-slr, cv=x=>unit==='us'? x*39.37 : x*100, u=unit==='us'?'in':'cm';
  P('psame',[{y:[''],x:[cv(slr)],type:'bar',orientation:'h',name:'higher sea since 1978',marker:{color:css('--ce')},text:[cv(slr).toFixed(1)+' '+u+' · higher sea'],textposition:'inside',insidetextanchor:'middle',textfont:{color:'#fff',size:13},hovertemplate:'sea-level rise 1978→2024: %{x:.1f} '+u+'<extra></extra>'},
    {y:[''],x:[cv(rest)],type:'bar',orientation:'h',name:'bigger storm / tide',marker:{color:css('--jp')},text:[cv(rest).toFixed(1)+' '+u],textposition:'inside',insidetextanchor:'middle',textfont:{color:'#fff',size:13},hovertemplate:'storm and tide difference: %{x:.1f} '+u+'<extra></extra>'}],
    base({barmode:'stack',height:170,margin:{l:10,r:10,t:30,b:40},legend:{orientation:'h',y:1.35,x:0},xaxis:{title:{text:'how much higher the 2024 record was than 1978 ('+u+')'},range:[0,cv(gap)*1.02]},yaxis:{visible:false}})); };
CH.flood=()=>{ const f=R.flood; if(!f||!document.getElementById('pflood')) return;
  P('pflood',[{x:f.yr,y:f.days,type:'bar',marker:{color:css('--ce')},hovertemplate:'%{x}: %{y} days<extra>water reached the 12 ft minor flood level</extra>',name:'each year'},
    {x:f.dec.map(d=>d[0]+5),y:f.dec.map(d=>d[1]),type:'scatter',mode:'lines+markers',line:{color:css('--jp'),width:3,shape:'hvh'},marker:{size:6},name:'decade average',hovertemplate:'%{x:.0f}s: %{y:.1f} days per year<extra>decade average</extra>'}],
    base({bargap:.1,xaxis:{title:{text:'year'}},yaxis:{title:{text:'days the water reached 12 ft'},rangemode:'tozero'}})); };
CH.map=()=>{ if(!document.getElementById('pmap')||!R.coast) return; const k=Math.cos(43.46*Math.PI/180), tr=[];
  R.coast.lines.forEach(l=>tr.push({x:l.map(p=>p[0]),y:l.map(p=>p[1]),type:'scatter',mode:'lines',line:{color:css('--ink2'),width:1.3},hoverinfo:'skip',showlegend:false}));
  const B=R.coast.buoys, sal=B.map(b=>b.sal);
  tr.push({x:[-70.3605],y:[43.4727],text:['Camp Ellis wave buoy'],type:'scatter',mode:'markers+text',textposition:'middle right',marker:{size:10,color:css('--muted'),symbol:'diamond'},textfont:{color:css('--ink2'),size:11},hoverinfo:'text',showlegend:false});
  tr.push({x:B.map(b=>b.lon),y:B.map(b=>b.lat),text:B.map(b=>`<b>${b.name}</b>`),type:'scatter',mode:'markers+text',textposition:B.map(b=>({'Jordan Point':'middle left','Wood Island':'bottom center','Ferry Beach':'middle right','Goose Rocks Beach':'middle right'})[b.name]||'top right'),
    textfont:{color:css('--ink'),size:12},marker:{size:20,color:sal,colorscale:[[0,'#c6dbef'],[1,'#08306b']],cmin:Math.min(...sal)-1,cmax:Math.max(...sal)+.5,line:{color:css('--card'),width:2},
    colorbar:{title:{text:'salinity (PSU)',side:'right'},thickness:10,len:.55,y:.3}},customdata:sal,hovertemplate:'%{text}: average salinity %{customdata:.1f} PSU<extra></extra>',showlegend:false});
  P('pmap',tr,base({margin:{l:4,r:4,t:4,b:4},xaxis:{visible:false,range:[-70.45,-70.29]},yaxis:{visible:false,range:[43.385,43.555],scaleanchor:'x',scaleratio:1/k},
    annotations:[{x:-70.3878,y:43.4835,ax:-70.3832,ay:43.4655,xref:'x',yref:'y',axref:'x',ayref:'y',showarrow:true,arrowhead:3,arrowsize:1.3,arrowwidth:3.5,arrowcolor:'#eb6834',text:''},
      {x:-70.4,y:43.49,text:'sand drifts<br>north',showarrow:false,font:{size:12,color:'#eb6834'},xanchor:'right'},
      {x:-70.33,y:43.505,text:'Saco Bay',showarrow:false,font:{size:13,color:css('--muted')}},{x:-70.415,y:43.452,text:'Saco River',showarrow:false,font:{size:11,color:css('--ink2')}},
      {x:-70.322,y:43.433,text:'Biddeford Pool',showarrow:false,font:{size:11,color:css('--ink2')}},{x:-70.398,y:43.522,text:'Old Orchard Beach',xanchor:'right',showarrow:false,font:{size:11,color:css('--ink2')}},
      {x:-70.292,y:43.389,text:'coastline © OpenStreetMap',showarrow:false,font:{size:9,color:css('--muted')},xanchor:'right'}]})); };
function calc(){ const out=document.getElementById('calcout'); if(!out) return; const v=id=>parseFloat(document.getElementById(id).value);
  const W=v('c-w'),h=v('c-h'),U=v('c-u'),Q=v('c-q'),S=v('c-s'),dS=v('c-ds'),So=v('c-so'), om=2*Math.PI/(12.4206*3600), gg=9.81;
  if([W,h,U,Q,S,dS,So].some(x=>!isFinite(x)||x<=0)){ out.innerHTML='<tr><td>Enter a positive number in every box.</td></tr>'; return; }
  const L=2*U/om, grad=dS/L, A=W*h, Kx=Q*S/(A*grad), Ri=(gg*7.7e-4*So)*Q/(W*U**3), reg=Ri<0.08?'well mixed':Ri<0.8?'partially mixed':'strongly layered (salt wedge)';
  out.innerHTML=`<tr><th>Result</th><th>Value</th></tr><tr><td>How far the tide carries water (tidal excursion)</td><td>${(L/1000).toFixed(1)} km</td></tr>
   <tr><td>Salinity change along the estuary ∂S/∂x</td><td>${(grad*1000).toFixed(2)} PSU per km</td></tr><tr><td>Horizontal mixing K<sub>x</sub></td><td>${Kx.toLocaleString(undefined,{maximumFractionDigits:0})} m²/s</td></tr>
   <tr><td>Estuarine Richardson number Ri<sub>E</sub></td><td>${Ri.toFixed(2)}: <span class="regime">${reg}</span></td></tr><tr><td>Share of fresh water at Jordan Point</td><td>${(Math.max(0,1-S/So)*100).toFixed(0)}%</td></tr>`; }
document.querySelectorAll('#calc input').forEach(i=>i.addEventListener('input',calc));
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{ v8=b.dataset.v; CH.anova(); });

function drawAll(){ texts(); for(const k in CH){ try{ CH[k](); }catch(e){ console.warn('chart',k,e); } } calc(); }
function setUnit(u){ unit=u; try{localStorage.setItem('une-units',u==='si'?'metric':'imperial')}catch(e){} drawAll(); }
document.getElementById('u-us').onclick=()=>setUnit('us'); document.getElementById('u-si').onclick=()=>setUnit('si');
function curTheme(){ const r=document.documentElement; return r.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); }
function syncTheme(){ const t=curTheme(); document.getElementById('th-light').setAttribute('aria-pressed',t==='light'); document.getElementById('th-dark').setAttribute('aria-pressed',t==='dark'); }
function setTheme(t){ document.documentElement.dataset.theme=t; try{localStorage.setItem('buoy-theme',t)}catch(e){} syncTheme(); drawAll(); }
document.getElementById('th-light').onclick=()=>setTheme('light'); document.getElementById('th-dark').onclick=()=>setTheme('dark');
try{ const t=localStorage.getItem('buoy-theme'); if(t) document.documentElement.dataset.theme=t; }catch(e){}
syncTheme();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{ syncTheme(); drawAll(); });
if (window.Plotly) drawAll(); else window.addEventListener('load',()=>window.Plotly&&drawAll());
