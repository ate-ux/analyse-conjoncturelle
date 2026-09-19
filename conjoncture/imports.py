"""
Import de données depuis des fichiers CSV et Excel.

Le module accepte deux formes de tableurs, les plus courantes en pratique :

1. **Format long** (recommandé), une ligne par observation, avec des colonnes
  *période* et *valeur* (et, si besoin, *entité*) :

    | periode | entite | valeur |
    |---------|--------|--------|
    | 2024  |    | 3,52  |
    | 2024-T1 |    | 0,9  |

2. **Format large**, une ligne par entité, une colonne par période :

    | region    | 2019 | 2020 | 2021 |
    |---------------|-------|-------|-------|
    | Extrême-Nord | 4,2  | 4,3  | 4,4  |

La détection est automatique : on cherche d'abord les colonnes de période et de
valeur ; à défaut, on bascule sur le format large si les en-têtes de colonnes
ressemblent à des périodes.

Toutes les valeurs sont lues en mémoire, normalisées, puis validées avant la
moindre écriture en base. Un import partiel est possible : les lignes valides
entrent, les autres sont retournées avec leur motif de rejet.
"""
from __future__ import annotations

import csv
import io
import re

from . import periodes

# --- Utilitaires --------------------------------------------------------------
entetes_periode = {"periode", "period", "date", "annee", "année", "trimestre",
          "mois", "periode_debut", "year", "quarter", "month"}
entetes_valeur = {"valeur", "value", "donnee", "donnée", "montant", "indice",
         "taux", "nb", "nombre", "total"}
entetes_entite = {"entite", "entité", "entity", "pays", "region", "région",
         "ville", "secteur", "zone", "pays_region", "libelle_entite"}


def _normaliser_entete(txt):
  return re.sub(r"[^a-zà-ÿ0-9]+", "_", str(txt or "").strip().lower()).strip("_")


def _en_nombre(txt):
  """Convertit un texte en nombre, en tolérant les formats français."""
  if txt is None:
    return None
  if isinstance(txt, (int, float)):
    return float(txt)
  s = str(txt).strip()
  if not s:
    return None
  s = s.replace("\u00a0", "").replace(" ", "").replace("%", "")
  if "," in s and "." in s:
    s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
  else:
    s = s.replace(",", ".")
  try:
    return float(s)
  except ValueError:
    return None


def _ressemble_a_periode(txt):
  return periodes.decomposer(txt) is not None


def lire_fichier(fichier):
  """Lit un CSV ou Excel et retourne une liste de dictionnaires.

  Retourne ``(lignes, erreur)`` ; ``erreur`` est ``None`` en cas de succès.
  """
  nom = getattr(fichier, "name", "") or ""
  extension = nom.rsplit(".", 1)[-1].lower() if "." in nom else ""
  try:
    brut = fichier.read()
  except Exception as exc:
    return [], f"Lecture du fichier impossible : {exc}"

  if extension in ("xlsx", "xlsm", "xls"):
    try:
      import openpyxl
    except ImportError:
      return [], "Le support Excel nécessite openpyxl (pip install openpyxl)."
    try:
      classeur = openpyxl.load_workbook(io.BytesIO(brut), data_only=True)
      feuille = classeur.active
      lignes_brutes = [
        [c for c in ligne]
        for ligne in feuille.iter_rows(values_only=True)
      ]
    except Exception as exc:
      return [], f"Lecture du classeur Excel impossible : {exc}"
  elif extension in ("csv", "txt", "tsv", ""):
    texte = None
    for encodage in ("utf-8-sig", "utf-8", "latin-1"):
      try:
        texte = brut.decode(encodage)
        break
      except UnicodeDecodeError:
        continue
    if texte is None:
      return [], "Encodage du fichier non reconnu (attendu : UTF-8 ou Latin-1)."
    separateur = "\t" if extension == "tsv" else None
    if separateur is None:
      echantillon = texte[:4096]
      try:
        separateur = csv.Sniffer().sniff(echantillon, delimiters=",;\t|").delimiter
      except Exception:
        separateur = ";" if echantillon.count(";") > echantillon.count(",") else ","
    lignes_brutes = list(csv.reader(io.StringIO(texte), delimiter=separateur))
  else:
    return [], (f"Format « .{extension} » non pris en charge. "
          "Utilisez CSV, TSV ou Excel (.xlsx).")

  lignes_brutes = [l for l in lignes_brutes if any(str(c or "").strip() for c in l)]
  if len(lignes_brutes) < 2:
    return [], "Le fichier ne contient pas assez de lignes (en-tête + données)."

  entetes = [str(c or "").strip() for c in lignes_brutes[0]]
  lignes = []
  for brute in lignes_brutes[1:]:
    ligne = {}
    for i, entete in enumerate(entetes):
      ligne[entete] = brute[i] if i < len(brute) else None
    ligne["_entetes"] = entetes
    lignes.append(ligne)
  return lignes, None


def analyser(lignes):
  """Détecte le format et prépare les observations.

  Retourne ``(observations, format_detecte, periodicite, erreurs)``.
  """
  if not lignes:
    return [], "inconnu", "annuelle", ["Aucune ligne à analyser."]

  entetes = lignes[0].get("_entetes") or [k for k in lignes[0] if k != "_entetes"]
  normalisees = {e: _normaliser_entete(e) for e in entetes}

  col_periode = next((e for e, n in normalisees.items() if n in entetes_periode), None)
  col_valeur = next((e for e, n in normalisees.items() if n in entetes_valeur), None)
  col_entite = next((e for e, n in normalisees.items() if n in entetes_entite), None)

  if not col_periode and len(entetes) >= 2:
    # Repli : la première colonne texte est la période.
    for e in entetes:
      valeurs = [str(l.get(e) or "").strip() for l in lignes[:20]]
      if sum(1 for v in valeurs if _ressemble_a_periode(v)) >= max(1, len(valeurs) // 2):
        col_periode = e
        break
  if not col_valeur and col_periode:
    restantes = [e for e in entetes if e != col_periode and e != col_entite]
    if restantes:
      col_valeur = restantes[-1]

  # --- Format long ---
  if col_periode and col_valeur:
    observations, erreurs = [], []
    for i, ligne in enumerate(lignes, start=2):
      brut_periode = ligne.get(col_periode)
      d = periodes.decomposer(brut_periode)
      if not d:
        erreurs.append({"ligne": i, "motif": f"période illisible : {brut_periode!r}"})
        continue
      valeur = _en_nombre(ligne.get(col_valeur))
      if valeur is None:
        erreurs.append({"ligne": i, "motif": f"valeur non numérique : {ligne.get(col_valeur)!r}"})
        continue
      entite = str(ligne.get(col_entite) or "").strip() if col_entite else ""
      observations.append({
        "periode": periodes.formater(d[0], d[1], d[2]),
        "entite": entite,
        "valeur": round(valeur, 6),
      })
    periodicite = periodes.inferer([o["periode"] for o in observations])
    return observations, "long", periodicite, erreurs

  # --- Format large : une colonne par période ---
  colonnes_periodes = []
  for e in entetes:
    d = periodes.decomposer(e)
    if d and not _en_nombre(e) is None and str(e).strip()[:4].isdigit():
      colonnes_periodes.append((e, d))
  if colonnes_periodes:
    observations, erreurs = [], []
    for i, ligne in enumerate(lignes, start=2):
      entite = ""
      if col_entite:
        entite = str(ligne.get(col_entite) or "").strip()
      if not entite:
        # Première colonne non-période = entité.
        for e in entetes:
          if e not in [c[0] for c in colonnes_periodes]:
            entite = str(ligne.get(e) or "").strip()
            if entite:
              break
      if not entite:
        erreurs.append({"ligne": i, "motif": "aucune entité identifiée"})
        continue
      for colonne, d in colonnes_periodes:
        valeur = _en_nombre(ligne.get(colonne))
        if valeur is None:
          continue
        observations.append({
          "periode": periodes.formater(d[0], d[1], d[2]),
          "entite": entite,
          "valeur": round(valeur, 6),
        })
    periodicite = periodes.inferer([o["periode"] for o in observations])
    return observations, "large", periodicite, erreurs

  return [], "inconnu", "annuelle", [{
    "ligne": 0,
    "motif": ("Format non reconnu : aucune colonne de période ni de valeur "
         "identifiable. Attendu : une colonne « periode » et une colonne "
         "« valeur », ou une colonne d'entité suivie de colonnes d'années."),
  }]


def apercu(observations, erreurs, limite=12):
  """Résumé présentable avant validation."""
  entites = sorted({o["entite"] for o in observations if o["entite"]})
  periodes_distinctes = sorted({o["periode"] for o in observations},
                 key=periodes.cle_tri)
  valeurs = [o["valeur"] for o in observations]
  return {
    "nb_observations": len(observations),
    "nb_erreurs": len(erreurs),
    "entites": entites,
    "nb_entites": len(entites),
    "debut": periodes_distinctes[0] if periodes_distinctes else None,
    "fin": periodes_distinctes[-1] if periodes_distinctes else None,
    "min": round(min(valeurs), 4) if valeurs else None,
    "max": round(max(valeurs), 4) if valeurs else None,
    "echantillon": observations[:limite],
    "erreurs": erreurs[:limite],
  }
