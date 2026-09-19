/* Graphique de projection multivariée : historique puis valeurs projetées. */
(function () {
  const sourceHist = document.getElementById("historique-multivarie");
  const sourceProj = document.getElementById("projection-multivarie");
  const cible = document.getElementById("graphique-multivarie");
  if (!sourceHist || !cible || typeof Chart === "undefined") return;

  let historique, projection;
  try {
    historique = JSON.parse(sourceHist.textContent);
  } catch (e) {
    return;
  }
  try {
    projection = sourceProj ? JSON.parse(sourceProj.textContent) : [];
  } catch (e) {
    projection = [];
  }
  if (!historique.periodes || !historique.periodes.length) return;

  // Le graphique juxtapose deux séries de longueurs différentes : on construit
  // un axe de libellés commun, et chaque série porte la valeur null là où elle
  // n'existe pas. Sans cela, la projection viendrait s'afficher au début du
  // graphique au lieu de prolonger l'historique.
  const labels = historique.periodes.concat(projection.map((p) => p.periode));
  const valeursHist = historique.valeurs.concat(
    projection.map(() => null)
  );
  const valeursProj = historique.periodes
    .map(() => null)
    .concat(projection.map((p) => p.valeur));
  const borneBasse = historique.periodes
    .map(() => null)
    .concat(projection.map((p) => p.bas));
  const borneHaute = historique.periodes
    .map(() => null)
    .concat(projection.map((p) => p.haut));

  new Chart(cible, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Historique",
          data: valeursHist,
          borderColor: "#1560c8",
          backgroundColor: "rgba(10, 36, 56, 0.08)",
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.2,
        },
        {
          label: "Projection",
          data: valeursProj,
          borderColor: "#c9a227",
          borderDash: [6, 4],
          borderWidth: 2.2,
          pointRadius: 0,
          tension: 0.2,
          spanGaps: true,
        },
        {
          label: "Borne haute (80 %)",
          data: borneHaute,
          borderColor: "rgba(201, 162, 39, 0.35)",
          borderWidth: 1,
          pointRadius: 0,
          fill: false,
          spanGaps: true,
        },
        {
          label: "Borne basse (80 %)",
          data: borneBasse,
          borderColor: "rgba(201, 162, 39, 0.35)",
          borderWidth: 1,
          pointRadius: 0,
          fill: false,
          spanGaps: true,
        },
      ],
    },
    options: {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "bottom", labels: { boxWidth: 12, padding: 14 } },
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 60 } },
        y: { grid: { color: "rgba(0,0,0,0.06)" } },
      },
    },
  });
})();
