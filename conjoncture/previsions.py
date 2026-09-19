"""
Prédictions économiques, modèles comparés.

Quatre modèles sont ajustés sur la même série, évalués sur les mêmes
observations retenues, puis comparés par deux mesures d'erreur :

1. **Tendance linéaire (MCO)**, la référence simple, déjà présente dans la
  plateforme. Elle sert de point de comparaison : un modèle plus complexe qui
  ne la bat pas ne mérite pas d'être retenu.
2. **Lissage exponentiel de Holt**, tendance sans saisonnalité. Robuste sur
  séries courtes.
3. **Holt-Winters**, tendance et saisonnalité. Pertinent à partir de deux
  cycles complets (séries mensuelles ou trimestrielles).
4. **ARIMA**, modèle autorégressif à moyenne mobile, sélectionné par AIC sur
  une grille d'ordres restreinte.

Évaluation honnête : la série est coupée en deux, apprentissage puis test. Les
modèles sont ajustés sur l'apprentissage seul, on prédit la partie test, et on
mesure l'erreur hors échantillon. C'est ce chiffre-là qui compte, pas la qualité
d'ajustement sur les données déjà connues.

Mesures d'erreur :

- **RMSE**, racine de l'erreur quadratique moyenne, dans l'unité de la série.
- **MAPE**, erreur absolue moyenne en pourcentage, seulement si la série ne
 contient pas de zéro ni de valeurs qui changent de signe.
- **MAE**, erreur absolue moyenne, plus lisible que le RMSE.
"""
from __future__ import annotations

import math

import numpy as np

from . import periodes


# --- Préparation --------------------------------------------------------------
def _serie_numerique(serie):
  """Trie une série {période: valeur} et retourne (périodes, valeurs, rangs)."""
  periodes_triees = sorted(serie, key=periodes.cle_tri)
  periodes_triees = [p for p in periodes_triees if serie[p] is not None]
  if len(periodes_triees) < 5:
    return [], [], [], None
  valeurs = np.array([float(serie[p]) for p in periodes_triees], dtype=float)
  rangs = np.array([periodes.rang_absolu(p) for p in periodes_triees], dtype=float)
  periodicite = periodes.inferer(periodes_triees)
  return periodes_triees, valeurs, rangs, periodicite


def _pas(periodicite):
  """Pas d'une période dans l'échelle du rang absolu."""
  return 1.0 / periodes.RANGS_PAR_AN.get(periodicite, 1)


def _saisonnalite(periodicite):
  """Nombre de points par cycle saisonnier, ou None."""
  n = periodes.RANGS_PAR_AN.get(periodicite, 1)
  return n if n >= 2 else None


# --- Mesures d'erreur ---------------------------------------------------------
def mesures_erreur(reels, predits, serie_complete=None):
  """RMSE, MAE et MAPE.

  La MAPE n'a de sens que si les valeurs sont strictement du même signe et
  jamais proches de zéro. On l'évalue sur la série **entière** lorsqu'elle est
  fournie, car un segment de test qui ne croise pas zéro peut malgré tout
  appartenir à une série qui, elle, le croise.
  """
  r = np.asarray(reels, dtype=float)
  p = np.asarray(predits, dtype=float)
  if r.size == 0 or r.size != p.size:
    return None
  ecarts = r - p
  rmse = float(np.sqrt(np.mean(ecarts ** 2)))
  mae = float(np.mean(np.abs(ecarts)))

  reference = np.asarray(serie_complete, dtype=float) if serie_complete is not None else r
  mape = None
  if (np.all(np.abs(reference) > 1e-6)
      and not (np.any(reference > 0) and np.any(reference < 0))):
    mape = float(np.mean(np.abs(ecarts / r)) * 100)
  return {
    "rmse": round(rmse, 4),
    "mae": round(mae, 4),
    "mape": round(mape, 2) if mape is not None else None,
  }


# --- Modèle 1 : tendance linéaire (MCO) --------------------------------------
def _ajuster_mco(rangs, valeurs):
  n = len(rangs)
  moyenne_x, moyenne_y = rangs.mean(), valeurs.mean()
  xc = rangs - moyenne_x
  denom = float(np.sum(xc ** 2))
  if denom == 0:
    return None
  pente = float(np.sum(xc * (valeurs - moyenne_y)) / denom)
  ordonnee = float(moyenne_y - pente * moyenne_x)
  return pente, ordonnee


def _predire_mco(modele, rangs):
  pente, ordonnee = modele
  return ordonnee + pente * np.asarray(rangs, dtype=float)


# --- Modèle 2 : Holt (tendance lissée) ---------------------------------------
def _holt(valeurs, alpha=0.5, beta=0.3):
  """Lissage exponentiel de Holt : niveau + tendance."""
  niveau = float(valeurs[0])
  tendance = float(valeurs[1] - valeurs[0]) if len(valeurs) > 1 else 0.0
  predictions = [niveau]
  for y in valeurs[1:]:
    prevu = niveau + tendance
    predictions.append(prevu)
    nouveau_niveau = alpha * y + (1 - alpha) * (niveau + tendance)
    tendance = beta * (nouveau_niveau - niveau) + (1 - beta) * tendance
    niveau = nouveau_niveau
  return {"niveau": niveau, "tendance": tendance, "ajustes": predictions}


def _predire_holt(modele, h):
  return np.array([modele["niveau"] + modele["tendance"] * (i + 1) for i in range(h)])


# --- Modèle 3 : Holt-Winters (tendance + saisonnalité) -----------------------
def _holt_winters(valeurs, periode, alpha=0.4, beta=0.2, gamma=0.3):
  """Holt-Winters additif. Nécessite au moins deux cycles complets."""
  n = len(valeurs)
  if periode is None or n < 2 * periode:
    return None
  # Initialisation : moyennes par saison et tendance de premier cycle.
  moyennes_saison = [
    float(np.mean(valeurs[i::periode])) for i in range(periode)
  ]
  niveau = float(np.mean(valeurs[:periode]))
  tendance = float((np.mean(valeurs[periode:2 * periode]) - np.mean(valeurs[:periode])) / periode)

  saisons = list(valeurs[:periode] - np.mean(valeurs[:periode]))
  ajustes = []
  for i, y in enumerate(valeurs):
    s = saisons[i % periode]
    prevu = niveau + tendance + s
    ajustes.append(prevu)
    ancien_niveau = niveau
    niveau = alpha * (y - s) + (1 - alpha) * (niveau + tendance)
    tendance = beta * (niveau - ancien_niveau) + (1 - beta) * tendance
    saisons[i % periode] = gamma * (y - niveau) + (1 - gamma) * s
  return {
    "niveau": niveau, "tendance": tendance, "saisons": saisons,
    "periode": periode, "ajustes": ajustes,
    "dernier_index": n - 1,
  }


def _predire_holt_winters(modele, h):
  sortie = []
  for i in range(h):
    s = modele["saisons"][(modele["dernier_index"] + 1 + i) % modele["periode"]]
    sortie.append(modele["niveau"] + modele["tendance"] * (i + 1) + s)
  return np.array(sortie)


# --- Modèle 4 : ARIMA --------------------------------------------------------
def _ajuster_arima(valeurs, ordres=((1, 1, 0), (0, 1, 1), (1, 1, 1), (2, 1, 1), (1, 1, 2), (2, 1, 2), (0, 1, 0))):
  """Sélectionne le meilleur ARIMA par AIC sur une grille restreinte."""
  try:
    import warnings

    from statsmodels.tsa.arima.model import ARIMA
  except ImportError:
    return None
  meilleur = None
  with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for ordre in ordres:
      try:
        modele = ARIMA(valeurs, order=ordre).fit()
        if meilleur is None or modele.aic < meilleur[1]:
          meilleur = (modele, float(modele.aic), ordre)
      except Exception:
        continue
  if meilleur is None:
    return None
  return {"modele": meilleur[0], "aic": round(meilleur[1], 2), "ordre": meilleur[2]}


def _predire_arima(modele, h):
  try:
    prev = modele["modele"].forecast(steps=h)
    return np.asarray(prev, dtype=float)
  except Exception:
    return None


# --- Orchestration ------------------------------------------------------------
def comparer_modeles(serie, horizon=3, part_test=0.25):
  """Ajuste les quatre modèles, les évalue hors échantillon, retient le meilleur.

  Retourne un dictionnaire prêt à afficher, ou ``None`` si la série est trop
  courte.
  """
  periodes_triees, valeurs, rangs, periodicite = _serie_numerique(serie)
  if len(valeurs) < 6:
    return None

  n = len(valeurs)
  n_test = max(2, int(round(n * part_test)))
  n_test = min(n_test, n - 4)     # il faut au moins 4 points d'apprentissage
  if n_test < 1:
    return None
  n_apprentissage = n - n_test
  y_app, y_test = valeurs[:n_apprentissage], valeurs[n_apprentissage:]
  x_app, x_test = rangs[:n_apprentissage], rangs[n_apprentissage:]
  periode_saison = _saisonnalite(periodicite)

  resultats = []

  # 1. MCO
  modele_mco = _ajuster_mco(x_app, y_app)
  scores_mco = mesures_erreur(y_test, _predire_mco(modele_mco, x_test), serie_complete=valeurs) if modele_mco else None
  resultats.append({
    "cle": "mco", "nom": "Tendance linéaire (MCO)",
    "note": "Référence simple : une droite de tendance.",
    "scores": scores_mco, "disponible": scores_mco is not None,
  })

  # 2. Holt
  hw = _holt(y_app)
  scores_holt = mesures_erreur(y_test, _predire_holt(hw, n_test), serie_complete=valeurs)
  resultats.append({
    "cle": "holt", "nom": "Lissage exponentiel de Holt",
    "note": "Suit le niveau et la tendance, sans saisonnalité.",
    "scores": scores_holt, "disponible": scores_holt is not None,
  })

  # 3. Holt-Winters
  hws = _holt_winters(y_app, periode_saison)
  scores_hws = mesures_erreur(y_test, _predire_holt_winters(hws, n_test), serie_complete=valeurs) if hws else None
  resultats.append({
    "cle": "holt_winters", "nom": "Holt-Winters (tendance + saisonnalité)",
    "note": (f"Saisonnalité de {periode_saison} points, "
         f"périodicité {periodicite}." if periode_saison
         else "Série annuelle : pas de saisonnalité exploitable."),
    "scores": scores_hws, "disponible": scores_hws is not None,
  })

  # 4. ARIMA
  arima = _ajuster_arima(y_app)
  prev_arima = _predire_arima(arima, n_test) if arima else None
  scores_arima = mesures_erreur(y_test, prev_arima, serie_complete=valeurs) if prev_arima is not None else None
  resultats.append({
    "cle": "arima", "nom": "ARIMA",
    "note": (f"Ordre retenu {arima['ordre']}, AIC {arima['aic']}."
         if arima else "Ajustement impossible sur cette série."),
    "scores": scores_arima, "disponible": scores_arima is not None,
  })

  # Choix du meilleur : RMSE hors échantillon, la plus faible.
  candidats = [r for r in resultats if r["disponible"] and r["scores"]]
  meilleur = min(candidats, key=lambda r: r["scores"]["rmse"]) if candidats else None
  if meilleur:
    meilleur["retenu"] = True

  # Projection finale : le modèle retenu est réajusté sur toute la série.
  projection = _projeter(meilleur["cle"], periodes_triees, valeurs, rangs,
              horizon, periode_saison)
  if meilleur and projection:
    meilleur["projection"] = projection["points"]

  return {
    "periodicite": periodicite,
    "nb_observations": n,
    "n_apprentissage": n_apprentissage,
    "n_test": n_test,
    "debut": periodes_triees[0],
    "fin": periodes_triees[-1],
    "derniere_valeur": round(float(valeurs[-1]), 3),
    "derniere_periode": periodes_triees[-1],
    "modeles": resultats,
    "meilleur": meilleur,
    "projection": projection,
  }


def _projeter(cle, periodes_triees, valeurs, rangs, horizon, periode_saison):
  """Réajuste le modèle retenu sur toute la série et projette l'horizon."""
  pas = _pas(periodes.inferer(periodes_triees))
  dernier_rang = float(rangs[-1])
  rangs_futurs = [dernier_rang + pas * (i + 1) for i in range(horizon)]

  # Étiquettes des périodes futures.
  annee_fin, rang_fin, periodicite = periodes.decomposer(periodes_triees[-1])
  n_par_an = periodes.RANGS_PAR_AN.get(periodicite, 1)
  etiquettes = []
  for i in range(1, horizon + 1):
    rang_absolu = rang_fin + i
    annee = annee_fin + (rang_absolu - 1) // n_par_an
    rang = (rang_absolu - 1) % n_par_an + 1
    etiquettes.append(periodes.formater(annee, rang, periodicite))

  if cle == "mco":
    modele = _ajuster_mco(rangs, valeurs)
    if not modele:
      return None
    predits = _predire_mco(modele, rangs_futurs)
    residus = valeurs - _predire_mco(modele, rangs)
    erreur = float(np.std(residus, ddof=2)) if len(residus) > 2 else float(np.std(residus))
    marge = 1.28 * erreur
    points = [
      {
        "periode": etiquettes[i],
        "valeur": round(float(predits[i]), 3),
        "bas": round(float(predits[i] - marge), 3),
        "haut": round(float(predits[i] + marge), 3),
      }
      for i in range(horizon)
    ]
    return {"points": points, "methode": "Tendance linéaire (MCO)",
        "intervalle": "80 % (erreur type résiduelle)"}

  if cle == "holt":
    hw = _holt(valeurs)
    predits = _predire_holt(hw, horizon)
    residus = valeurs - np.array(hw["ajustes"])
    erreur = float(np.std(residus))
    marge = 1.28 * erreur
    points = [
      {
        "periode": etiquettes[i],
        "valeur": round(float(predits[i]), 3),
        "bas": round(float(predits[i] - marge), 3),
        "haut": round(float(predits[i] + marge), 3),
      }
      for i in range(horizon)
    ]
    return {"points": points, "methode": "Lissage exponentiel de Holt",
        "intervalle": "80 % (écart-type des résidus)"}

  if cle == "holt_winters":
    hws = _holt_winters(valeurs, periode_saison)
    if not hws:
      return None
    predits = _predire_holt_winters(hws, horizon)
    residus = valeurs - np.array(hws["ajustes"])
    erreur = float(np.std(residus))
    marge = 1.28 * erreur
    points = [
      {
        "periode": etiquettes[i],
        "valeur": round(float(predits[i]), 3),
        "bas": round(float(predits[i] - marge), 3),
        "haut": round(float(predits[i] + marge), 3),
      }
      for i in range(horizon)
    ]
    return {"points": points, "methode": "Holt-Winters",
        "intervalle": "80 % (écart-type des résidus)"}

  if cle == "arima":
    arima = _ajuster_arima(valeurs)
    if not arima:
      return None
    try:
      prevision = arima["modele"].get_forecast(steps=horizon)
      moyennes = np.asarray(prevision.predicted_mean, dtype=float)
      try:
        ic = np.asarray(prevision.conf_int(alpha=0.2), dtype=float)
      except Exception:
        ic = None
      points = []
      for i in range(horizon):
        points.append({
          "periode": etiquettes[i],
          "valeur": round(float(moyennes[i]), 3),
          "bas": round(float(ic[i][0]), 3) if ic is not None else None,
          "haut": round(float(ic[i][1]), 3) if ic is not None else None,
        })
      return {"points": points, "methode": f"ARIMA{arima['ordre']}",
          "intervalle": "80 % (intervalle de prévision du modèle)",
          "note": ("Le modèle retenu a été réajusté sur la série complète ; "
               "l'ordre peut différer de celui sélectionné sur "
               "l'échantillon d'apprentissage.")}
    except Exception:
      return None

  return None


def synthese(comparaison):
  """Phrase de lecture pour l'affichage et les rapports."""
  if not comparaison or not comparaison.get("meilleur"):
    return "Série trop courte pour comparer des modèles de prévision."
  m = comparaison["meilleur"]
  s = m["scores"]
  parties = [f"Sur cette série ({comparaison['debut']} → {comparaison['fin']}, "
        f"{comparaison['nb_observations']} points), le modèle retenu est "
        f"« {m['nom']} », évalué hors échantillon sur les "
        f"{comparaison['n_test']} dernières périodes : "]
  if s.get("mape") is not None:
    parties.append(f"erreur moyenne de {s['mape']} % (MAPE), ")
  parties.append(f"RMSE de {s['rmse']} et erreur absolue moyenne de {s['mae']}.")
  if comparaison.get("projection"):
    p = comparaison["projection"]["points"][-1]
    parties.append(
      f" Projection à l'horizon {p['periode']} : {p['valeur']}"
      + (f" (intervalle {p['bas']} – {p['haut']})." if p.get("bas") is not None else ".")
    )
  return "".join(parties)
