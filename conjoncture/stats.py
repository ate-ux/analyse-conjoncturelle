"""
Module d'analyse statistique de la plateforme.

Méthodes mobilisées, toutes sourcées et reproductibles :

1. **Statistiques descriptives**, moyenne, médiane, écart-type, coefficient de
  variation, min/max, indice de concentration (HHI) pour les régions.
2. **Analyse de tendance**, régression linéaire par moindres carrés ordinaires
  (MCO) sur les séries annuelles : pente, R², erreur standard, p-value,
  intervalle de prévision.
3. **Prévision**, extrapolation linéaire à court terme, avec borne basse et
  haute fondée sur l'erreur type résiduelle.
4. **Analyse de corrélation**, coefficient de Pearson entre deux indicateurs,
  avec p-value, sur la période commune.

Toutes les fonctions retournent des structures simples (dicts / listes),
directement exploitables par les gabarits et le générateur de rapports.
"""
from __future__ import annotations

import math

import numpy as np

from .data import economie


# --- 1. Statistiques descriptives --------------------------------------------
def descriptives(valeurs):
  """Statistiques descriptives d'une liste de nombres."""
  v = [float(x) for x in valeurs if x is not None]
  if not v:
    return None
  arr = np.array(v)
  moyenne = float(arr.mean())
  ecart_type = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
  return {
    "n": len(v),
    "moyenne": round(moyenne, 3),
    "mediane": round(float(np.median(arr)), 3),
    "ecart_type": round(ecart_type, 3),
    "cv": round(ecart_type / moyenne * 100, 2) if moyenne else None,
    "minimum": round(float(arr.min()), 3),
    "maximum": round(float(arr.max()), 3),
    "etendue": round(float(arr.max() - arr.min()), 3),
  }


def indice_concentration(valeurs):
  """Indice de Herfindahl-Hirschman (HHI) : mesure la concentration.

  Interprétation usuelle : < 1500 concentré faiblement, 1500-2500 modéré,
  > 2500 fortement concentré.
  """
  v = [float(x) for x in valeurs if x]
  total = sum(v)
  if not total:
    return None
  parts = [x / total for x in v]
  hhi = sum((p * 100) ** 2 for p in parts)
  if hhi < 1500:
    lecture = "concentration faible"
  elif hhi <= 2500:
    lecture = "concentration modérée"
  else:
    lecture = "concentration forte"
  return {"valeur": round(hhi, 1), "lecture": lecture}


# --- 2. Analyse de tendance (MCO) --------------------------------------------
def tendance(serie):
  """Régression linéaire par MCO sur une série {année: valeur}.

  Retourne la pente annuelle, le R², l'erreur standard de la pente, la
  p-value, et l'équation de la droite.
  """
  if not serie:
    return None
  annees = np.array(sorted(int(a) for a in serie), dtype=float)
  valeurs = np.array([float(serie[int(a)]) for a in annees], dtype=float)
  n = len(annees)
  if n < 3:
    return None

  x = annees - annees.mean()
  y = valeurs
  pente = float(np.sum(x * y) / np.sum(x * x))
  ordonnee = float(y.mean() - pente * annees.mean())

  y_pred = ordonnee + pente * annees
  residus = y - y_pred
  sst = float(np.sum((y - y.mean()) ** 2))
  sse = float(np.sum(residus ** 2))
  r2 = 1 - sse / sst if sst else 0.0

  # Erreur standard de la pente et statistique de Student
  dl = n - 2
  if dl > 0:
    s2 = sse / dl
    erreur_pente = math.sqrt(s2 / float(np.sum(x * x))) if np.sum(x * x) else None
  else:
    erreur_pente = None

  p_value = None
  t_stat = None
  if erreur_pente:
    t_stat = pente / erreur_pente
    try:
      from scipy import stats as st
      p_value = float(2 * (1 - st.t.cdf(abs(t_stat), dl)))
    except Exception:
      p_value = None

  if pente > 0:
    lecture = "tendance haussière"
  elif pente < 0:
    lecture = "tendance baissière"
  else:
    lecture = "tendance stable"

  return {
    "pente": round(pente, 4),
    "ordonnee": round(ordonnee, 2),
    "r2": round(r2, 4),
    "erreur_pente": round(erreur_pente, 4) if erreur_pente else None,
    "t_stat": round(t_stat, 3) if t_stat else None,
    "p_value": round(p_value, 4) if p_value is not None else None,
    "significatif": bool(p_value is not None and p_value < 0.05),
    "erreur_standard": round(math.sqrt(sse / dl), 3) if dl > 0 else None,
    "debut": int(annees[0]),
    "fin": int(annees[-1]),
    "n": n,
    "lecture": lecture,
    "equation": f"y = {ordonnee:.2f} {'+' if pente >= 0 else '−'} "
          f"{abs(pente):.2f} × année",
  }


# --- 3. Prévision ------------------------------------------------------------
def prevision(serie, horizon=3):
  """Extrapolation linéaire à court terme, avec intervalle de prévision à 80 %.

  L'intervalle est fondé sur l'erreur type résiduelle de la régression.
  """
  t = tendance(serie)
  if not t:
    return None
  annees = sorted(int(a) for a in serie)
  derniere = annees[-1]
  erreur = t.get("erreur_standard") or 0.0
  marge = 1.28 * erreur # ~80 % de confiance

  points = []
  for i in range(1, horizon + 1):
    annee = derniere + i
    valeur = t["ordonnee"] + t["pente"] * annee
    points.append({
      "annee": annee,
      "valeur": round(valeur, 2),
      "bas": round(valeur - marge, 2),
      "haut": round(valeur + marge, 2),
    })
  return {"points": points, "modele": t}


# --- 4. Corrélation ----------------------------------------------------------
def correlation(serie_a, serie_b):
  """Coefficient de Pearson entre deux séries, sur les années communes."""
  annees = sorted(set(int(a) for a in serie_a) & set(int(a) for a in serie_b))
  if len(annees) < 3:
    return None
  a = np.array([float(serie_a[int(x)]) for x in annees])
  b = np.array([float(serie_b[int(x)]) for x in annees])
  if a.std() == 0 or b.std() == 0:
    return None
  r = float(np.corrcoef(a, b)[0, 1])
  p_value = None
  try:
    from scipy import stats as st
    r_s, p_value = st.pearsonr(a, b)
    p_value = float(p_value)
  except Exception:
    pas = None

  if abs(r) >= 0.7:
    force = "forte"
  elif abs(r) >= 0.4:
    force = "modérée"
  else:
    force = "faible"

  return {
    "r": round(r, 3),
    "r2": round(r * r, 3),
    "p_value": round(p_value, 4) if p_value is not None else None,
    "significatif": bool(p_value is not None and p_value < 0.05),
    "sens": "positive" if r >= 0 else "négative",
    "force": force,
    "n": len(annees),
    "annees": annees,
  }


# --- 5. Vues d'ensemble prêtes pour l'affichage ------------------------------
def analyse_indicateur(cle):
  """Analyse complète d'un indicateur national : descriptif + tendance + prévision."""
  ind = economie.INDICATEURS_NATIONAUX.get(cle)
  if not ind:
    return None
  serie = ind["serie"]
  return {
    "cle": cle,
    "libelle": ind["libelle"],
    "unite": ind["unite"],
    "source": economie.SOURCES.get(ind["source"], {}).get("nom", ""),
    "serie": serie,
    "descriptif": descriptives(list(serie.values())),
    "tendance": tendance(serie),
    "prevision": prevision(serie, 3),
    "commentaire": ind.get("commentaire", ""),
    "seuil": ind.get("seuil"),
    "seuil_libelle": ind.get("seuil_libelle"),
  }


def analyse_globale():
  """Analyse de tous les indicateurs nationaux."""
  return {
    cle: analyse_indicateur(cle)
    for cle in economie.INDICATEURS_NATIONAUX
  }


def analyse_regionale():
  """Statistiques descriptives sur les régions : population, pauvreté, densité."""
  regions = economie.tableau_regions()
  populations = [r["population"] for r in regions]
  pauvrete = [r["pauvrete"] for r in regions]
  densite = [r["densite"] for r in regions]
  return {
    "regions": regions,
    "population": descriptives(populations),
    "pauvrete": descriptives(pauvrete),
    "densite": descriptives(densite),
    "concentration_population": indice_concentration(populations),
    "concentration_pauvrete": indice_concentration(pauvrete),
    "ecart_pauvrete": {
      "max": max(regions, key=lambda r: r["pauvrete"]),
      "min": min(regions, key=lambda r: r["pauvrete"]),
    },
  }


def analyse_cemac():
  """Statistiques descriptives sur les six pays de la CEMAC (2025)."""
  lignes = economie.tableau_cemac("2025")
  croissance = [l["croissance"] for l in lignes if l["croissance"] is not None]
  inflation = [l["inflation"] for l in lignes if l["inflation"] is not None]
  pib = [l["pib_mds"] for l in lignes if l["pib_mds"]]
  return {
    "pays": lignes,
    "croissance": descriptives(croissance),
    "inflation": descriptives(inflation),
    "pib": descriptives(pib),
    "concentration_pib": indice_concentration(pib),
    "totaux": economie.totaux_cemac("2025"),
  }


def correlations_principales():
  """Corrélations entre indicateurs nationaux (paires les plus pertinentes)."""
  ind = economie.INDICATEURS_NATIONAUX
  paires = [
    ("inflation", "pauvrete"),
    ("pib_croissance", "chomage"),
    ("pib_par_habitant", "inflation"),
    ("pib_croissance", "pib_par_habitant"),
  ]
  resultats = []
  for a, b in paires:
    if a in ind and b in ind:
      c = correlation(ind[a]["serie"], ind[b]["serie"])
      if c:
        resultats.append({
          "a": ind[a]["libelle"],
          "b": ind[b]["libelle"],
          "cle_a": a, "cle_b": b,
          **c,
        })
  return resultats
