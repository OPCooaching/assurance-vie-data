const STRATEGY_COLORS={
  "Bernard origine":"#263238",
  "60/40 mondial adapté":"#d64545",
  "Harry Browne adapté":"#2f6db3",
  "Faber Trend 10 mois":"#2f8f5b",
  "Momentum académique 12 mois":"#d88a22",
  "ChatGPT Dynamique":"#7a4fb3",
  "ChatGPT Adaptative":"#008b95",
  "Claude 1":"#8b5e34",
  "Claude 2":"#b34f7d"
};
const FALLBACK_COLORS=["#6d7780","#8a6fb0","#2b7a78","#a56a43","#5a7d9a","#8a8a4a"];

async function loadJSON(path){
  const r=await fetch(path,{cache:"no-store"});
  if(!r.ok)throw new Error(path);
  return r.json();
}
function pct(x){return Number.isFinite(x)?(100*x).toFixed(2)+" %":"—";}
function euro(x){return Number.isFinite(x)?new Intl.NumberFormat("fr-FR",{style:"currency",currency:"EUR",maximumFractionDigits:0}).format(x):"—";}
function colorFor(label,index=0){return STRATEGY_COLORS[label]||FALLBACK_COLORS[index%FALLBACK_COLORS.length];}
function metrics(values){
  const v=values.filter(Number.isFinite);
  if(v.length===0)return {};
  if(v.length===1)return {since:0,r5:NaN,r20:NaN,dd:0,vol20:NaN,last:v[0]};
  const r=v.slice(1).map((x,i)=>x/v[i]-1);
  let peak=v[0],dd=0;
  for(const x of v){peak=Math.max(peak,x);dd=Math.min(dd,x/peak-1);}
  const ret=(n)=>v.length>n?v[v.length-1]/v[v.length-1-n]-1:NaN;
  const last20=r.slice(-20);
  const mean=last20.reduce((a,b)=>a+b,0)/(last20.length||1);
  const variance=last20.length>1?last20.reduce((a,b)=>a+(b-mean)**2,0)/(last20.length-1):NaN;
  return {since:v[v.length-1]/v[0]-1,r5:ret(5),r20:ret(20),dd,vol20:Number.isFinite(variance)?Math.sqrt(variance)*Math.sqrt(252):NaN,last:v[v.length-1]};
}
function swatch(label,index=0){
  return '<span class="swatch" style="background:'+colorFor(label,index)+'"></span>';
}
function renderSummary(series,startEur){
  const box=document.querySelector("#summary");
  if(!box)return;
  box.innerHTML="";
  series.forEach((s,i)=>{
    const m=metrics(s.values);
    const d=document.createElement("div");
    d.className="metric";
    d.innerHTML="<span>"+swatch(s.label,i)+s.label+"</span><b>"+pct(m.since)+"</b><small>Depuis l'origine"+(startEur&&Number.isFinite(m.last)?" · "+euro(startEur*m.last/100):"")+"</small>";
    box.appendChild(d);
  });
}
function renderTable(series,startEur){
  const t=document.querySelector("#metrics-body");
  if(!t)return;
  t.innerHTML="";
  series.forEach((s,i)=>{
    const m=metrics(s.values);
    const tr=document.createElement("tr");
    tr.innerHTML="<td>"+swatch(s.label,i)+s.label+"</td><td>"+pct(m.since)+"</td><td>"+pct(m.r5)+"</td><td>"+pct(m.r20)+"</td><td>"+pct(m.dd)+"</td><td>"+pct(m.vol20)+"</td><td>"+(startEur&&Number.isFinite(m.last)?euro(startEur*m.last/100):(Number.isFinite(m.last)?m.last.toFixed(2):"—"))+"</td>";
    t.appendChild(tr);
  });
}
function renderChart(labels,series,startEur){
  const ctx=document.querySelector("#comparison-chart");
  if(!ctx)return;
  const onePoint=labels.length<=1;
  new Chart(ctx,{
    type:"line",
    data:{
      labels,
      datasets:series.map((s,i)=>({
        label:s.label,
        data:s.values,
        borderColor:colorFor(s.label,i),
        backgroundColor:colorFor(s.label,i),
        borderWidth:2,
        pointRadius:onePoint?5:1.5,
        pointHoverRadius:5,
        spanGaps:true,
        tension:.1
      }))
    },
    options:{
      responsive:true,
      interaction:{mode:"index",intersect:false},
      plugins:{
        legend:{labels:{usePointStyle:true,pointStyle:"circle"}},
        tooltip:{callbacks:{label:(c)=>startEur?c.dataset.label+": "+euro(startEur*c.parsed.y/100):c.dataset.label+": "+c.parsed.y.toFixed(2)}}
      },
      scales:{y:{title:{display:true,text:startEur?"Valeur théorique (€)":"Base 100"}}}
    }
  });
}
function renderDetailSwatches(){
  document.querySelectorAll("[data-series-color]").forEach((el,i)=>{
    el.style.background=colorFor(el.dataset.seriesColor,i);
  });
}
async function initDashboard(dataPath){
  const data=await loadJSON(dataPath);
  const labels=data.dates||[];
  const series=(data.series||[]).map(s=>({label:s.label,values:s.values}));
  renderChart(labels,series,data.start_eur||null);
  renderSummary(series,data.start_eur||null);
  renderTable(series,data.start_eur||null);
  renderDetailSwatches();
  const status=document.querySelector("#status");
  if(status)status.textContent=data.generated_at?"Mise à jour : "+data.generated_at:"Point de départ : 07/09/2026";
}
async function initOverview(paths){
  const datasets=await Promise.all(paths.map(loadJSON));
  const allDates=[...new Set(datasets.flatMap(d=>d.dates||[]))].sort();
  const byLabel=new Map();
  for(const d of datasets){
    const dates=d.dates||[];
    for(const s of (d.series||[])){
      if(!byLabel.has(s.label))byLabel.set(s.label,new Map());
      const m=byLabel.get(s.label);
      dates.forEach((dt,i)=>{if(s.values[i]!==null&&s.values[i]!==undefined)m.set(dt,s.values[i]);});
    }
  }
  const series=[...byLabel.entries()].map(([label,m])=>({label,values:allDates.map(d=>m.has(d)?m.get(d):null)}));
  const startEur=datasets.find(d=>d.start_eur)?.start_eur||null;
  renderChart(allDates,series,startEur);
  renderSummary(series,startEur);
  renderTable(series,startEur);
  const status=document.querySelector("#status");
  if(status)status.textContent="Vue d'ensemble des stratégies";
}