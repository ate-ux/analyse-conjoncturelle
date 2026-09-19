"""
Désaisonnalisation des séries infra-annuelles.

Une série trimestrielle ou mensuelle superpose trois mouvements : une tendance
de fond, une saisonnalité qui revient chaque année, et un résidu irrégulier.
Confondre les trois fait lire une embellie saisonnière comme une reprise, une
erreur classique en analyse conjoncturelle.

Ce module met en œuvre la décomposition classique :

- **tendance** par moyenne mobile centrée, dont la longueur est celle du cycle
 saisonnier (4 pour un trimestre, 12 pour un mois) ;
- **coefficients saisonniers** estimés en rapportant chaque observation à la
 tendance, puis moyennés par rang, et recentrés pour que leur moyenne soit
 nulle (modèle additif) ou égale à 1 (modèle multiplicatif) ;
- **série désaisonnalisée** (CVS), obtenue en retirant la composante
 saisonnière de la série observée ;
- **résidu** et sa dispersion, qui disent la qualité de l'ajustement.

Toutes les fonctions raisonnent sur des dictionnaires ``{periode: valeur}``,
comme le reste de la plateforme, et ne dépendent que de la bibliothèque
standard.
"""
from __future__ import annotations

import math

from . import periodes

# Nombre de rangs par an, selon la périodicité.
RANGS_PAR_AN = periodes.RANGS_PAR_AN


def _trier(serie):
  """Retourne ``[(periode, valeur)]`` trié chronologiquement, valeurs valides."""
  couples = []
  for periode, valeur in serie.items():
    if valeur is None:
      continue
    try:
      v = float(valeur)
    except (TypeError, ValueError):
      continue
    if math.isnan(v) or math.isinf(v):
      continue
    couples.append((periode, v))
  couples.sort(key=lambda c: periodes.cle_tri(c[0]))
  return couples


def moyenne_mobile(couples, longueur):
  """Moyenne mobile centrée sur ``longueur`` points.

  Retourne un dictionnaire ``{index: moyenne}`` où l'indice repère la position
  dans la liste. Les extrémités, où la fenêtre dépasse, sont absentes.

  Pour une longueur paire, la moyenne est centrée en combinant deux moyennes
  glissantes : sans cela, le centre tomberait entre deux observations et
  décalerait la tendance d'un demi-pas.
  """
  valeurs = [v for _, v in couples]
  n = len(valeurs)
  resultat = {}
  if longueur < 2 or n < longueur:
    return resultat

  demi = longueur // 2
  paire = longueur % 2 == 0

  for i in range(n):
    if paire:
      # Moyenne mobile centrée d'ordre pair : moyenne de deux moyennes
      # glissantes de ``longueur`` points, décalées d'un cran. Chaque
      # fenêtre doit contenir exactement ``longueur`` valeurs, c'est
      # l'erreur qui faussait la tendance d'un facteur (L-1)/L.
      debut_1, fin_1 = i - demi + 1, i + demi + 1
      debut_2, fin_2 = i - demi, i + demi
      if debut_1 < 0 or fin_1 > n or debut_2 < 0 or fin_2 > n:
        continue
      m1 = sum(valeurs[debut_1:fin_1]) / longueur
      m2 = sum(valeurs[debut_2:fin_2]) / longueur
      resultat[i] = (m1 + m2) / 2
    else:
      debut, fin = i - demi, i + demi + 1
      if debut < 0 or fin > n:
        continue
      resultat[i] = sum(valeurs[debut:fin]) / longueur
  return resultat


def tendance(serie, periodicite=None):
  """Tendance par moyenne mobile, au pas de la saisonnalité."""
  couples = _trier(serie)
  if not couples:
    return {}
  per = periodicite or periodes.inferer([p for p, _ in couples])
  longueur = RANGS_PAR_AN.get(per, 1)
  if longueur <= 1:
    # Série annuelle : aucune saisonnalité à extraire, la tendance est la
    # moyenne mobile sur trois points, ou la série elle-même si trop courte.
    longueur = 3
  moyennes = moyenne_mobile(couples, longueur)
  return {couples[i][0]: v for i, v in moyennes.items()}


def _moyenne(valeurs):
  return sum(valeurs) / len(valeurs) if valeurs else 0.0


def _ecart_type(valeurs):
  if len(valeurs) < 2:
    return 0.0
  m = _moyenne(valeurs)
  return math.sqrt(sum((v - m) ** 2 for v in valeurs) / (len(valeurs) - 1))


def coefficients_saisonniers(serie, modele="additif", periodicite=None):
  """Estime les coefficients saisonniers, un par rang.

  ``modele`` vaut ``"additif"`` (l'écart saisonnier s'ajoute au niveau) ou
  ``"multiplicatif"`` (il le multiplie). Le choix dépend de l'allure de la
  série : le multiplicatif convient quand l'amplitude saisonnière croît avec
  le niveau, ce qui est fréquent sur les séries nominales.
  """
  couples = _trier(serie)
  if not couples:
    return {"coefficients": {}, "modele": modele, "rangs": 0}

  per = periodicite or periodes.inferer([p for p, _ in couples])
  n_rangs = RANGS_PAR_AN.get(per, 1)
  if n_rangs <= 1:
    return {"coefficients": {}, "modele": modele, "rangs": 1}

  tend = tendance(serie, per)
  # Rapport au trend : différence (additif) ou quotient (multiplicatif)
  par_rang = {r: [] for r in range(1, n_rangs + 1)}
  for periode, valeur in couples:
    if periode not in tend:
      continue
    t = tend[periode]
    d = periodes.decomposer(periode)
    if not d:
      continue
    rang = d[1]
    if modele == "multiplicatif":
      if t != 0:
        par_rang[rang].append(valeur / t)
    else:
      par_rang[rang].append(valeur - t)

  bruts = {}
  for rang in range(1, n_rangs + 1):
    obs = par_rang[rang]
    if obs:
      # Moyenne tronquée : on écarte la plus forte et la plus faible
      # lorsqu'il y a assez d'observations, pour limiter l'effet d'une
      # année atypique sur un coefficient qui doit rester stable.
      if len(obs) >= 5:
        triees = sorted(obs)
        retenues = triees[1:-1]
      else:
        retenues = obs
      bruts[rang] = _moyenne(retenues)
    else:
      bruts[rang] = 0.0 if modele == "additif" else 1.0

  # Recentrage : la somme des coefficients doit être nulle (additif) ou leur
  # moyenne égale à 1 (multiplicatif), sinon la désaisonnalisation biaise le
  # niveau général de la série.
  if modele == "multiplicatif":
    moyenne_coef = _moyenne(list(bruts.values())) or 1.0
    coefficients = {r: (v / moyenne_coef) for r, v in bruts.items()}
  else:
    moyenne_coef = _moyenne(list(bruts.values()))
    coefficients = {r: (v - moyenne_coef) for r, v in bruts.items()}

  return {
    "coefficients": coefficients,
    "modele": modele,
    "rangs": n_rangs,
    "periodicite": per,
  }


def dessaisonaliser(serie, modele="additif", periodicite=None):
  """Retire la composante saisonnière de chaque observation.

  Retourne un dictionnaire ``{periode: valeur CVS}``. Les périodes sont
  renvoyées telles quelles : la série corrigée couvre exactement la même
  étendue que la série d'origine.
  """
  estimation = coefficients_saisonniers(serie, modele, periodicite)
  coefs = estimation["coefficients"]
  if not coefs:
    # Série annuelle : rien à corriger, on renvoie la série telle quelle.
    return {p: v for p, v in _trier(serie)}

  resultat = {}
  for periode, valeur in _trier(serie):
    d = periodes.decomposer(periode)
    if not d:
      continue
    rang = d[1]
    c = coefs.get(rang, 0.0 if modele == "additif" else 1.0)
    if modele == "multiplicatif":
      resultat[periode] = valeur / c if c else valeur
    else:
      resultat[periode] = valeur - c
  return resultat


def decomposer(serie, modele="additif", periodicite=None):
  """Décomposition complète : tendance, saisonnalité, résidu, CVS.

  Retourne un dictionnaire prêt à afficher, avec les séries alignées et des
  indicateurs de qualité.
  """
  couples = _trier(serie)
  if not couples:
    return {"disponible": False, "raison": "série vide"}

  estimation = coefficients_saisonniers(serie, modele, periodicite)
  coefs = estimation["coefficients"]
  per = estimation.get("periodicite") or periodes.inferer([p for p, _ in couples])

  if not coefs:
    return {
      "disponible": False,
      "raison": ("série annuelle : aucune saisonnalité intra-annuelle à "
            "extraire"),
      "periodicite": per,
    }

  tend = tendance(serie, per)
  cvs = dessaisonaliser(serie, modele, per)

  # Nombre de cycles complets : sans au moins deux années, un coefficient
  # saisonnier n'est pas identifiable de façon fiable.
  annees = len({periodes.decomposer(p)[0] for p, _ in couples})
  if annees < 2:
    return {
      "disponible": False,
      "raison": (f"{annees} année(s) seulement : il en faut au moins deux "
            "pour estimer une saisonnalité"),
      "periodicite": per,
    }

  # Série alignée, pour l'affichage
  lignes = []
  residus = []
  for periode, valeur in couples:
    t = tend.get(periode)
    d = periodes.decomposer(periode)
    c = coefs.get(d[1], 0.0 if modele == "additif" else 1.0) if d else 0.0
    if modele == "multiplicatif":
      cvs_val = valeur / c if c else valeur
    else:
      cvs_val = valeur - c
    residu = None
    if t is not None:
      attendu = (t * c) if modele == "multiplicatif" else (t + c)
      residu = valeur - attendu
      residus.append(residu)
    lignes.append({
      "periode": periode,
      "libelle": periodes.libelle(periode, per),
      "observee": round(valeur, 4),
      "tendance": round(t, 4) if t is not None else None,
      "coef": round(c, 6) if isinstance(c, float) else c,
      "cvs": round(cvs_val, 4),
      "residu": round(residu, 4) if residu is not None else None,
    })

  # Qualité : part de la variance expliquée par la saisonnalité seule, puis
  # dispersion du résidu rapportée au niveau moyen.
  valeurs = [v for _, v in couples]
  niveau = _moyenne([abs(v) for v in valeurs]) or 1.0
  ecart_residu = _ecart_type(residus) if residus else None
  ecart_total = _ecart_type(valeurs)

  force_saison = None
  if ecart_total:
    ecarts_coefs = [abs(c) for c in coefs.values()]
    force_saison = _ecart_type(ecarts_coefs) / ecart_total

  return {
    "disponible": True,
    "modele": modele,
    "periodicite": per,
    "rangs": estimation["rangs"],
    "coefficients": coefficients_lisibles(coefs, modele, per),
    "lignes": lignes,
    "n_points": len(couples),
    "n_annees": annees,
    "amplitude_saisonniere": round(
      max(coefs.values()) - min(coefs.values()), 4
    ),
    "force_saisonniere": round(force_saison, 3) if force_saison else None,
    "ecart_residu": round(ecart_residu, 4) if ecart_residu else None,
    "residu_relatif": (round(ecart_residu / niveau, 4)
              if ecart_residu else None),
  }


def coefficients_lisibles(coefs, modele, periodicite):
  """Coefficients saisonniers prêts à afficher, par rang."""
  out = []
  for rang in sorted(coefs):
    if periodicite == "mensuelle":
      nom = periodes.LIBELLES_MOIS[rang - 1]
    elif periodicite == "trimestrielle":
      nom = f"T{rang}"
    elif periodicite == "semestrielle":
      nom = f"S{rang}"
    else:
      nom = str(rang)
    valeur = coefs[rang]
    if modele == "multiplicatif":
      out.append({
        "rang": rang,
        "nom": nom,
        "valeur": round(valeur, 4),
        "effet": round((valeur - 1) * 100, 2),
        "sens": "supérieur" if valeur > 1 else "inférieur",
      })
    else:
      out.append({
        "rang": rang,
        "nom": nom,
        "valeur": round(valeur, 4),
        "effet": round(valeur, 4),
        "sens": "supérieur" if valeur > 0 else "inférieur",
      })
  return out


def _amplitude_saisonniere(tranche):
  """Amplitude de la composante saisonnière, tendance retirée.

  Mesurer l'étendue brute de la tranche ne dit rien de la saisonnalité : elle
  est dominée par la pente de la tendance. On retire donc d'abord la tendance
  linéaire ajustée sur la tranche, puis on mesure l'étendue des résidus.
  """
  if len(tranche) < 4:
    return None
  xs = list(range(len(tranche)))
  ys = [v for _, v in tranche]
  n = len(ys)
  mx = sum(xs) / n
  my = sum(ys) / n
  denom = sum((x - mx) ** 2 for x in xs)
  if denom == 0:
    return None
  pente = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
  residus = [y - (my + pente * (x - mx)) for x, y in zip(xs, ys)]
  return max(residus) - min(residus)


def choisir_modele(serie, periodicite=None):
  """Choisit entre modèle additif et multiplicatif.

  Le raisonnement est direct :

  - modèle additif : l'écart saisonnier garde la même amplitude en valeur
   absolue, quelle que soit la croissance du niveau ;
  - modèle multiplicatif : l'écart saisonnier grandit avec le niveau, donc son
   amplitude absolue croît elle aussi.

  On compare l'amplitude saisonnière des deux moitiés de la série, tendance
  retirée. Une amplitude qui croît nettement désigne le multiplicatif. Le
  critère est simple et explicable devant un jury, ce qui vaut mieux qu'un
  test sophistiqué aux conclusions fragiles sur des séries courtes.
  """
  couples = _trier(serie)
  if len(couples) < 8:
    return "additif", "série trop courte pour trancher, additif retenu par défaut"

  per = periodicite or periodes.inferer([p for p, _ in couples])
  n_rangs = RANGS_PAR_AN.get(per, 1)
  if n_rangs <= 1:
    return "additif", "série annuelle, aucun modèle saisonnier"

  milieu = len(couples) // 2
  a1 = _amplitude_saisonniere(couples[:milieu])
  a2 = _amplitude_saisonniere(couples[milieu:])
  if not a1 or not a2 or a1 <= 0:
    return "additif", "amplitude saisonnière non mesurable, additif retenu"

  rapport = a2 / a1
  if rapport > 1.25:
    return "multiplicatif", (
      f"amplitude saisonnière croissante avec le niveau "
      f"(x{rapport:.2f} entre les deux moitiés)"
    )
  return "additif", (
    f"amplitude saisonnière stable (x{rapport:.2f} entre les deux moitiés)"
  )
