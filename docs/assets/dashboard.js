async function loadJSON(path){const r=await fetch(path,{cache:"no-store"});if(!r.ok)throw new Error(path);return r.json();}
function pct(x){return Number.isFinite(x)?(100*x).toFixed(2)+" %":"—";}
function euro(x){return Number.isFinite(x)?new Intl.NumberFormat("fr-FR",{style:"currency",currency:"EUR",maximumFractionDigits:0}).format(x):"—";}
function metrics(values){
  const v=values.filter(Number.isFinite); if(v.length<2)return {};
  const r=v.slice(1).map((x,i)=>x/v[i]-1);
  let peak=v[0],dd=0; for(const x of v){peak=Math.max(peak,x);dd=Math.min(dd,x/peak-1);}
  const ret=(n)=>v.length>n?v[v.length-1]/v[v.length-1-n]-1:NaN;
  const last20=r.slice(-20); const mean=last20.reduce((a,b)=>a+b,0)/(last20.length||1);
  const variance=last20.length>1?last20.reduce((a,b)=>a+(b-mean)**2,0)/(last20.length-1):NaN;
  return {since:v[v.length-1]/v[0]-1,r5:ret(5),r20:ret(20),dd:dd,vol20:Number.isFinite(variance)?Math.sqrt(variance)*Math.sqrt(252):NaN,last:v[v.length-1]};
}
function renderSummary(series,startEur){
  const box=document.querySelector("#summary"); if(!box)return; box.innerHTML="";
  for(const s of series){
    const m=metrics(s.values); const d=document.createElement("div"); d.className="metric";
    d.innerHTML="<span>"+s.label+"</span><b>"+pct(m.since)+"</b><small>Depuis l'origine"+(startEur?" · "+euro(startEur*m.last/100):"")+"</small>";
    box.appendChild(d);
  }
}
function renderTable(series,startEur){
  const t=document.querySelector("#metrics-body"); if(!t)return; t.innerHTML="";
  for(const s of series){
    const m=metrics(s.values); const tr=document.createElement("tr");
    tr.innerHTML="<td>"+s.label+"</td><td>"+pct(m.since)+"</td><td>"+pct(m.r5)+"</td><td>"+pct(m.r20)+"</td><td>"+pct(m.dd)+"</td><td>"+pct(m.vol20)+"</td><td>"+(startEur?euro(startEur*m.last/100):(Number.isFinite(m.last)?m.last.toFixed(2):"—"))+"</td>";
    t.appendChild(tr);
  }
}
function renderChart(labels,series,startEur){
  const ctx=document.querySelector("#comparison-chart"); if(!ctx)return;
  new Chart(ctx,{type:"line",data:{labels:labels,datasets:series.map(s=>({label:s.label,data:s.values,borderWidth:2,pointRadius:0,tension:.1}))},options:{responsive:true,interaction:{mode:"index",intersect:false},plugins:{tooltip:{callbacks:{label:(c)=>startEur?c.dataset.label+": "+euro(startEur*c.parsed.y/100):c.dataset.label+": "+c.parsed.y.toFixed(2)}}},scales:{y:{title:{display:true,text:startEur?"Valeur théorique (€)":"Base 100"}}}}});
}
async function initDashboard(dataPath){
  const data=await loadJSON(dataPath); const labels=data.dates||[];
  const series=(data.series||[]).map(s=>({label:s.label,values:s.values}));
  renderChart(labels,series,data.start_eur||null); renderSummary(series,data.start_eur||null); renderTable(series,data.start_eur||null);
  const status=document.querySelector("#status"); if(status)status.textContent=data.generated_at?"Mise à jour : "+data.generated_at:"";
}