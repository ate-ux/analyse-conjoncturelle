/* Analyse conjoncturelle, scripts généraux */

/* Jeton CSRF extrait du cookie, pour les appels JSON. */
function jetonCsrf() {
 const nom = "csrftoken";
 const cookies = document.cookie ? document.cookie.split(";") : [];
 for (let c of cookies) {
  c = c.trim();
  if (c.startsWith(nom + "=")) return decodeURIComponent(c.slice(nom.length + 1));
 }
 const champ = document.querySelector("[name=csrfmiddlewaretoken]");
 return champ ? champ.value : "";
}

/* Appel JSON générique. */
async function appelJson(url, options = {}) {
 const rep = await fetch(url, {
  method: options.method || "GET",
  headers: {
   "Content-Type": "application/json",
   "X-CSRFToken": jetonCsrf(),
   ...(options.headers || {}),
  },
  body: options.body ? JSON.stringify(options.body) : undefined,
 });
 if (!rep.ok) {
  let detail = "Erreur " + rep.status;
  try { const j = await rep.json(); detail = j.erreur || j.detail || detail; } catch (e) {}
  throw new Error(detail);
 }
 return rep.json();
}

/* Défilement des zones de discussion. */
function versLeBas(element) {
 if (element) element.scrollTop = element.scrollHeight;
}

/* Ajustement automatique de la hauteur d'une zone de saisie. */
function autoHauteur(textarea) {
 if (!textarea) return;
 textarea.style.height = "auto";
 textarea.style.height = Math.min(textarea.scrollHeight, 130) + "px";
}

/* Onglets génériques : [data-onglet] + [data-panneau]. */
document.addEventListener("click", (e) => {
 const bouton = e.target.closest("[data-onglet]");
 if (!bouton) return;
 const groupe = bouton.closest("[data-onglets]") || document;
 const cible = bouton.dataset.onglet;
 groupe.querySelectorAll("[data-onglet]").forEach((b) => {
  b.classList.toggle("actif", b === bouton);
 });
 groupe.querySelectorAll("[data-panneau]").forEach((p) => {
  p.style.display = p.dataset.panneau === cible ? "" : "none";
 });
});

/* Presse-papiers discret sur les blocs de code. */
document.addEventListener("click", async (e) => {
 const bouton = e.target.closest("[data-copier]");
 if (!bouton) return;
 try {
  await navigator.clipboard.writeText(bouton.dataset.copier);
  const ancien = bouton.textContent;
  bouton.textContent = "Copié";
  setTimeout(() => { bouton.textContent = ancien; }, 1400);
 } catch (err) { /* navigation privée : on ignore */ }
});

/* État de connexion réseau, affiché dans les pieds de page. */
function majEtatReseau() {
 const enLigne = navigator.onLine;
 document.querySelectorAll("[data-etat-reseau]").forEach((el) => {
  el.textContent = enLigne ? "connexion active" : "hors ligne";
  el.classList.toggle("en-ligne", enLigne);
  el.classList.toggle("hors-ligne", !enLigne);
 });
}
window.addEventListener("online", majEtatReseau);
window.addEventListener("offline", majEtatReseau);
document.addEventListener("DOMContentLoaded", majEtatReseau);
