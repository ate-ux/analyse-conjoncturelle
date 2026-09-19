/* ==========================================================================
  Graphique de projection, série observée + prévision
  Lit deux blocs JSON posés dans le gabarit :
   #serie-prevision : {periodes: [...], valeurs: [...]}
   #projection   : [{periode, valeur, bas, haut}, ...]
  ========================================================================== */
(function () {
 const cible = document.getElementById("graphique-prevision");
 if (!cible || typeof Chart === "undefined") return;

 const lire = (id) => {
  const el = document.getElementById(id);
  if (!el) return null;
  try { return JSON.parse(el.textContent); } catch (e) { return null; }
 };

 const serie = lire("serie-prevision");
 const projection = lire("projection");
 if (!serie || !serie.periodes) return;

 const etiquettes = serie.periodes.slice();
 const observees = serie.valeurs.slice();
 const projetees = new Array(observees.length - 1).fill(null);
 const bornesBasses = new Array(observees.length - 1).fill(null);
 const bornesHautes = new Array(observees.length - 1).fill(null);

 // On rattache la projection au dernier point observé, pour que la courbe
 // ne présente pas de rupture visuelle.
 projetees.push(observees[observees.length - 1]);
 bornesBasses.push(null);
 bornesHautes.push(null);

 if (Array.isArray(projection) && projection.length) {
  projection.forEach((p) => {
   etiquettes.push(p.periode);
   observees.push(null);
   projetees.push(p.valeur);
   bornesBasses.push(p.bas !== undefined ? p.bas : null);
   bornesHautes.push(p.haut !== undefined ? p.haut : null);
  });
 }

 const jeux = [
  {
   label: "Observé",
   data: observees,
   borderColor: "#14527a",
   backgroundColor: "rgba(20, 82, 122, .08)",
   borderWidth: 2.4,
   pointRadius: 2.6,
   pointBackgroundColor: "#14527a",
   tension: 0.25,
   fill: false,
   spanGaps: false,
  },
 ];

 if (Array.isArray(projection) && projection.length) {
  jeux.push({
   label: "Projeté",
   data: projetees,
   borderColor: "#c9a227",
   borderWidth: 2.6,
   borderDash: [7, 4],
   pointRadius: 3,
   pointBackgroundColor: "#c9a227",
   tension: 0.25,
   fill: false,
   spanGaps: true,
  });
  jeux.push({
   label: "Borne haute (80 %)",
   data: bornesHautes,
   borderColor: "rgba(201, 162, 39, .38)",
   borderWidth: 1,
   pointRadius: 0,
   fill: false,
   spanGaps: true,
  });
  jeux.push({
   label: "Borne basse (80 %)",
   data: bornesBasses,
   borderColor: "rgba(201, 162, 39, .38)",
   borderWidth: 1,
   pointRadius: 0,
   fill: "-1",
   backgroundColor: "rgba(201, 162, 39, .12)",
   spanGaps: true,
  });
 }

 new Chart(cible, {
  type: "line",
  data: { labels: etiquettes, datasets: jeux },
  options: {
   responsive: true,
   maintainAspectRatio: false,
   interaction: { mode: "index", intersect: false },
   plugins: {
    legend: {
     position: "bottom",
     labels: { boxWidth: 14, boxHeight: 2, font: { size: 11 } },
    },
    tooltip: {
     callbacks: {
      label: (ctx) =>
       ctx.dataset.label + " : " +
       (ctx.parsed.y === null ? "n.d." : ctx.parsed.y),
     },
    },
   },
   scales: {
    x: {
     grid: { display: false },
     ticks: { maxRotation: 60, minRotation: 0, font: { size: 10 } },
    },
    y: {
     grid: { color: "rgba(85, 96, 107, .12)" },
     ticks: { font: { size: 10 } },
    },
   },
  },
 });
})();
