/* Assistant « Le Perpétuel », dialogue en ligne / hors ligne. */

let config = { enLigne: false, conversation: null, urlMessage: "", urlNouvelle: "" };
let enCours = false;

function bulle(role, texte, mode, avertissement) {
 const fil = document.getElementById("fil");
 const vide = document.getElementById("accueil-vide");
 if (vide) vide.remove();

 const div = document.createElement("div");
 div.className = "bulle " + (role === "utilisateur" ? "utilisateur" : "assistant");
 if (role === "assistant" && mode) {
  const et = document.createElement("span");
  et.className = "etiquette-mode";
  et.textContent = mode === "en_ligne" ? "En ligne" : "Hors ligne";
  div.appendChild(et);
 }
 div.appendChild(document.createTextNode(texte));
 if (avertissement) {
  const av = document.createElement("span");
  av.className = "avertissement";
  av.textContent = avertissement;
  div.appendChild(av);
 }
 fil.appendChild(div);
 versLeBas(fil);
 return div;
}

function indicateurAttente() {
 const fil = document.getElementById("fil");
 const div = document.createElement("div");
 div.className = "bulle assistant";
 div.id = "attente";
 div.textContent = "…";
 fil.appendChild(div);
 versLeBas(fil);
}

function retirerAttente() {
 const a = document.getElementById("attente");
 if (a) a.remove();
}

function majEtat(enLigne, force) {
 const zone = document.getElementById("etat-assistant");
 const texte = document.getElementById("texte-etat");
 if (!zone || !texte) return;
 zone.classList.toggle("en-ligne", enLigne);
 zone.classList.toggle("hors-ligne", !enLigne);
 if (force) {
  texte.textContent = "hors ligne : base de connaissances locale";
 } else if (navigator.onLine && enLigne) {
  texte.textContent = "en ligne : modèle connecté";
 } else if (!navigator.onLine) {
  texte.textContent = "hors ligne : réseau indisponible";
 } else {
  texte.textContent = "hors ligne : base de connaissances locale";
 }
}

async function envoyer(question) {
 if (enCours || !question.trim()) return;
 enCours = true;

 bulle("utilisateur", question);
 const saisie = document.getElementById("saisie");
 saisie.value = "";
 autoHauteur(saisie);
 indicateurAttente();

 const forcer = document.getElementById("forcer-hors-ligne");
 const mode = forcer && forcer.checked ? "hors_ligne" : "en_ligne";

 try {
  const r = await appelJson(config.urlMessage, {
   method: "POST",
   body: {
    message: question,
    conversation: config.conversation,
    mode: mode,
   },
  });
  retirerAttente();
  config.conversation = r.conversation;
  bulle("assistant", r.reponse, r.mode, r.avertissement);
  if (r.mode === "hors_ligne") majEtat(false, mode === "hors_ligne");
 } catch (e) {
  retirerAttente();
  bulle("assistant",
   "Je n'ai pas pu joindre le service : " + e.message +
   ". Vérifiez votre connexion, ou cochez « Forcer le mode hors ligne » " +
   "pour interroger la base de connaissances locale.",
   "hors_ligne", null);
 } finally {
  enCours = false;
 }
}

document.addEventListener("DOMContentLoaded", () => {
 const bloc = document.getElementById("etat-config");
 if (bloc) {
  try { config = { ...config, ...JSON.parse(bloc.textContent) }; } catch (e) {}
 }
 majEtat(config.enLigne, false);
 window.addEventListener("online", () => majEtat(config.enLigne, false));
 window.addEventListener("offline", () => majEtat(config.enLigne, false));

 const saisie = document.getElementById("saisie");
 const fil = document.getElementById("fil");
 versLeBas(fil);

 if (saisie) {
  autoHauteur(saisie);
  saisie.addEventListener("input", () => autoHauteur(saisie));
  saisie.addEventListener("keydown", (e) => {
   if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    envoyer(saisie.value);
   }
  });
 }

 const bouton = document.getElementById("envoyer");
 if (bouton) bouton.addEventListener("click", () => envoyer(saisie.value));

 document.querySelectorAll(".suggestions button").forEach((b) => {
  b.addEventListener("click", () => envoyer(b.dataset.question));
 });

 const nouvelle = document.getElementById("nouvelle-conversation");
 if (nouvelle) {
  nouvelle.addEventListener("click", async () => {
   try {
    const r = await appelJson(config.urlNouvelle, { method: "POST", body: {} });
    config.conversation = r.conversation;
    const zoneFil = document.getElementById("fil");
    zoneFil.innerHTML = "";
    const vide = document.createElement("div");
    vide.className = "accueil-vide";
    vide.innerHTML = "<h3>Nouvelle conversation</h3><p class='petit'>Posez votre question.</p>";
    zoneFil.appendChild(vide);
   } catch (e) { /* silencieux */ }
  });
 }
});
