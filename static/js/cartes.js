/* Cartes interactives, Leaflet + contours GeoJSON servis par la plateforme. */

const COULEURS_CARTE = ["#e8f1f7", "#a8cde5", "#5fa3cd", "#1d6fa5", "#1d7ae0"];

const PALETTE_CARTE = {
 bleu: "#1d6fa5",
 or: "#c9a227",
 vert: "#2f7d54",
 rouge: "#b23a48",
 gris: "#8a949e",
};

let carte, coucheCourante, donneesRegions = [], donneesPays = [];
let territoire = "regions", indicateur = "pauvrete";

function classe(valeur, seuils, couleurs) {
 for (let i = seuils.length - 1; i >= 0; i--) {
  if (valeur >= seuils[i]) return couleurs[i + 1] || couleurs[couleurs.length - 1];
 }
 return couleurs[0];
}

const CONFIG = {
 pauvrete: { libelle: "Taux de pauvreté", unite: " %", seuils: [10, 20, 40, 60], couleurs: COULEURS_CARTE, champ: "pauvrete", couleurGraph: PALETTE_CARTE.or },
 population: { libelle: "Population", unite: " hab.", seuils: [700000, 1000000, 1500000, 2500000], couleurs: COULEURS_CARTE, champ: "population", couleurGraph: PALETTE_CARTE.bleu },
 densite: { libelle: "Densité", unite: " hab/km²", seuils: [10, 25, 50, 100], couleurs: COULEURS_CARTE, champ: "densite", couleurGraph: PALETTE_CARTE.bleu },
 croissance: { libelle: "Croissance du PIB", unite: " %", seuils: [0, 2, 4, 6], couleurs: ["#f3d9dc", "#e0a9b0", "#c98c96", "#6b7f95", "#1d6fa5"], champ: "croissance", couleurGraph: PALETTE_CARTE.bleu },
 inflation: { libelle: "Inflation", unite: " %", seuils: [1, 3, 5, 8], couleurs: ["#e8f1f7", "#a8cde5", "#f0d98a", "#d9a83a", "#b23a48"], champ: "inflation", couleurGraph: PALETTE_CARTE.rouge },
};

function formaterNombre(v, unite) {
 if (v === null || v === undefined) return "non disponible";
 let texte = Math.abs(v) >= 10000
  ? v.toLocaleString("fr-FR", { maximumFractionDigits: 0 })
  : v.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
 return texte + (unite || "");
}

function construireLegende(cfg) {
 const zone = document.getElementById("legende");
 if (!zone) return;
 const bornes = [0, ...cfg.seuils];
 let html = "";
 for (let i = 0; i < bornes.length; i++) {
  const bas = i === 0 ? "moins de " + formaterNombre(cfg.seuils[0], cfg.unite)
            : "plus de " + formaterNombre(cfg.seuils[i - 1], cfg.unite);
  html += `<span class="entree">
   <span class="pastille-couleur" style="background:${cfg.couleurs[i]}"></span>${bas}
  </span>`;
 }
 zone.innerHTML = html;
}

function surbrillance(couche, actif) {
 couche.setStyle({
  weight: actif ? 2.6 : 1,
  color: actif ? PALETTE_CARTE.or : "#ffffff",
  fillOpacity: actif ? 0.92 : 0.78,
 });
 if (actif) couche.bringToFront();
}

async function dessinerRegions() {
 const cfg = CONFIG[indicateur] || CONFIG.pauvrete;
 const geo = await appelJson("/api/carte/regions/");

 if (coucheCourante) carte.removeLayer(coucheCourante);
 coucheCourante = L.geoJSON(geo, {
  style: (f) => {
   const v = f.properties[cfg.champ];
   return {
    fillColor: classe(v, cfg.seuils, cfg.couleurs),
    weight: 1, color: "#ffffff", fillOpacity: 0.78,
   };
  },
  onEachFeature: (f, couche) => {
   const p = f.properties;
   couche.bindTooltip(
    `<b>${p.nom_fr || p.shapeName}</b><br>` +
    `Chef-lieu : ${p.chef_lieu || "n.d."}<br>` +
    `Population : ${formaterNombre(p.population, " hab.")}<br>` +
    `Densité : ${formaterNombre(p.densite, " hab/km²")}<br>` +
    `Pauvreté (2022) : ${formaterNombre(p.pauvrete, " %")}`,
    { sticky: true, className: "infobulle-carte" }
   );
   couche.on({
    mouseover: (e) => surbrillance(e.target, true),
    mouseout: (e) => surbrillance(e.target, false),
   });
  },
 }).addTo(carte);

 const infos = donneesRegions.map((r) => ({ nom: r.nom, valeur: r[cfg.champ] }));
 const zone = document.getElementById("legende");
 if (zone) {
  const moy = infos.reduce((s, d) => s + (d.valeur || 0), 0) / (infos.length || 1);
  const max = infos.reduce((a, b) => ((a.valeur || 0) > (b.valeur || 0) ? a : b), infos[0]);
  const min = infos.reduce((a, b) => ((a.valeur || 0) < (b.valeur || 0) ? a : b), infos[0]);
  construireLegende(cfg);
  zone.insertAdjacentHTML("beforeend",
   `<span class="entree" style="margin-left:auto">
    <span class="badge-source">moyenne ${formaterNombre(moy, cfg.unite)} ·
    de ${min.nom} à ${max.nom}</span></span>`);
 }
 return infos;
}

async function dessinerPays() {
 const cfg = CONFIG[indicateur] && ["croissance", "inflation"].includes(indicateur)
  ? CONFIG[indicateur] : CONFIG.croissance;
 const geo = await appelJson("/api/carte/pays/");

 if (coucheCourante) carte.removeLayer(coucheCourante);
 coucheCourante = L.geoJSON(geo, {
  style: (f) => {
   const v = f.properties[cfg.champ];
   return {
    fillColor: classe(v, cfg.seuils, cfg.couleurs),
    weight: 1, color: "#ffffff", fillOpacity: 0.8,
   };
  },
  onEachFeature: (f, couche) => {
   const p = f.properties;
   couche.bindTooltip(
    `<b>${p.nom_fr || p.name}</b><br>` +
    `Croissance : ${formaterNombre(p.croissance, " %")}<br>` +
    `Inflation : ${formaterNombre(p.inflation, " %")}<br>` +
    `PIB (2025) : ${formaterNombre(p.pib_mds, " Mds USD")}<br>` +
    `Population : ${formaterNombre(p.population, " M hab.")}`,
    { sticky: true }
   );
   couche.on({
    mouseover: (e) => surbrillance(e.target, true),
    mouseout: (e) => surbrillance(e.target, false),
   });
  },
 }).addTo(carte);
 construireLegende(cfg);
}

async function rafraichir() {
 const titre = document.getElementById("titre-carte");
 if (territoire === "regions") {
  if (titre) titre.textContent = "Cameroun : régions";
  await dessinerRegions();
 } else {
  if (titre) titre.textContent = "Zone CEMAC : pays";
  await dessinerPays();
 }
}

document.addEventListener("DOMContentLoaded", () => {
 const cible = document.getElementById("carte");
 if (!cible || typeof L === "undefined") return;

 carte = L.map("carte", { attributionControl: false, zoomControl: true });
 L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
  maxZoom: 12,
  subdomains: "abcd",
 }).addTo(carte);

 const blocR = document.getElementById("donnees-regions");
 const blocP = document.getElementById("donnees-pays");
 try { donneesRegions = JSON.parse(blocR.textContent); } catch (e) { donneesRegions = []; }
 try { donneesPays = JSON.parse(blocP.textContent); } catch (e) { donneesPays = []; }

 carte.setView([5.6, 12.4], 5);
 rafraichir().catch(() => {
  carte.setView([3.9, 13.5], 5);
 });

 document.querySelectorAll("#bascule-territoire button").forEach((b) => {
  b.addEventListener("click", () => {
   document.querySelectorAll("#bascule-territoire button").forEach((x) => x.classList.remove("actif"));
   b.classList.add("actif");
   territoire = b.dataset.territoire;
   carte.setView(territoire === "regions" ? [5.6, 12.4] : [3.4, 16.0],
          territoire === "regions" ? 6 : 4);
   const select = document.getElementById("select-indicateur");
   if (select) {
    select.innerHTML = territoire === "regions"
     ? `<option value="pauvrete">Taux de pauvreté (2022)</option>
       <option value="population">Population</option>
       <option value="densite">Densité (hab/km²)</option>`
     : `<option value="croissance">Croissance du PIB (2025)</option>
       <option value="inflation">Inflation (2025)</option>`;
    indicateur = select.value;
   }
   rafraichir();
  });
 });

 const select = document.getElementById("select-indicateur");
 if (select) select.addEventListener("change", () => {
  indicateur = select.value;
  rafraichir();
 });

 /* Graphiques annexes de la page cartes. */
 const dz = document.getElementById("graph-densite");
 if (dz) traceBarres(dz, donneesRegions.map((r) => ({ nom: r.nom, valeur: r.densite })),
           PALETTE_CARTE.bleu, " hab/km²");
 const pz = document.getElementById("graph-pib-pays");
 if (pz) traceBarres(pz, donneesPays.map((p) => ({ nom: p.nom, valeur: p.pib })),
           PALETTE_CARTE.or, " Mds USD");
});
