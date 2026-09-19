"""
Gestion des périodicités, annuelle et infra-annuelle.

Une période est représentée par un texte normalisé :

- annuelle   : ``2024``
- trimestrielle : ``2024-T1`` … ``2024-T4``
- mensuelle   : ``2024-01`` … ``2024-12``
- semestrielle : ``2024-S1``, ``2024-S2``

Chaque période se décompose en une année et un rang dans l'année, ce qui permet
de trier, de tracer et de modéliser aussi bien une série annuelle qu'une série
mensuelle sans changer le reste du code.
"""
import re

PERIODICITES = [
  ("annuelle", "Annuelle"),
  ("semestrielle", "Semestrielle"),
  ("trimestrielle", "Trimestrielle"),
  ("mensuelle", "Mensuelle"),
]

RANGS_PAR_AN = {
  "annuelle": 1,
  "semestrielle": 2,
  "trimestrielle": 4,
  "mensuelle": 12,
}

LIBELLES_MOIS = [
  "janvier", "février", "mars", "avril", "mai", "juin",
  "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def decomposer(periode, periodicite=None):
  """Décompose une période en ``(annee, rang, periodicite)``.

  ``rang`` commence à 1. Pour une période annuelle, ``rang`` vaut 1.
  Retourne ``None`` si la période est illisible.
  """
  if periode is None:
    return None
  txt = str(periode).strip().upper().replace("/", "-").replace(" ", "")
  if not txt:
    return None

  def chiffres(texte):
    """Ne conserve que les chiffres d'un fragment."""
    return int(re.sub(r"\D", "", texte)) if re.search(r"\d", texte) else None

  # Trimestre : 2024T1, 2024-T1, 2024Q1, 2024-Q1
  for marqueur in ("T", "Q"):
    if marqueur in txt:
      gauche, _, droite = txt.partition(marqueur)
      annee, rang = chiffres(gauche), chiffres(droite)
      if annee is not None and rang is not None and 1 <= rang <= 4:
        return (annee, rang, "trimestrielle")
      # Un marqueur de trimestre suivi d'un rang hors bornes (2024-T9)
      # n'est pas une période mensuelle : on refuse plutôt que de
      # réinterpréter le rang comme un mois.
      return None

  # Semestre : 2024S1, 2024-S2
  if "S" in txt:
    gauche, _, droite = txt.partition("S")
    annee, rang = chiffres(gauche), chiffres(droite)
    if annee is not None and rang is not None and 1 <= rang <= 2:
      return (annee, rang, "semestrielle")
    return None

  # Mensuelle : 2024-03
  if "-" in txt:
    gauche, _, droite = txt.partition("-")
    annee, rang = chiffres(gauche), chiffres(droite)
    if annee is not None and rang is not None and 1 <= rang <= 12:
      return (annee, rang, "mensuelle")

  # Annuelle : 2024
  annee = chiffres(txt)
  if annee is not None and len(re.sub(r"\D", "", txt)) == 4:
    return (annee, 1, "annuelle")
  return None


def formater(annee, rang=1, periodicite="annuelle"):
  """Construit le texte normalisé d'une période."""
  annee = int(annee)
  if periodicite == "trimestrielle":
    return f"{annee}-T{int(rang)}"
  if periodicite == "semestrielle":
    return f"{annee}-S{int(rang)}"
  if periodicite == "mensuelle":
    return f"{annee}-{int(rang):02d}"
  return str(annee)


def libelle(periode, periodicite="annuelle"):
  """Libellé lisible d'une période, pour l'affichage."""
  d = decomposer(periode)
  if not d:
    return str(periode)
  annee, rang, per = d
  if per == "trimestrielle":
    return f"T{rang} {annee}"
  if per == "semestrielle":
    return f"S{rang} {annee}"
  if per == "mensuelle" and 1 <= rang <= 12:
    return f"{LIBELLES_MOIS[rang - 1]} {annee}"
  return str(annee)


def inferer(periodes):
  """Devine la périodicité d'une liste de périodes.

  On retient la périodicité la plus fine rencontrée : une série mêlant des
  points annuels et trimestriels est traitée comme trimestrielle.
  """
  ordre = ["annuelle", "semestrielle", "trimestrielle", "mensuelle"]
  trouvees = []
  for p in periodes:
    d = decomposer(p)
    if d:
      trouvees.append(d[2])
  if not trouvees:
    return "annuelle"
  return max(trouvees, key=lambda x: ordre.index(x))


def cle_tri(periode):
  """Clé de tri chronologique stable."""
  d = decomposer(periode)
  if not d:
    return (0, 0, 0)
  annee, rang, per = d
  rang_par_an = {"annuelle": 1, "semestrielle": 2, "trimestrielle": 4, "mensuelle": 12}
  return (annee, rang * 12 // rang_par_an.get(per, 1), 0)


def rang_absolu(periode):
  """Rang absolu d'une période, pour les régressions et les prévisions."""
  d = decomposer(periode)
  if not d:
    return None
  annee, rang, per = d
  n = RANGS_PAR_AN.get(per, 1)
  return annee + (rang - 1) / n


def toutes_periodes(debut, fin, periodicite="annuelle"):
  """Génère les périodes d'un intervalle, pas à pas."""
  n = RANGS_PAR_AN.get(periodicite, 1)
  liste = []
  for annee in range(int(debut), int(fin) + 1):
    for rang in range(1, n + 1):
      liste.append(formater(annee, rang, periodicite))
  return liste
