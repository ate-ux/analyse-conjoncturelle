/* Graphiques du tableau de bord et du module statistique (Chart.js) */

const PALETTE = {
  bleu: "#1d6fa5",
  bleuFonce: "#1d7ae0",
  or: "#c9a227",
  vert: "#2f7d54",
  rouge: "#b23a48",
  gris: "#8a949e",
  grille: "#e6ebef",
};
const SERIES_COULEURS = ["#1d6fa5", "#c9a227", "#2f7d54", "#b23a48", "#14527a", "#8a949e"];

const OPTIONS_BASE = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: "#1560c8",
      padding: 10,
      titleFont: { size: 12, weight: "600" },
      bodyFont: { size: 12 },
      displayColors: false,
    },
  },
  scales: {
    x: { grid: { display: false }, ticks: { color: PALETTE.gris, font: { size: 11 } } },
    y: {
      grid: { color: PALETTE.grille, drawBorder: false },
      ticks: { color: PALETTE.gris, font: { size: 11 } },
    },
  },
};

function optionsAvecUnite(unite, seuil) {
  const o = JSON.parse(JSON.stringify(OPTIONS_BASE));
  if (unite) {
    o.scales.y.ticks.callback = (v) => v + " " + unite;
  }
  if (seuil !== undefined && seuil !== null && seuil !== "") {
    o.scales.y.suggestedMin = undefined;
  }
  return o;
}

/* Courbe d'évolution d'une série {année: valeur}. */
function traceSerie(canvas) {
  let serie;
  try { serie = JSON.parse(canvas.dataset.serie); } catch (e) { return; }
  const annees = Object.keys(serie).sort();
  const valeurs = annees.map((a) => serie[a]);
  const unite = canvas.dataset.unite || "";
  const seuil = canvas.dataset.seuil;

  const jeux = [{
    label: canvas.dataset.libelle,
    data: valeurs,
    borderColor: PALETTE.bleu,
    backgroundColor: "rgba(29, 111, 165, .10)",
    borderWidth: 2,
    pointRadius: 3,
    pointBackgroundColor: PALETTE.bleu,
    fill: true,
    tension: 0.28,
  }];

  if (seuil !== undefined && seuil !== "" && seuil !== null) {
    jeux.push({
      label: "Repère",
      data: annees.map(() => parseFloat(seuil)),
      borderColor: PALETTE.or,
      borderWidth: 1.4,
      borderDash: [5, 4],
      pointRadius: 0,
      fill: false,
    });
  }

  new Chart(canvas, {
    type: "line",
    data: { labels: annees, datasets: jeux },
    options: optionsAvecUnite(unite),
  });
}

/* Barres horizontales : [{nom, valeur}]. */
function traceBarres(canvas, donnees, couleur, unite) {
  const tri = [...donnees].sort((a, b) => (b.valeur || 0) - (a.valeur || 0));
  new Chart(canvas, {
    type: "bar",
    data: {
      labels: tri.map((d) => d.nom),
      datasets: [{
        data: tri.map((d) => d.valeur),
        backgroundColor: couleur || PALETTE.bleu,
        borderRadius: 5,
        barThickness: 16,
      }],
    },
    options: {
      ...optionsAvecUnite(unite || ""),
      indexAxis: "y",
      scales: {
        x: { grid: { color: PALETTE.grille }, ticks: { color: PALETTE.gris, font: { size: 11 } } },
        y: { grid: { display: false }, ticks: { color: "#24292f", font: { size: 11 } } },
      },
    },
  });
}

/* Barres groupées : catégories + plusieurs séries. */
function traceBarresGroupees(canvas, categories, series) {
  new Chart(canvas, {
    type: "bar",
    data: {
      labels: categories,
      datasets: series.map((s, i) => ({
        label: s.nom,
        data: s.donnees,
        backgroundColor: SERIES_COULEURS[i % SERIES_COULEURS.length],
        borderRadius: 4,
      })),
    },
    options: {
      ...JSON.parse(JSON.stringify(OPTIONS_BASE)),
      plugins: {
        ...OPTIONS_BASE.plugins,
        legend: { display: true, position: "bottom", labels: { boxWidth: 10, font: { size: 11 } } },
      },
    },
  });
}

/* Nuage de points avec droite de tendance (module statistique). */
function traceCorrelation(canvas, points, droite) {
  const jeux = [{
    label: "Observations",
    data: points,
    backgroundColor: PALETTE.bleu,
    pointRadius: 4,
    type: "scatter",
  }];
  if (droite) {
    jeux.push({
      label: "Ajustement",
      data: droite,
      borderColor: PALETTE.or,
      borderWidth: 2,
      pointRadius: 0,
      showLine: true,
      fill: false,
      type: "line",
    });
  }
  new Chart(canvas, {
    type: "scatter",
    data: { datasets: jeux },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true, position: "bottom", labels: { boxWidth: 10, font: { size: 11 } } },
        tooltip: { backgroundColor: "#1560c8", displayColors: false },
      },
      scales: {
        x: { grid: { color: PALETTE.grille }, ticks: { color: PALETTE.gris, font: { size: 11 } } },
        y: { grid: { color: PALETTE.grille }, ticks: { color: PALETTE.gris, font: { size: 11 } } },
      },
    },
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("canvas[data-serie]").forEach(traceSerie);

  const pauvrete = document.getElementById("graph-pauvrete");
  const blocPauvrete = document.getElementById("donnees-pauvrete");
  if (pauvrete && blocPauvrete) {
    try {
      traceBarres(pauvrete, JSON.parse(blocPauvrete.textContent), PALETTE.or, " %");
    } catch (e) { /* données absentes : on n'affiche rien */ }
  }

  const cemac = document.getElementById("graph-cemac");
  const blocCemac = document.getElementById("donnees-cemac");
  if (cemac && blocCemac) {
    try {
      traceBarres(cemac, JSON.parse(blocCemac.textContent), PALETTE.bleu, " %");
    } catch (e) { /* idem */ }
  }

  const prevision = document.getElementById("graph-prevision");
  const blocPrevision = document.getElementById("donnees-prevision");
  if (prevision && blocPrevision) {
    try {
      const d = JSON.parse(blocPrevision.textContent);
      new Chart(prevision, {
        type: "line",
        data: {
          labels: d.labels,
          datasets: [
            {
              label: "Prévision",
              data: d.valeurs,
              borderColor: PALETTE.or,
              backgroundColor: "rgba(201,162,39,.12)",
              borderWidth: 2,
              borderDash: [6, 4],
              pointRadius: 3,
              tension: 0.25,
              fill: false,
            },
            {
              label: "Borne haute (80 %)",
              data: d.haut,
              borderColor: "rgba(201,162,39,.45)",
              borderWidth: 1,
              pointRadius: 0,
              fill: "+1",
              backgroundColor: "rgba(201,162,39,.08)",
            },
            {
              label: "Borne basse (80 %)",
              data: d.bas,
              borderColor: "rgba(201,162,39,.45)",
              borderWidth: 1,
              pointRadius: 0,
              fill: false,
            },
          ],
        },
        options: {
          ...JSON.parse(JSON.stringify(OPTIONS_BASE)),
          plugins: {
            ...OPTIONS_BASE.plugins,
            legend: { display: true, position: "bottom", labels: { boxWidth: 10, font: { size: 11 } } },
          },
        },
      });
    } catch (e) { /* idem */ }
  }

  const corr = document.getElementById("graph-correlation");
  const blocCorr = document.getElementById("donnees-correlation");
  if (corr && blocCorr) {
    try {
      const d = JSON.parse(blocCorr.textContent);
      traceCorrelation(corr, d.points, d.droite);
    } catch (e) { /* idem */ }
  }
});
