"""
Récupère les bibliothèques tierces utilisées par la plateforme.

Ces fichiers ne sont pas inclus dans l'archive légère pour en réduire le poids :
ils représentent à eux seuls la majeure partie des octets et ne sont pas du code
que j'ai écrit. Ce script les télécharge une fois, puis la plateforme fonctionne
sans aucun accès réseau, comme avec l'archive complète.

Il fait aussi deux nettoyages, indispensables au déploiement en production :

 · il retire les commentaires « sourceMappingURL » des fichiers JavaScript.
  Ces cartes sources ne servent qu'au débogage dans le navigateur ; leur
  absence fait échouer le rassemblement des fichiers statiques.
 · il télécharge les images de contrôle des cartes référencées par la feuille
  de style de Leaflet, sans quoi ce même rassemblement s'interrompt.

Usage :
  python recuperer_assets.py
  python recuperer_assets.py --forcer  # retélécharge tout

Les fichiers sont écrits dans static/vendor/.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
import urllib.request

RACINE = pathlib.Path(__file__).resolve().parent
VENDOR = "static/vendor"

TELECHARGEMENTS = [
  ("leaflet/leaflet.js", "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"),
  ("leaflet/leaflet.css", "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"),
  ("leaflet/images/marker-icon.png", "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png"),
  ("leaflet/images/marker-icon-2x.png", "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png"),
  ("leaflet/images/marker-shadow.png", "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png"),
  ("leaflet/images/layers.png", "https://unpkg.com/leaflet@1.9.4/dist/images/layers.png"),
  ("leaflet/images/layers-2x.png", "https://unpkg.com/leaflet@1.9.4/dist/images/layers-2x.png"),
  ("chart/chart.umd.js", "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"),
]

# Fichiers dont il faut retirer la référence à une carte source absente.
NETTOYAGE_SOURCEMAP = ["leaflet/leaflet.js", "chart/chart.umd.js"]

MOTIF_SOURCEMAP = re.compile(rb"\n?//# sourceMappingURL=\S+\s*$")


def telecharger(destination: pathlib.Path, url: str, forcer: bool) -> str:
  if destination.exists() and not forcer:
    return "déjà présent"
  destination.parent.mkdir(parents=True, exist_ok=True)
  try:
    with urllib.request.urlopen(url, timeout=90) as reponse:
      contenu = reponse.read()
  except Exception as exc:
    return f"ÉCHEC ({exc})"
  if not contenu:
    return "ÉCHEC (réponse vide)"
  destination.write_bytes(contenu)
  return f"téléchargé ({len(contenu):,} octets)".replace(",", " ")


def nettoyer_sourcemap(chemin: pathlib.Path) -> str:
  """Retire le commentaire sourceMappingURL en fin de fichier."""
  if not chemin.exists():
    return "absent"
  contenu = chemin.read_bytes()
  nettoye, nombre = MOTIF_SOURCEMAP.subn(b"", contenu)
  if nombre:
    chemin.write_bytes(nettoye)
    return f"référence sourceMap retirée ({nombre})"
  return "rien à retirer"


def main() -> int:
  analyseur = argparse.ArgumentParser(description=__doc__)
  analyseur.add_argument("--forcer", action="store_true",
              help="retélécharger même si les fichiers existent")
  options = analyseur.parse_args()

  echecs = 0
  print("Téléchargement des bibliothèques :")
  for relatif, url in TELECHARGEMENTS:
    destination = RACINE / VENDOR / relatif
    resultat = telecharger(destination, url, options.forcer)
    if resultat.startswith("ÉCHEC"):
      echecs += 1
    print(f" {relatif:38s} {resultat}")

  print("\nNettoyage des références aux cartes sources :")
  for relatif in NETTOYAGE_SOURCEMAP:
    resultat = nettoyer_sourcemap(RACINE / VENDOR / relatif)
    print(f" {relatif:38s} {resultat}")

  print()
  if echecs:
    print(f"{echecs} fichier(s) en échec. Vérifiez la connexion puis "
       "relancez le script.")
    return 1
  print("Bibliothèques en place et nettoyées. La plateforme fonctionne "
     "désormais sans accès réseau, et le rassemblement des fichiers "
     "statiques peut s'achever.")
  return 0


if __name__ == "__main__":
  sys.exit(main())
