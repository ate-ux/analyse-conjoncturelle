#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Script de construction exécuté par Render à chaque déploiement.
#  - installe les dépendances
#  - récupère les bibliothèques tierces (cartes, graphiques)
#  - rassemble les fichiers statiques
#  - applique les migrations
#  - crée un administrateur, seulement si la base est neuve
#
# L'ordre compte : les bibliothèques doivent être présentes AVANT
# collectstatic, sinon elles manqueraient du manifeste des fichiers statiques
# et l'application lèverait une erreur au premier affichage.
# ---------------------------------------------------------------------------
set -o errexit  # arrête le script à la première erreur
set -o pipefail

echo "==> 1/5 Installation des dépendances"
pip install --upgrade pip
pip install -r requirements.txt

echo "==> 2/5 Bibliothèques de cartes et de graphiques"
python recuperer_assets.py || echo "  Bibliothèques déjà en place."

echo "==> 3/5 Rassemblement des fichiers statiques"
python manage.py collectstatic --no-input

echo "==> 4/5 Migrations de base de données"
python manage.py migrate --no-input

echo "==> 5/5 Comptes administrateurs"
# On ne crée un administrateur que si les identifiants sont fournis.
# Sans identifiants, on ne touche à rien : surtout pas de comptes de
# démonstration aux mots de passe publics sur une application en ligne.
if [ -n "$ADMIN1_IDENTIFIANTS" ]; then
 # --si-absent : au premier déploiement le compte est créé, ensuite il est
 # laissé tel quel. Sans ce drapeau, chaque redéploiement réécraserait le mot
 # de passe avec la valeur de la variable d'environnement.
 python manage.py initialiser --admin1 "$ADMIN1_IDENTIFIANTS" --si-absent \
  || echo "  Administrateur déjà en place."
else
 echo "  ADMIN1_IDENTIFIANTS non défini, étape ignorée."
 echo "  Créez votre administrateur avec :"
 echo "   python manage.py initialiser --admin1 identifiant:motdepasse"
fi

echo "==> Construction terminée"
