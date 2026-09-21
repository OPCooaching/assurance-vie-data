const STRATEGY_COLORS={
"Bernard origine":"#f6bd60","60/40 mondial adapté":"#e76f51","Harry Browne adapté":"#457b9d","Faber Trend 10 mois":"#2a9d8f","Momentum académique 12 mois":"#8f5fbf",
"ChatGPT A — Momentum hebdomadaire":"#8ecae6","ChatGPT B — Momentum adaptatif":"#4cc9f0","ChatGPT C — Momentum diversifié":"#4895ef",
"Claude A — Socle mondial et satellites":"#e76f51","Claude B — Risque cible constant":"#6c63ff","Claude C — Tendance confirmée par l’ampleur":"#2a9d8f","Claude D — Momentum multi-horizon":"#ff9f1c","Claude E — Momentum sous garde-fou":"#ec4899",
"Repère académique (moyenne)":"#2a9d8f","ChatGPT (moyenne des 3)":"#4cc9f0","Claude (moyenne des 5)":"#f4a261"};
const FALLBACK=["#8ecae6","#ffb703","#fb8500","#90be6d","#c77dff"];
const ACADEMIC=["60/40 mondial adapté","Harry Browne adapté","Faber Trend 10 mois","Momentum académique 12 mois"];
let activeChart;
const colorFor=(label,i=0)=>STRATEGY_COLORS[label]||FALLBACK[i%FALLBACK.length];
async function loadJSON(path){const r=await fetch(path,{cache:"no-store"});if(!r.ok)throw new Error(path);return r.json();}
const pct=x=>Number.isFinite(x)?(100*x).toFixed(2)+" %":"—";
const swatch=(label,i=0)=>'<span class="swatch" style="background:'+colorFor(label,i)+'"></span>';
function metrics(values){const v=values.filter(Number.isFinite);if(!v.length)return{};if(v.length===1)return{since:0,r5:NaN,r20:NaN,dd:0,vol20:NaN,last:v[0]};const r=v.slice(1).map((x,i)=>x/v[i]-1);let peak=v[0],dd=0;for(const x of v){peak=Math.max(peak,x);dd=Math.min(dd,x/peak-1);}const ret=n=>v.length>n?v.at(-1)/v.at(-1-n)-1:NaN,last=r.slice(-20),mean=last.reduce((a,b)=>a+b,0)/(last.length||1),variance=last.length>1?last.reduce((a,b)=>a+(b-mean)**2,0)/(last.length-1):NaN;return{since:v.at(-1)/v[0]-1,r5:ret(5),r20:ret(20),dd,vol20:Number.isFinite(variance)?Math.sqrt(variance)*Math.sqrt(252):NaN,last:v.at(-1)};}
function renderSummary(series){const box=document.querySelector("#summary");if(box)box.innerHTML=series.map((s,i)=>{const m=metrics(s.values);return '<article class="metric"><span class="eyebrow">'+swatch(s.label,i)+s.label+'</span><b>'+pct(m.since)+'</b><small>Depuis le 09/09/2026 · base '+(Number.isFinite(m.last)?m.last.toFixed(2):"—")+'</small></article>';}).join("");}
function renderTable(series){const body=document.querySelector("#metrics-body");if(body)body.innerHTML=series.map((s,i)=>{const m=metrics(s.values);return '<tr><td>'+swatch(s.label,i)+s.label+'</td><td>'+pct(m.since)+'</td><td>'+pct(m.r5)+'</td><td>'+pct(m.r20)+'</td><td>'+pct(m.dd)+'</td><td>'+pct(m.vol20)+'</td><td>'+(Number.isFinite(m.last)?m.last.toFixed(2):"—")+'</td></tr>';}).join("");}
function renderLegend(series){const box=document.querySelector("#chart-legend");if(box)box.innerHTML=series.map((s,i)=>'<span>'+swatch(s.label,i)+s.label+'</span>').join("");}
function renderChart(labels,series){const canvas=document.querySelector("#comparison-chart");if(!canvas)return;renderLegend(series);if(activeChart)activeChart.destroy();activeChart=new Chart(canvas,{type:"line",data:{labels,datasets:series.map((s,i)=>({label:s.label,data:s.values,borderColor:colorFor(s.label,i),backgroundColor:colorFor(s.label,i),borderWidth:s.label==="Bernard origine"?4:2.5,pointRadius:labels.length<12?3:0,pointHoverRadius:6,tension:.28,spanGaps:true,fill:false}))},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:"index",intersect:false},plugins:{legend:{display:false},tooltip:{padding:12,callbacks:{label:c=>c.dataset.label+": "+c.parsed.y.toFixed(2)}}},scales:{x:{grid:{display:false},ticks:{color:"#99abb8",maxRotation:0}},y:{grid:{color:"rgba(148,163,184,.14)"},ticks:{color:"#99abb8"},title:{display:true,text:"Indice base 100",color:"#99abb8"}}}}});}
function renderStrategyDetails(strategies){const box=document.querySelector("#strategy-details");if(!box)return;const list=Array.isArray(strategies)?strategies:Object.entries(strategies||{}).map(([id,s])=>({...s,id}));box.innerHTML=list.map((s,i)=>{const holdings=(s.holdings||[]).map(h=>'<li><span>'+h.name+'</span><b>'+Number(h.weight_pct).toFixed(2)+' %</b></li>').join("");return '<article class="strategy"><div class="strategy-title">'+swatch(s.label,i)+'<div><h3>'+s.label+'</h3><small>'+[s.version,s.status].filter(Boolean).join(" · ")+'</small></div></div>'+(s.resume||s.short?'<p>'+(s.resume||s.short)+'</p>':"")+(s.objectif||s.objective?'<p><strong>But.</strong> '+(s.objectif||s.objective)+'</p>':"")+(s.regle||s.main_rule?'<p><strong>Règle de sélection et de remplacement.</strong> '+(s.regle||s.main_rule)+'</p>':"")+(s.frequence?'<p><strong>Quand cela peut changer.</strong> '+s.frequence+'</p>':"")+(s.faiblesse?'<p class="muted"><strong>Point de vigilance.</strong> '+s.faiblesse+'</p>':"")+(holdings?'<div class="holdings"><h4>Allocation de la dernière revue</h4><ul>'+holdings+'</ul></div>':'<p class="muted">Allocation en attente de la prochaine revue.</p>')+(s.statut_public?'<p class="status-note">'+s.statut_public+'</p>':"")+'</article>';}).join("")||'<p class="muted">Aucune stratégie documentée.</p>';}
function setStatus(data){const e=document.querySelector("#status");if(e)e.textContent=data.generated_at?"Données mises à jour le "+new Date(data.generated_at).toLocaleString("fr-FR"):"";}
async function initDashboard(path){const data=await loadJSON(path),series=data.series||[];renderChart(data.dates||[],series);renderSummary(series);renderTable(series);renderStrategyDetails(data.strategies||{});setStatus(data);}
function average(label,items,dates){return{label,values:dates.map((_,i)=>{const v=items.map(s=>s.values[i]).filter(Number.isFinite);return v.length?v.reduce((a,b)=>a+b,0)/v.length:null;})};}
function renderGroups(groups){const box=document.querySelector("#group-breakdown");if(!box)return;box.innerHTML=groups.filter(g=>g.members.length).map((g,i)=>'<article class="group-card group-'+i+'"><span class="eyebrow">'+swatch(g.summary.label,i)+g.title+'</span><strong>'+g.members.length+' '+(g.members.length>1?"stratégies":"stratégie")+'</strong><p>'+g.description+'</p><div class="strategy-tags">'+g.members.map(s=>'<span>'+s.label+'</span>').join("")+'</div>'+(g.href?'<a href="'+g.href+'">Voir le détail →</a>':"")+'</article>').join("");}
async function initOverview(paths){const data=await Promise.all(paths.map(loadJSON)),dates=[...new Set(data.flatMap(d=>d.dates||[]))].sort(),all=new Map();for(const d of data)(d.series||[]).forEach(s=>{const m=new Map();(d.dates||[]).forEach((dt,i)=>m.set(dt,s.values[i]));all.set(s.label,{label:s.label,values:dates.map(dt=>m.get(dt)??null)});});const bernard=all.get("Bernard origine"),academic=ACADEMIC.map(x=>all.get(x)).filter(Boolean),chatgpt=[...all.values()].filter(s=>s.label.startsWith("ChatGPT ")),claude=[...all.values()].filter(s=>s.label.startsWith("Claude "));const groups=[{title:"Bernard",description:"Le portefeuille suivi tel qu’il était au départ.",members:bernard?[bernard]:[],summary:bernard},{title:"Références académiques",description:"Quatre règles de référence, regroupées pour une lecture simple.",members:academic,summary:average("Repère académique (moyenne)",academic,dates),href:"academic.html"},{title:"Stratégies ChatGPT",description:"Trois approches suivies avec la même poche de marché.",members:chatgpt,summary:average("ChatGPT (moyenne des 3)",chatgpt,dates),href:"chatgpt.html"},{title:"Stratégies Claude",description:"Cinq approches suivies dans la même enveloppe de risque.",members:claude,summary:average("Claude (moyenne des 5)",claude,dates),href:"claude.html"}],display=groups.filter(g=>g.summary&&g.members.length).map(g=>g.summary);renderChart(dates,display);renderSummary(display);renderTable(display);renderGroups(groups);const e=document.querySelector("#status");if(e)e.textContent="Lecture simplifiée · dernière valorisation commune : "+(dates.at(-1)||"—");}

const htmlEscape=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
const percent=value=>Number.isFinite(value)?(value*100).toFixed(1)+" %":"—";
const whole=value=>Number.isFinite(value)?value.toFixed(0)+" / 100":"—";
const screenerCharts=[];
const SCREENER_COLORS=["#2a9d8f","#f6bd60","#8f5fbf","#e76f51","#4cc9f0"];
const statusLabel=status=>({
  "analysable par les prix":"Oui : assez de prix réels",
  "hors screener de marché":"Non : prix non comparable",
  "historique insuffisant":"Pas encore : historique trop court",
  "données à résoudre":"À résoudre : cotation manquante",
  "devise à vérifier":"À vérifier : devise de cotation",
}[status]||status);
function renderScreenerRows(rows){
  const body=document.querySelector("#screener-body");
  if(!body)return;
  body.innerHTML=rows.map(row=>'<tr><td><strong>'+htmlEscape(row.name)+'</strong><span class="table-sub">'+htmlEscape(row.asset_id)+(row.symbol?" · "+htmlEscape(row.symbol):"")+'</span></td><td>'+htmlEscape(row.category)+'</td><td><span class="status-pill">'+htmlEscape(statusLabel(row.status))+'</span><span class="table-sub">'+htmlEscape(row.note)+'</span></td><td>'+whole(row.market_observation_score)+'</td><td>'+percent(row.ret_20d)+'</td><td>'+percent(row.ret_60d)+'</td><td>'+percent(row.ret_120d)+'</td><td>'+percent(row.vol_60d_ann)+'</td><td>'+percent(row.drawdown_252d)+'</td><td>'+(row.volume_available?(Number.isFinite(row.volume_ratio_20d)?htmlEscape(row.volume_ratio_20d.toFixed(1))+" × sa moyenne":"donnée présente"):"—")+'</td></tr>').join("")||'<tr><td colspan="10">Aucun support ne correspond à ce filtre.</td></tr>';
}
function destroyScreenerCharts(){while(screenerCharts.length)screenerCharts.pop().destroy();}
function addScreenerChart(canvas,config){if(canvas&&typeof Chart!=="undefined")screenerCharts.push(new Chart(canvas,config));}
function renderScreenerVisuals(rows){
  if(typeof Chart==="undefined")return;
  destroyScreenerCharts();

  const states=["analysable par les prix","hors screener de marché","historique insuffisant","données à résoudre","devise à vérifier"];
  const availableStates=states.filter(status=>rows.some(row=>row.status===status));
  const coverageConfig={
    type:"doughnut",
    data:{
      labels:availableStates.map(status=>statusLabel(status)),
      datasets:[{
        data:availableStates.map(status=>rows.filter(row=>row.status===status).length),
        backgroundColor:SCREENER_COLORS,
        borderColor:"#10212c",
        borderWidth:3,
      }],
    },
    options:{
      responsive:true,
      maintainAspectRatio:false,
      plugins:{
        legend:{position:"bottom",labels:{color:"#dce7eb",font:{size:16},padding:18,boxWidth:15}},
        tooltip:{callbacks:{label:context=>context.label+": "+context.parsed+" supports"}},
      },
    },
  };
  addScreenerChart(document.querySelector("#coverage-chart"),coverageConfig);

  const top=rows
    .filter(row=>Number.isFinite(row.market_observation_score))
    .sort((a,b)=>b.market_observation_score-a.market_observation_score)
    .slice(0,10);
  const topConfig={
    type:"bar",
    data:{
      labels:top.map(row=>row.name),
      datasets:[{
        label:"Profil actuel",
        data:top.map(row=>row.market_observation_score),
        backgroundColor:"#f6bd60",
        borderRadius:7,
        borderSkipped:false,
      }],
    },
    options:{
      indexAxis:"y",
      responsive:true,
      maintainAspectRatio:false,
      plugins:{
        legend:{display:false},
        tooltip:{callbacks:{label:context=>context.parsed.x.toFixed(0)+" / 100 · profil calculé avec les prix"}},
      },
      scales:{
        x:{
          min:0,max:100,
          title:{display:true,text:"Profil actuel : tendance des prix + moindre instabilité",color:"#cbd9df",font:{size:14}},
          grid:{color:"rgba(148,163,184,.14)"},
          ticks:{color:"#dce7eb",font:{size:13}},
        },
        y:{grid:{display:false},ticks:{color:"#e8f0f4",font:{size:13}}},
      },
    },
  };
  addScreenerChart(document.querySelector("#top-chart"),topConfig);

  const points=rows
    .filter(row=>Number.isFinite(row.trend_score)&&Number.isFinite(row.stability_score))
    .map(row=>({x:row.stability_score,y:row.trend_score,name:row.name}));
  const mapConfig={
    type:"scatter",
    data:{datasets:[{
      data:points,
      backgroundColor:"rgba(76,201,240,.75)",
      borderColor:"#4cc9f0",
      pointRadius:4,
      pointHoverRadius:7,
    }]},
    options:{
      responsive:true,
      maintainAspectRatio:false,
      plugins:{
        legend:{display:false},
        tooltip:{callbacks:{label:context=>context.raw.name+" · progression "+context.raw.y.toFixed(0)+" / 100 · moins de secousses "+context.raw.x.toFixed(0)+" / 100"}},
      },
      scales:{
        x:{
          min:0,max:100,
          title:{display:true,text:"À droite : prix moins secoués et moins de forte baisse",color:"#dce7eb",font:{size:14}},
          grid:{color:"rgba(148,163,184,.14)"},
          ticks:{color:"#dce7eb",font:{size:13}},
        },
        y:{
          min:0,max:100,
          title:{display:true,text:"En haut : prix en hausse sur 1, 3 et 6 mois",color:"#dce7eb",font:{size:14}},
          grid:{color:"rgba(148,163,184,.14)"},
          ticks:{color:"#dce7eb",font:{size:13}},
        },
      },
    },
  };
  addScreenerChart(document.querySelector("#map-chart"),mapConfig);
}
function initScreener(path){return loadJSON(path).then(data=>{
  const rows=data.rows||[],counts=data.counts||{};
  const status=document.querySelector("#screener-status");
  if(status)status.textContent="Données de marché arrêtées au "+htmlEscape(data.as_of_date||"—")+" · actualisées automatiquement chaque jour ouvré.";
  const count=document.querySelector("#screener-counts");
  if(count)count.innerHTML=[
    ["Tous les supports du contrat",counts.total_supports,"Ils sont tous recensés ; rien n’est masqué."],
    ["Supports comparables aujourd’hui",counts.price_analysable,"Ils ont au moins six mois de prix réels, donc on peut comparer leur parcours."],
    ["Supports avec activité de cotation",counts.volume_analysable,"Le volume existe et peut aider à étudier les actions et ETF concernés."],
  ].map(([label,value,detail])=>'<article class="metric"><span class="eyebrow">'+htmlEscape(label)+'</span><b>'+htmlEscape(value??"—")+'</b><small>'+htmlEscape(detail)+'</small></article>').join("");
  const contract=document.querySelector("#data-contract");
  if(contract)contract.innerHTML=[
    ["1. Ce que le prix a fait","Nous calculons la hausse ou la baisse sur un, trois et six mois. C’est utilisé dans le profil actuel pour savoir quels supports ont récemment progressé ou reculé."],
    ["2. À quel point le parcours a été mouvementé","Nous mesurons les variations des trois derniers mois et la pire baisse depuis le plus haut de l’année. Cela évite de ne regarder que les gagnants récents."],
    ["3. L’activité de cotation, quand elle existe","Pour certaines actions et ETF, on compare le volume du jour à sa moyenne. Ce repère n’est pas encore utilisé dans le profil : il servira à tester des stratégies différentes."],
  ].map(([title,text])=>'<article class="contract-card"><h3>'+htmlEscape(title)+'</h3><p>'+htmlEscape(text)+'</p></article>').join("");
  renderScreenerVisuals(rows);
  const search=document.querySelector("#screener-search"),filter=document.querySelector("#screener-filter");
  const refresh=()=>{const query=(search?.value||"").trim().toLocaleLowerCase("fr"),state=filter?.value||"";renderScreenerRows(rows.filter(row=>(!state||row.status===state)&&(!query||[row.name,row.asset_id,row.category,row.symbol].filter(Boolean).join(" ").toLocaleLowerCase("fr").includes(query))));};
  search?.addEventListener("input",refresh);filter?.addEventListener("change",refresh);refresh();
});}
