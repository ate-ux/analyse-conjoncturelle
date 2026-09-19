# Analyse conjoncturelle, Cameroun & zone CEMAC

Plateforme web Django d'analyse conjoncturelle, réalisée comme projet académique
(ISSEA, option Data Science). Elle réunit un tableau de bord, des cartes
interactives, un module statistique, un assistant conversationnel et un
générateur automatique de rapports PDF.

## Fonctionnalités

- **Tableau de bord**, indicateurs clés du Cameroun, séries longues, lecture
  commentée, comparaison des six pays de la CEMAC.
- **Cartes interactives**, dix régions du Cameroun et six pays de la CEMAC,
  choroplèthes selon trois ou deux indicateurs, avec infobulles et légende.
- **Module statistique**, statistiques descriptives, régression linéaire (MCO)
  avec pente, R² et p-value, prévision à trois ans avec intervalle à 80 %,
  corrélations de Pearson, indice de concentration (HHI).
- **Le Perpétuel**, assistant conversationnel. En ligne, il interroge un LLM
  (fournisseur compatible OpenAI, Groq par défaut) avec le contexte factuel de
  la plateforme. Hors ligne, il bascule automatiquement sur un moteur de règles
  adossé à une base de connaissances embarquée. Le cloisonnement public /
  confidentiel est appliqué avant l'envoi au modèle.
- **Prédictions comparées**, quatre modèles ajustés sur la même série puis
  évalués hors échantillon : tendance linéaire (MCO), lissage exponentiel de
  Holt, Holt-Winters (tendance + saisonnalité) et ARIMA (ordre choisi par AIC).
  Le meilleur est retenu sur le RMSE de test, puis réajusté sur la série
  complète pour projeter l'horizon, avec intervalle à 80 %. La MAPE est fournie
  quand elle a un sens, omise sinon.
- **Import de données**, dépôt d'un fichier CSV, TSV ou Excel par les
  administrateurs. Détection automatique du format (long ou large), des
  colonnes de période, d'entité et de valeur ; aperçu avant toute écriture ;
  rapport d'erreurs ligne par ligne ; import partiel accepté. Export CSV de tout
  le catalogue et modèle de fichier téléchargeable.
- **Séries infra-annuelles**, périodicités annuelle, semestrielle,
  trimestrielle et mensuelle, de bout en bout : import, stockage, graphiques,
  analyse statistique, prédictions et rapports.
- **Désaisonnalisation**, sur une série infra-annuelle, sépare la tendance de
  fond, la saisonnalité et le résidu irrégulier. Moyenne mobile centrée,
  coefficients saisonniers additifs ou multiplicatifs, série corrigée des
  variations saisonnières (CVS), choix automatique du modèle. Une embellie
  saisonnière n'est pas une reprise : cette page le montre.
- **Prévision multivariée**, régression multiple par moindres carrés. Relie une
  variable à ses déterminants (de quoi l'inflation dépend-elle, et non seulement
  comment elle a évolué). Coefficients en unités d'origine avec écarts-types,
  t, p, VIF et Durbin-Watson, test de Fisher, projection avec intervalle.
- **Rapports PDF**, quatre formats générés automatiquement : synthèse
  conjoncturelle, profil régional, profil pays, note statistique.
- **Deux niveaux d'accès**, deux administrateurs au maximum (données
  confidentielles), nombre d'utilisateurs illimité. Les séries marquées
  confidentielles sont exclues du catalogue, de l'export et des prédictions pour
  les simples utilisateurs.

## Identité visuelle

Palette vive : bleu franc (#1560c8), bleu clair (#2c8ef0), ambre chaud (#f5a623)
et turquoise (#00b3a4) en accent. Aucun fond sombre : les dégradés de la page de
connexion vont du bleu au turquoise.

Le logo de l'ISSEA est détouré (fond noir retiré) et posé directement sur le
dégradé, dans l'en-tête et sur les pages publiques. La carte de marque DEUS Stat
est présentée sur une plaque claire.

Signature présente sur toutes les pages : Joseph ATEBA, Data Scientist,
atebajoseph047@gmail.com, +237 670 211 522.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # puis renseignez la clé du LLM (facultatif)
python manage.py migrate
python manage.py initialiser --demo
python manage.py runserver
```

L'application écoute sur <http://127.0.0.1:8000/>.

### Comptes de démonstration

| Rôle | Identifiant | Mot de passe |
|---|---|---|
| Administrateur | `perpetuel` | `Conjoncture2026!` |
| Administrateur | `deus` | `DeusStat2026!` |
| Utilisateur | `analyste` | `Demo2026!` |
| Utilisateur | `etudiant` | `Demo2026!` |
| Utilisateur | `invite` | `Demo2026!` |

À changer avant tout usage réel.

## Assistant : mode en ligne et mode hors ligne

Renseignez la clé dans `.env` :

```
GROQ_API_KEY=votre_cle
```

Clé gratuite sur <https://console.groq.com/keys>. Sans clé, ou lorsque le
réseau est indisponible, l'assistant répond depuis la base de connaissances
locale et le signale dans la réponse. Aucune page ne devient inaccessible :
le repli est automatique.

## Sources des données

- **Banque mondiale**, World Development Indicators (séries longues).
- **INS Cameroun**, ECAM 5 (2022) pour la pauvreté, RGPH pour la démographie.
- **BEAC / CEMAC**, cadre communautaire et critères de convergence.
- **Direction générale du Trésor** (France), conjoncture et finances publiques.

Contours géographiques : geoBoundaries (régions du Cameroun, ADM1) et Natural
Earth (pays). Fond de carte : CARTO.

## Structure du projet

```
conjoncture_project/    configuration Django
conjoncture/
  data/economie.py      base de données sourcée et base de connaissances
  stats.py              module statistique (descriptif, MCO, prévision, corrélation)
  previsions.py         quatre modèles comparés, évaluation hors échantillon
  periodes.py           périodicités annuelle et infra-annuelles
  saisonnalite.py       décomposition : tendance, saisonnalité, résidu
  multivarie.py         régression multiple et projection multivariée
  vues_analyses.py      vues des pages Saisonnalité et Multivarié
  tests/                110 tests (périodes, saisonnalité, régression, import, app)
  imports.py            lecture et analyse des fichiers CSV / Excel
  service_import.py     écriture des imports, export du catalogue
  assistant.py          Le Perpétuel : appel LLM et repli hors ligne
  rapports.py           génération PDF (ReportLab)
  models.py             utilisateur à rôle, séries, points, imports, journal
  views.py, urls.py, forms.py, forms_import.py, admin.py
templates/              gabarits (connexion, accueil, tableau de bord, cartes…)
static/                 styles, scripts, contours géographiques, bibliothèques
```

## Formats d'import acceptés

**Format long** (recommandé), une ligne par observation :

```
periode;entite;valeur
2023;Extrême-Nord;4,5
2024-T1;Cameroun;0,9
2024-01;Cameroun;1,6
```

**Format large**, une ligne par entité, une colonne par période :

```
region;2019;2020;2021;2022
Extrême-Nord;4.2;4.3;4.4;4.5
Littoral;1.1;1.2;1.3;1.4
```

Périodes reconnues : `2024` (annuel), `2024-S1` (semestriel), `2024-T1` ou
`2024Q1` (trimestriel), `2024-03` (mensuel). Séparateur au choix (point-virgule,
virgule, tabulation, barre verticale) ; décimale au point ou à la virgule.

## Tests

```bash
python manage.py test conjoncture
```

110 tests couvrent cinq zones : les périodicités (analyse et tri des périodes),
la désaisonnalisation (coefficients retrouvés sur des séries construites), la
régression multivariée (coefficients exacts, colinéarité, autocorrélation),
la lecture des fichiers d'import (formats long et large, périodes
infra-annuelles, lignes rejetées) et l'application elle-même (cloisonnement des
rôles, génération des rapports).

Les tests de pages déclarent un stockage de fichiers statiques sans manifeste :
sans quoi ils dépendraient d'un `collectstatic` préalable, ce qui n'a pas de sens
pour des tests unitaires.

## Notes

Les coefficients saisonniers et les coefficients de régression sont estimés sur
les données disponibles ; ils ne valent pas au-delà de la période observée.
L'extrapolation des variables explicatives dans la projection multivariée est
signalée dans la page : elle suppose que les déterminants suivent leur tendance
passée, ce qui n'est pas garanti.

Les valeurs 2025-2026 sont des estimations. Les prévisions du module statistique
sont des extrapolations, non des prévisions officielles. La série de pauvreté
ECAM 5 n'est pas comparable aux éditions antérieures : la rupture est signalée
dans les commentaires et la note méthodologique.
