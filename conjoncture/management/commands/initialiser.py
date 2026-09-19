"""
Initialise la plateforme : crée les administrateurs (deux au maximum) et
quelques comptes de démonstration.

Usage :
  python manage.py initialiser --demo
  python manage.py initialiser --admin1 admin1:motdepasse --admin2 admin2:motdepasse
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from conjoncture.models import Utilisateur


DEMO_ADMIN = ("perpetuel", "Conjoncture2026!")
DEMO_ADMIN2 = ("deus", "DeusStat2026!")
DEMO_USERS = [
  ("analyste", "Awa", "Ngo Bell", "ISSEA, Data Science"),
  ("etudiant", "Paul", "Mbarga", "ISSEA, Analyse conjoncturelle"),
  ("invite", "Sara", "Tchoumi", "DEUS Stat"),
]


class Command(BaseCommand):
  help = "Crée les administrateurs et les comptes de démonstration."

  def add_arguments(self, parser):
    parser.add_argument("--demo", action="store_true",
              help="Crée aussi les comptes de démonstration.")
    parser.add_argument("--admin1", type=str, default="",
              help="Identifiant:motdepasse du premier administrateur.")
    parser.add_argument("--admin2", type=str, default="",
              help="Identifiant:motdepasse du second administrateur.")
    parser.add_argument("--si-absent", action="store_true", dest="si_absent",
              help="Ne crée le compte que s'il n'existe pas déjà ; "
                 "ne touche pas au mot de passe existant.")

  @transaction.atomic
  def handle(self, *args, **options):
    maximum = getattr(settings, "MAX_ADMINS", 2)
    crees = []

    paires = []
    if options["admin1"]:
      paires.append(options["admin1"])
    if options["admin2"]:
      paires.append(options["admin2"])
    if not paires:
      paires = [f"{DEMO_ADMIN[0]}:{DEMO_ADMIN[1]}",
           f"{DEMO_ADMIN2[0]}:{DEMO_ADMIN2[1]}"]

    for i, paire in enumerate(paires[:maximum]):
      if ":" not in paire:
        self.stderr.write(f"Format invalide : {paire} (attendu identifiant:motdepasse)")
        continue
      identifiant, motdepasse = paire.split(":", 1)

      # --si-absent : utilisé au déploiement. On ne veut surtout pas
      # réécraser le mot de passe à chaque redéploiement, sinon un
      # changement fait depuis l'application serait annulé sans prévenir.
      if options["si_absent"] and Utilisateur.objects.filter(
          username=identifiant).exists():
        self.stdout.write(
          f" · admin {identifiant} déjà présent, mot de passe inchangé"
        )
        continue

      user, cree = Utilisateur.objects.get_or_create(
        username=identifiant,
        defaults={
          "role": Utilisateur.Role.ADMIN,
          "is_staff": True,
          "first_name": "Administrateur",
          "last_name": str(i + 1),
        },
      )
      user.role = Utilisateur.Role.ADMIN
      user.is_staff = True
      user.set_password(motdepasse)
      user.save()
      crees.append(f"admin {identifiant} {'créé' if cree else 'mis à jour'}")

    if options["demo"]:
      for identifiant, prenom, nom, organisation in DEMO_USERS:
        user, cree = Utilisateur.objects.get_or_create(
          username=identifiant,
          defaults={
            "first_name": prenom, "last_name": nom,
            "organisation": organisation,
            "role": Utilisateur.Role.UTILISATEUR,
          },
        )
        user.set_password("Demo2026!")
        user.save()
        crees.append(f"utilisateur {identifiant}")

    self.stdout.write(self.style.SUCCESS(
      f"{len(crees)} compte(s) traité(s) :"
    ))
    for ligne in crees:
      self.stdout.write(f" · {ligne}")
    self.stdout.write(
      f"\nLimite d'administrateurs : {maximum}. "
      "Recevez la plateforme, changez les mots de passe."
    )
    if options["demo"] or not paires:
      self.stdout.write(
        "Démo, admins : perpetuel / Conjoncture2026!, "
        "deus / DeusStat2026! ; utilisateurs : Demo2026!"
      )
