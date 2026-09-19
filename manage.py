#!/usr/bin/env python
"""Utilitaire de ligne de commande Django, Analyse conjoncturelle."""
import os
import sys


def main():
  os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conjoncture_project.settings")
  try:
    from django.core.management import execute_from_command_line
  except ImportError as exc:
    raise ImportError(
      "Django est introuvable. Activez votre environnement virtuel puis "
      "installez les dépendances : pip install -r requirements.txt"
    ) from exc
  execute_from_command_line(sys.argv)


if __name__ == "__main__":
  main()
