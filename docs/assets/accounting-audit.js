/* Display the actual simulated holdings separately from archived targets. */
metrics = function(values) {
  const v = values.filter(Number.isFinite);
  if (!v.length) return {};
  let peak = v[0], dd = 0;
  for (const x of v) { peak = Math.max(peak, x); dd = Math.min(dd, x/peak-1); }
  const r = v.slice(1).map((x,i) => x/v[i]-1).slice(-20);
  const mean = r.reduce((a,b)=>a+b,0)/r.length;
  const variance = r.length === 20 ? r.reduce((a,b)=>a+(b-mean)**2,0)/19 : NaN;
  return {since:v.at(-1)/v[0]-1, r5:v.length>5?v.at(-1)/v.at(-6)-1:NaN,
    r20:v.length>20?v.at(-1)/v.at(-21)-1:NaN, dd, vol20:Math.sqrt(variance*252), last:v.at(-1)};
};
renderSummary = function(series,startEur,dates=[]) {
  const box=document.querySelector("#summary");
  if (!box) return;
  box.innerHTML=series.map(s=>{
    const m=metrics(s.values), first=dates[s.values.findIndex(Number.isFinite)];
    return '<article class="metric"><span>'+htmlEscape(s.label)+'</span><b>'+pct(m.since)+
      '</b><small>'+(first?'Depuis le '+formatDate(first):'Depuis le début de cette série')+
      ' · base '+(Number.isFinite(m.last)?m.last.toFixed(2):'—')+'</small></article>';
  }).join("");
};
renderStrategyDetails = function(strategies,decisions=[]) {
  const box=document.querySelector("#strategy-details"); if(!box) return;
  box.innerHTML=Object.entries(strategies).map(([id,s])=>{
    const d=decisions.find(x=>x.strategy_id===id);
    const positions=(s.holdings||[]).map(h=>'<li>'+htmlEscape(h.name)+' : '+Number(h.weight_pct).toFixed(2)+' %</li>').join("");
    const targets=d?Object.entries(d.target_allocation_percent||{}).map(([a,w])=>'<li>'+htmlEscape(a)+' : '+Number(w).toFixed(2)+' %</li>').join(""):"";
    const moves=d?.mouvements;
    const changed=moves?Object.values(moves).flat():[];
    const changes=d?'<h4>Ce que cette revue change</h4><p>'+
      (["maintain","no_change"].includes(d.decision_type)?"Aucun achat ni vente prévu : les titres sont conservés.":
      changed.length?changed.map(m=>htmlEscape(m.asset)+' : '+m.from_percent+' % → '+m.to_percent+' %').join('<br>'):
      "Les proportions cibles sont indiquées ci-dessous ; aucun écart avec une cible précédente n’est disponible.")+
      '</p>':"";
    return '<article class="strategy"><h3>'+htmlEscape(s.label)+'</h3><p>'+htmlEscape(s.resume||"")+
      '</p><p>'+htmlEscape(s.objectif||"")+'</p><p>'+htmlEscape(s.regle||"")+'</p><p>'+htmlEscape(s.frequence||"")+
      '</p><p>'+htmlEscape(s.faiblesse||"")+'</p><h4>Positions simulées à la dernière valorisation</h4><ul>'+positions+
      '</ul><p>Les proportions évoluent avec les cours entre deux arbitrages.</p>'+
      (d?'<details><summary>Dernière revue enregistrée'+(d.decided_at?' le '+formatDate(d.decided_at):'')+
        ' — date d’effet '+formatDate(d.date)+'</summary><p>'+htmlEscape(d.rationale||"")+
        '</p>'+changes+'<h4>Proportions cibles archivées</h4><ul>'+targets+'</ul>'+
        (d.warnings||[]).map(w=>'<p>'+htmlEscape(w)+'</p>').join("")+'</details>':"")+
      '<p>'+htmlEscape(s.statut_public||"")+'</p></article>';
  }).join("");
};
const originalInitDashboard = initDashboard;
initDashboard = async function(path) {
  await originalInitDashboard(path);
  const data=await loadJSON(path);
  renderDecisionHistory(data.decision_history,data.strategies||{});
  renderSummary((data.series||[]).slice().sort((a,b)=>a.label.localeCompare(b.label,"fr")),null,data.dates||[]);
  const received=(data.decision_history||[]).map(d=>d.decided_at).filter(Boolean).sort().at(-1);
  if(received && document.querySelector("#review-banner")) {
    const p=document.createElement("p");
    p.textContent="Dernière revue effectivement enregistrée le "+formatDate(received)+
      ". Les dates d’effet affichées tiennent compte de la réception réelle.";
    document.querySelector("#review-banner").append(p);
  }
  const note=document.createElement("section"); note.className="card";
  note.innerHTML='<h2>Comment lire ces résultats</h2><p>Calcul corrigé le 20 octobre 2026 : les positions sont conservées entre arbitrages et les nouveaux titres ne produisent un rendement qu’après leur prix d’exécution. Les décisions anciennes sont conservées.</p>'+
    '<p>Les frais propres au contrat et les délais réels d’exécution ne sont pas connus avec précision. Les résultats sont des simulations. Les premiers points ChatGPT proviennent en partie de décisions reconstituées ; les données macro historiques peuvent avoir été révisées. La volatilité sur 20 séances reste vide tant que 20 rendements ne sont pas disponibles.</p>'+
    '<p>Les revues académiques contrôlent les règles ; leurs courbes sont calculées à partir de ces règles. Les proportions cibles archivées et les poids valorisés peuvent donc différer.</p>'+
    '<p><a href="audit-calculs.html">Corrections, limites et contrôles détaillés</a></p>';
  document.querySelector("main").prepend(note);
  const status=document.querySelector("#status");
  if(status && data.freshness) {
    const rows=Object.values(data.freshness.holdings).flat();
    const delayed=rows.filter(r=>!r.price_date || r.price_date<data.freshness.as_of);
    const unique=[...new Map(delayed.map(r=>[r.asset_id,r])).values()];
    status.textContent="Valorisation simulée au "+formatDate(data.freshness.as_of)+". "+
      (unique.length?"Derniers cours conservés pour : "+unique.map(r=>r.name+" ("+
        (r.price_date?formatDate(r.price_date):"cours manquant")+")").join(" ; ")+".":"Tous les supports détenus disposent d’un cours à cette date.")+
      " Données générées le "+formatDate(data.generated_at)+".";
  }
};
initOverview = async function(paths) {
  const data=await Promise.all(paths.map(loadJSON));
  const all=new Map();
  for(const d of data) for(const s of d.series||[]) all.set(s.label,{
    label:s.label, byDate:new Map(d.dates.map((dt,i)=>[dt,s.values[i]]))});
  const members=[...all.values()];
  const dates=[...new Set(data.flatMap(d=>d.dates))].sort()
    .filter(dt=>members.every(s=>Number.isFinite(s.byDate.get(dt))));
  if(!dates.length) throw new Error("Aucune fenêtre commune disponible");
  const normalised=members.map(s=>({label:s.label,values:dates.map(d=>100*s.byDate.get(d)/s.byDate.get(dates[0]))}));
  const groups=[
    {title:"Bernard origine",members:normalised.filter(s=>s.label==="Bernard origine"),href:""},
    {title:"Références académiques",members:normalised.filter(s=>ACADEMIC.includes(s.label)),href:"academic.html"},
    {title:"ChatGPT",members:normalised.filter(s=>s.label.startsWith("ChatGPT ")),href:"chatgpt.html"},
    {title:"Claude",members:normalised.filter(s=>s.label.startsWith("Claude ")),href:"claude.html"}
  ].filter(g=>g.members.length);
  for(const g of groups) {
    g.summary=average(g.title+" — "+g.members.length+" série(s)",g.members,dates);
    g.description=g.title==="Bernard origine"?"Portefeuille de référence initial, conservé pour comparer les stratégies.":
      "Moyenne à composition constante sur la fenêtre commune ; ce n’est pas un portefeuille investi.";
  }
  const series=groups.map(g=>g.summary);
  renderChart(dates,series,null); renderSummary(series,null,dates); renderTable(series,null,dates); renderGroups(groups);
  document.querySelector("#status").textContent="Comparaison sur la même période : "+
    formatDate(dates[0])+" au "+formatDate(dates.at(-1))+". Toutes les séries sont ramenées à 100 au début de cette fenêtre.";
  const review=await loadReviewStatus(); renderReviewBanner(review);
};
const originalRenderReviewBanner = renderReviewBanner;
renderReviewBanner = function(review) {
  originalRenderReviewBanner(review);
  const box=document.querySelector("#review-banner");
  if(box) {
    box.innerHTML=box.innerHTML.replaceAll("samedi samedi","samedi");
    if(review?.updated_at) {
      const p=document.createElement("p");
      p.textContent="État enregistré le "+formatDate(review.updated_at)+
        ". La date prévue de la revue et sa date de traitement peuvent être différentes.";
      box.append(p);
    }
  }
};
renderDecisionHistory = function(decisions,strategies={}) {
  const box=document.querySelector("#history-body"); if(!box)return;
  const labels={maintain:"Allocation conservée",no_change:"Allocation conservée",
    rebalance:"Nouvelle allocation",reconstructed_allocation:"Départ reconstitué"};
  box.innerHTML=(decisions||[]).map(d=>'<tr><td>'+
    (d.decided_at?'Revue enregistrée le '+formatDate(d.decided_at)+'<br>':"")+
    'Effet simulé : '+formatDate(d.date)+'</td><td>'+htmlEscape(strategies[d.strategy_id]?.label||d.strategy_id)+
    '</td><td>'+htmlEscape(d.strategy_version||"")+'</td><td>'+htmlEscape(labels[d.decision_type]||d.decision_type)+
    '</td><td>'+htmlEscape(d.rationale||"")+(d.warnings||[]).map(w=>'<p>'+htmlEscape(w)+'</p>').join("")+
    '</td><td>'+Object.entries(d.target_allocation_percent||{}).map(([a,w])=>htmlEscape(a)+' : '+Number(w).toFixed(2)+' %').join('<br>')+'</td></tr>').join("");
};
initBacktestResults = async function(path) {
  const data=await loadJSON(path),box=document.querySelector("#backtest-results");
  if(!box)return;
  box.innerHTML='<p>Calcul corrigé : achats à la valorisation suivante, positions conservées entre décisions. Tests exploratoires, hors frais du contrat ; univers actuel et données macro potentiellement révisées.</p>'+
    (data.results||[]).map(r=>{
      const m=r.metrics||{};
      if(r.status==="unavailable")return '<article><h3>'+htmlEscape(r.strategy_id)+
        '</h3><p>Résultat indisponible : un support ne dispose pas de prix à la date d’exécution simulée.</p><p>'+htmlEscape(r.reason)+'</p></article>';
      return '<article><h3>'+htmlEscape(r.label||r.strategy_id)+'</h3><p>'+
        formatDate(m.start)+' au '+formatDate(m.end)+' — indice final : '+Number(m.final_value).toFixed(2)+
        ' ; rendement annuel : '+pct(m.annualized_return)+' ; pire baisse : '+pct(m.max_drawdown)+
        ' ; volatilité annuelle : '+pct(m.annualized_volatility)+'.</p></article>';
    }).join("");
};
