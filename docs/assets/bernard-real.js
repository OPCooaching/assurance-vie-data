// Independent chart: the observed portfolio never replaces the origin witness.
(async function () {
  const host = document.querySelector('main');
  if (!host) return;
  const response = await fetch('data/bernard-real.json', {cache: 'no-store'});
  if (!response.ok) throw new Error('Suivi réel indisponible');
  const data = await response.json();
  const snapshot = data.latest_snapshot;
  const segment = data.segments.at(-1);
  const last = segment.valuations.at(-1);
  const section = document.createElement('section');
  section.className = 'card';
  section.id = 'bernard-real';
  const esc = text => String(text).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const money = n => Number(n).toLocaleString('fr-FR', {style:'currency',currency:'EUR'});
  const date = d => String(d).split('-').reverse().join('/');
  section.innerHTML = '<h2>Portefeuille réel de Bernard</h2>' +
    '<p>Relevé du <strong>' + date(snapshot.as_of_date) + '</strong> : <strong>' + money(snapshot.total_eur) + '</strong>. ' +
    'Les nouvelles positions servent au suivi à partir de ce relevé. Le portefeuille d’origine et les décisions théoriques restent conservés.</p>' +
    '<p>' + (last.status === 'observed' ? 'Dernier point observé' : 'Dernière valeur estimée') + ' au ' + date(last.date) + ' : <strong>' + money(last.value_eur) + '</strong>.</p>' +
    '<p class="muted">Comparaison en base 100 au ' + date(snapshot.as_of_date) + '. Après le relevé, la courbe du portefeuille réel est une estimation sur les positions connues. Les retraits effectivement réalisés et les prochains relevés permettront de la rapprocher du contrat.</p>' +
    '<div style="height:340px"><canvas aria-label="Suivi du portefeuille réel depuis le dernier relevé" role="img"></canvas></div>' +
    '<details><summary>Positions du dernier relevé et limites</summary><div class="table-wrap"><table><thead><tr><th>Support</th><th>Montant observé</th><th>Poids</th></tr></thead><tbody>' +
    snapshot.holdings.map(h => '<tr><td>' + esc(h.support_name) + '</td><td>' + money(h.value_eur) + '</td><td>' + (100*h.value_eur/snapshot.total_eur).toFixed(2) + ' %</td></tr>').join('') +
    '</tbody></table></div><p>Netissima est conservé à sa valeur constatée jusqu’aux intérêts confirmés. Les prix de référence du relevé sont arrondis. Les frais et retraits futurs ne sont pas anticipés. Les courbes théoriques sont recalées sur leur dernier point publié avant le relevé. Les données manquantes restent signalées.</p></details>';
  const banner = document.querySelector('#review-banner');
  if (banner) banner.after(section); else host.prepend(section);
  if (last.pending_supports.length) {
    const warning = document.createElement('p');
    warning.className = 'muted';
    warning.textContent = 'Valorisation provisoire : ' + last.pending_supports.length + ' support(s) utilisent un cours antérieur.';
    section.append(warning);
  }
  if (typeof Chart !== 'undefined') new Chart(section.querySelector('canvas'), {
    type:'line', data:{labels:segment.dates, datasets:segment.series.map((s,i) => ({
      label:s.label, data:s.values, borderColor:i === 0 ? '#35c78a' : ['#99abb8','#ffd166','#a78bfa','#38bdf8','#e05263'][i%5],
      borderWidth:i === 0 ? 4 : 2, pointRadius:segment.dates.length < 10 ? 3 : 0,
      spanGaps:false, hidden:i > 1, fill:false
    }))}, options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
      plugins:{legend:{labels:{color:'#99abb8'}}},scales:{x:{ticks:{color:'#99abb8'}},y:{ticks:{color:'#99abb8'},title:{display:true,text:'Base 100 au dernier relevé',color:'#99abb8'}}}
  }});
})().catch(error => {
  console.error('Bernard réel:', error);
  const p = document.createElement('p');
  p.textContent = 'Le suivi du portefeuille réel n’a pas pu être chargé.';
  document.querySelector('main')?.prepend(p);
});
