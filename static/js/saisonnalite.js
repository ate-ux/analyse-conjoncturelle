/* Graphique de décomposition saisonnière : observée, CVS, tendance. */
(function () {
  const source = document.getElementById("donnees-saisonnalite");
  const cible = document.getElementById("graphique-saisonnalite");
  if (!source || !cible || typeof Chart === "undefined") return;

  let donnees;
  try {
    donnees = JSON.parse(source.textContent);
  } catch (e) {
    return;
  }
  if (!donnees.periode || !donnees.periode.length) return;

  new Chart(cible, {
    type: "line",
    data: {
      labels: donnees.periode,
      datasets: [
        {
          label: "Série observée",
          data: donnees.observee,
          borderColor: "#1560c8",
          backgroundColor: "rgba(10, 36, 56, 0.08)",
          borderWidth: 1.6,
          pointRadius: 0,
          tension: 0.2,
        },
        {
          label: "Série corrigée (CVS)",
          data: donnees.cvs,
          borderColor: "#c9a227",
          backgroundColor: "rgba(201, 162, 39, 0.10)",
          borderWidth: 2.2,
          pointRadius: 0,
          tension: 0.2,
        },
        {
          label: "Tendance",
          data: donnees.tendance,
          borderColor: "#8c2f39",
          borderDash: [6, 4],
          borderWidth: 1.8,
          pointRadius: 0,
          tension: 0.2,
          spanGaps: true,
        },
      ],
    },
    options: {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "bottom", labels: { boxWidth: 12, padding: 14 } },
        tooltip: { callbacks: {} },
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 60, minRotation: 0 } },
        y: { grid: { color: "rgba(0,0,0,0.06)" } },
      },
    },
  });
})();
