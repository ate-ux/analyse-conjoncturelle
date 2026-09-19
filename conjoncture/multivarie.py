"""
Prévision multivariée, régression multiple appliquée à la conjoncture.

Une prévision univariée n'exploite que le passé de la série elle-même. La
prévision multivariée relie la variable d'intérêt à des variables explicatives :
l'inflation aux prix alimentaires, à la masse monétaire et au taux de change par
exemple. Elle répond à une question que l'univarié ne sait pas poser : *par quoi*
la variable est-elle mouvée ?

Trois précautions gouvernent ce module, et chacune est calculée, pas supposée :

- **colinéarité**, deux régresseurs fortement corrélés rendent les coefficients
 instables : on calcule le facteur d'inflation de la variance (VIF) et on
 signale les variables fautives ;
- **autocorrélation des résidus**, des résidus qui se suivent gonflent la
 significativité : on calcule la statistique de Durbin-Watson ;
- **variables explicatives futures**, un modèle multivarié a besoin de la valeur
 future des régresseurs. Nous ne les connaissons pas : nous les extrapolons par
 leur propre tendance, et cette hypothèse est affichée, jamais dissimulée.

Tous les calculs sont faits avec numpy et scipy : aucune dépendance ajoutée.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import stats as scipy_stats

from . import periodes

# Seuil usuel au-delà duquel la colinéarité devient problématique.
SEUIL_VIF = 10.0
# Seuils de Durbin-Watson : hors de cette plage, les résidus sont suspectés
# d'autocorrélation (bornes usuelles pour un modèle sans retards).
DW_BAS, DW_HAUT = 1.5, 2.5


def periodes_communes(serie_cible, series_explicatives):
  """Nombre de périodes présentes à la fois dans la cible et dans toutes les
  variables explicatives.

  Sert à écarter d'emblée les combinaisons de séries qui ne se recouvrent pas
  assez : mieux vaut le dire avant d'ajuster que d'échouer après.
  """
  if not series_explicatives:
    return 0
  communes = None
  for _, s in series_explicatives:
    cles = {p for p, v in s.items() if v is not None}
    communes = cles if communes is None else (communes & cles)
  cles_cible = {p for p, v in serie_cible.items() if v is not None}
  return len((communes or set()) & cles_cible)


def _aligner(serie_cible, series_explicatives):
  """Aligne la cible et les régresseurs sur leurs périodes communes.

  Retourne ``(periodes_communes, y, X_brut, noms)`` ou ``None`` si la
  conjonction est trop pauvre pour ajuster quoi que ce soit.
  """
  noms = [nom for nom, _ in series_explicatives]
  communes = None
  for _, s in series_explicatives:
    cles = {p for p, v in s.items() if v is not None}
    communes = cles if communes is None else (communes & cles)
  cles_cible = {p for p, v in serie_cible.items() if v is not None}
  communes = (communes or set()) & cles_cible

  # L'ordre chronologique compte : la régression n'a de sens que sur une
  # séquence ordonnée, notamment pour tester l'autocorrélation des résidus.
  triees = sorted(communes, key=periodes.cle_tri)
  if len(triees) < 8:
    return None

  y = np.array([float(serie_cible[p]) for p in triees], dtype=float)
  colonnes = []
  for _, s in series_explicatives:
    colonnes.append(np.array([float(s[p]) for p in triees], dtype=float))
  X_brut = np.column_stack(colonnes) if colonnes else np.zeros((len(triees), 0))
  return triees, y, X_brut, noms


def _standardiser(X_brut):
  """Centre et réduit chaque régresseur.

  Sans cette étape, comparer l'effet d'un régresseur exprimé en milliards à
  celui d'un taux en pourcentage n'a aucun sens.
  """
  moyennes = X_brut.mean(axis=0)
  ecarts = X_brut.std(axis=0, ddof=1)
  ecarts[ecarts == 0] = 1.0    # colonne constante : on la neutralise
  return (X_brut - moyennes) / ecarts, moyennes, ecarts


def vif(X_standardise):
  """Facteur d'inflation de la variance, un par régresseur.

  Chaque régresseur est régressé sur tous les autres ; le VIF mesure à quel
  point il est redondant. Au-delà de 10, la colinéarité est jugée forte.
  """
  n, k = X_standardise.shape
  resultats = []
  for j in range(k):
    autres = np.delete(X_standardise, j, axis=1)
    if autres.shape[1] == 0:
      resultats.append(1.0)
      continue
    A = np.column_stack([np.ones(n), autres])
    cible = X_standardise[:, j]
    try:
      coefs, *_ = np.linalg.lstsq(A, cible, rcond=None)
      predits = A @ coefs
      ss_res = float(np.sum((cible - predits) ** 2))
      ss_tot = float(np.sum((cible - cible.mean()) ** 2))
      r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    except np.linalg.LinAlgError:
      r2 = 0.0
    r2 = min(max(r2, 0.0), 1.0 - 1e-12)
    resultats.append(1.0 / (1.0 - r2))
  return resultats


def durbin_watson(residus):
  """Statistique de Durbin-Watson. Proche de 2 : pas d'autocorrélation."""
  r = np.asarray(residus, dtype=float)
  if r.size < 2:
    return None
  denominateur = float(np.sum(r ** 2))
  if denominateur == 0:
    return None
  return float(np.sum(np.diff(r) ** 2) / denominateur)


def ajuster(serie_cible, series_explicatives):
  """Ajuste une régression multiple par les moindres carrés ordinaires.

  ``series_explicatives`` est une liste de couples ``(nom, {periode: valeur})``.
  Retourne un dictionnaire complet : coefficients, erreurs standard, tests de
  Student, qualité de l'ajustement et diagnostics.
  """
  aligne = _aligner(serie_cible, series_explicatives)
  if aligne is None:
    # Distinguer les deux causes : l'absence de régresseur n'a rien à voir
    # avec la longueur de l'échantillon, et l'utilisateur doit savoir
    # laquelle des deux le bloque.
    if not series_explicatives:
      return {"disponible": False,
          "raison": "aucune variable explicative fournie"}
    return {
      "disponible": False,
      "raison": ("moins de huit périodes communes aux variables : "
            "l'échantillon est trop court pour ajuster un modèle"),
    }
  cles, y, X_brut, noms = aligne
  n, k = X_brut.shape
  if k == 0:
    return {"disponible": False, "raison": "aucune variable explicative fournie"}
  if n <= k + 1:
    return {
      "disponible": False,
      "raison": (f"{n} observations pour {k} régresseurs : il faut "
            "davantage de points que de variables"),
    }

  X_std, moyennes, ecarts = _standardiser(X_brut)
  # Colonne de 1 pour l'ordonnée à l'origine
  A = np.column_stack([np.ones(n), X_std])

  try:
    coefs, *_ = np.linalg.lstsq(A, y, rcond=None)
  except np.linalg.LinAlgError:
    return {"disponible": False, "raison": "ajustement impossible (matrice singulière)"}

  predits = A @ coefs
  residus = y - predits

  # Qualité de l'ajustement
  ss_res = float(np.sum(residus ** 2))
  ss_tot = float(np.sum((y - y.mean()) ** 2))
  r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
  ddl = n - k - 1
  r2_ajuste = 1.0 - (1.0 - r2) * (n - 1) / ddl if ddl > 0 else None
  sigma2 = ss_res / ddl if ddl > 0 else None

  # Erreurs standard et tests de Student
  erreurs, t_stats, p_values = [], [], []
  if sigma2 and sigma2 > 0:
    try:
      cov = sigma2 * np.linalg.inv(A.T @ A)
      for j in range(A.shape[1]):
        se = math.sqrt(max(cov[j, j], 0.0))
        erreurs.append(se)
        if se > 0:
          t = coefs[j] / se
          t_stats.append(float(t))
          p_values.append(float(2 * (1 - scipy_stats.t.cdf(abs(t), ddl))))
        else:
          t_stats.append(None)
          p_values.append(None)
    except np.linalg.LinAlgError:
      erreurs = [None] * A.shape[1]
      t_stats = [None] * A.shape[1]
      p_values = [None] * A.shape[1]
  else:
    erreurs = [None] * A.shape[1]
    t_stats = [None] * A.shape[1]
    p_values = [None] * A.shape[1]

  # Test global de Fisher. Un ajustement parfait donne un R² de 1 et une
  # statistique infinie : calculer le rapport diviserait par zéro.
  f_stat = f_pvalue = None
  if k > 0 and ddl > 0:
    if (1.0 - r2) > 1e-12:
      f_stat = (r2 / k) / ((1 - r2) / ddl)
      try:
        f_pvalue = float(1 - scipy_stats.f.cdf(f_stat, k, ddl))
      except Exception:
        f_pvalue = None
    else:
      # Ajustement exact : Fisher est infini, la probabilité critique nulle.
      f_pvalue = 0.0

  # Diagnostics
  vifs = vif(X_std)
  dw = durbin_watson(residus)
  # Normalité des résidus (Jarque-Bera)
  jb = jb_p = None
  if residus.size >= 8 and ddl > 0:
    try:
      jb, jb_p = scipy_stats.jarque_bera(residus)
      jb, jb_p = float(jb), float(jb_p)
    except Exception:
      pass

  # Coefficients exprimés en unités d'origine : l'effet d'une hausse d'une
  # unité du régresseur (et non d'un écart-type), plus directement lisible.
  #
  # La régression a été ajustée sur des régresseurs centrés-réduits :
  #   y = c0 + somme( cj * (xj - moyenne_j) / ecart_j )
  # L'ordonnée à l'origine en unités d'origine n'est donc pas c0, mais la
  # valeur prévue lorsque tous les régresseurs sont nuls :
  #   constante = c0 - somme( cj * moyenne_j / ecart_j )
  constante_origine = float(coefs[0]) - sum(
    float(coefs[j + 1]) * float(moyennes[j]) / float(ecarts[j])
    for j in range(k)
  )

  coefficients = [{
    "nom": "constante",
    "valeur_standardisee": round(float(coefs[0]), 4),
    "valeur": round(constante_origine, 4),
    "erreur": round(erreurs[0], 4) if erreurs[0] else None,
    "t": round(t_stats[0], 3) if t_stats[0] is not None else None,
    "p": round(p_values[0], 4) if p_values[0] is not None else None,
    "vif": None,
    "significatif": (p_values[0] is not None and p_values[0] < 0.05),
  }]
  for j, nom in enumerate(noms):
    brut = float(coefs[j + 1] / ecarts[j])    # dé-standardisation
    coefficients.append({
      "nom": nom,
      "valeur_standardisee": round(float(coefs[j + 1]), 4),
      "valeur": round(brut, 6),
      "erreur": round(erreurs[j + 1], 4) if erreurs[j + 1] else None,
      "t": round(t_stats[j + 1], 3) if t_stats[j + 1] is not None else None,
      "p": round(p_values[j + 1], 4) if p_values[j + 1] is not None else None,
      "vif": round(vifs[j], 2),
      "significatif": (p_values[j + 1] is not None and p_values[j + 1] < 0.05),
    })

  alertes = []
  colineaires = [c["nom"] for c in coefficients if c["vif"] and c["vif"] > SEUIL_VIF]
  if colineaires:
    alertes.append(
      "Colinéarité forte entre régresseurs (VIF > 10) : "
      + ", ".join(colineaires)
      + ", leurs coefficients individuels sont instables, même si le "
       "pouvoir explicatif global reste valable."
    )
  if dw is not None and not (DW_BAS <= dw <= DW_HAUT):
    alertes.append(
      f"Résidus autocorrélés (Durbin-Watson = {dw:.2f}, attendu entre "
      f"{DW_BAS} et {DW_HAUT}) : les tests de significativité sont "
      "optimistes. Envisagez d'ajouter la variable décalée d'une période."
    )
  if k >= n - 2:
    alertes.append("Trop de régresseurs pour si peu d'observations : le modèle surajuste.")

  return {
    "disponible": True,
    "periodicite": periodes.inferer(cles),
    "n_observations": n,
    "n_regresseurs": k,
    "degres_liberte": ddl,
    "periode_debut": cles[0],
    "periode_fin": cles[-1],
    "coefficients": coefficients,
    "r2": round(r2, 4),
    "r2_ajuste": round(r2_ajuste, 4) if r2_ajuste is not None else None,
    "f": round(f_stat, 3) if f_stat else None,
    "p_fisher": round(f_pvalue, 5) if f_pvalue is not None else None,
    "durbin_watson": round(dw, 3) if dw is not None else None,
    "jarque_bera": round(jb, 3) if jb is not None else None,
    "p_jarque_bera": round(jb_p, 4) if jb_p is not None else None,
    "ecart_residuel": round(math.sqrt(sigma2), 4) if sigma2 else None,
    "alertes": alertes,
    "noms": noms,
    # Conservé pour la prévision : modèle en unités standardisées
    "_modele": {
      "coefs": [float(c) for c in coefs],
      "moyennes": [float(m) for m in moyennes],
      "ecarts": [float(e) for e in ecarts],
      "cles": list(cles),
      "noms": list(noms),
    },
  }


def _extrapoler(serie, cible_periodes):
  """Extrapole un régresseur par sa tendance linéaire sur les périodes voulues.

  C'est l'hypothèse la plus forte du modèle multivarié : nous n'avons pas la
  valeur future des variables explicatives. Nous prolongeons donc chacune par
  la tendance qu'elle a suivie, ce qui revient à supposer que les
  déterminants passés continuent à l'identique.
  """
  couples = sorted(
    ((p, float(v)) for p, v in serie.items() if v is not None),
    key=lambda c: periodes.cle_tri(c[0]),
  )
  if len(couples) < 2:
    return None
  rangs = np.array([periodes.rang_absolu(p) for p, _ in couples], dtype=float)
  valeurs = np.array([v for _, v in couples], dtype=float)
  A = np.column_stack([np.ones(len(rangs)), rangs])
  try:
    coefs, *_ = np.linalg.lstsq(A, valeurs, rcond=None)
  except np.linalg.LinAlgError:
    return None
  rangs_cible = np.array([periodes.rang_absolu(p) for p in cible_periodes], dtype=float)
  return coefs[0] + coefs[1] * rangs_cible


def prevoir(serie_cible, series_explicatives, horizon=3):
  """Prévoit la cible à ``horizon`` périodes, à partir du modèle ajusté.

  Les variables explicatives futures sont extrapolées par leur tendance, une
  hypothèse affichée dans les alertes, car l'incertitude qu'elle ajoute est
  réelle et souvent supérieure à l'erreur du modèle lui-même.
  """
  modele = ajuster(serie_cible, series_explicatives)
  if not modele["disponible"]:
    return modele

  per = modele["periodicite"]
  dernieres = modele["_modele"]["cles"]
  n = periodes.RANGS_PAR_AN.get(per, 1)
  d = periodes.decomposer(dernieres[-1])
  if not d:
    return {"disponible": False, "raison": "période finale illisible"}
  annee, rang, _ = d

  futures = []
  a, r = annee, rang
  for _ in range(horizon):
    r += 1
    if r > n:
      r = 1
      a += 1
    futures.append(periodes.formater(a, r, per))

  # Reconstitution du modèle en unités standardisées
  m = modele["_modele"]
  coefs = np.array(m["coefs"])

  colonnes = []
  for nom, serie in series_explicatives:
    valeurs = _extrapoler(serie, futures)
    if valeurs is None:
      return {"disponible": False,
          "raison": f"impossible d'extrapoler « {nom} »"}
    colonnes.append(valeurs)
  X_futur = np.column_stack(colonnes) if colonnes else np.zeros((horizon, 0))

  moyennes = np.array(m["moyennes"])
  ecarts = np.array(m["ecarts"])
  X_std = (X_futur - moyennes) / ecarts
  A = np.column_stack([np.ones(horizon), X_std])
  predits = A @ coefs

  # Intervalle de prévision à 80 %, au niveau moyen : l'erreur du modèle,
  # majorée par celle des régresseurs extrapolés.
  ecart = modele["ecart_residuel"] or 0.0
  marge = 1.2816 * ecart     # quantile normal à 80 %

  points = []
  for i, p in enumerate(futures):
    points.append({
      "periode": p,
      "libelle": periodes.libelle(p, per),
      "valeur": round(float(predits[i]), 4),
      "bas": round(float(predits[i] - marge), 4),
      "haut": round(float(predits[i] + marge), 4),
    })

  alertes = list(modele["alertes"])
  alertes.append(
    "Les variables explicatives futures sont extrapolées par leur tendance : "
    "l'incertitude affichée ne couvre que l'erreur du modèle, pas celle des "
    "régresseurs. L'intervalle réel est donc plus large."
  )

  return {
    "disponible": True,
    "modele": modele,
    "points": points,
    "intervalle": "80 % (erreur du modèle seul)",
    "alertes": alertes,
  }


def synthese(resultat):
  """Phrase de synthèse, en français, prête à être lue.

  Accepte les deux formes de retour du module :

  - le résultat d'``ajuster``, où les statistiques sont à la racine ;
  - le résultat de ``prevoir``, où l'ajustement est imbriqué sous ``modele``
   et où les alertes de projection s'ajoutent à celles du modèle.
  """
  if not resultat or not resultat.get("disponible"):
    return (resultat or {}).get("raison", "modèle indisponible")

  modele = resultat.get("modele", resultat)
  alertes = resultat.get("alertes") or modele.get("alertes") or []

  parties = [
    f"Le modèle explique {modele['r2']:.1%} de la variance de la cible "
    f"(R² ajusté {modele['r2_ajuste']:.1%}) sur {modele['n_observations']} "
    f"observations."
  ]
  significatifs = [c["nom"] for c in modele["coefficients"]
           if c["nom"] != "constante" and c["significatif"]]
  if significatifs:
    parties.append(
      "Variables significatives au seuil de 5 % : "
      + ", ".join(significatifs) + "."
    )
  else:
    parties.append("Aucun régresseur n'est significatif au seuil de 5 %.")
  if alertes:
    parties.append(alertes[0])
  return " ".join(parties)
