"""
Service d'import en base : transforme les observations analysées en
``PointDonnee``, avec journal et rapport.

La séparation avec ``imports.py`` est volontaire : ``imports.py`` lit et
analyse (aucune écriture), ce module écrit. On peut donc montrer un aperçu
avant toute modification de la base.
"""
from __future__ import annotations

from django.db import transaction

from . import periodes
from .models import ImportDonnees, Journal, PointDonnee, SerieDonnees


def executer_import(*, observations, serie, utilisateur, nom_fichier,
                    remplacer=False, fichier=None, lignes_lues=0, erreurs=None,
                    apercu=None):
    """Écrit les observations dans la série indiquée.

    Retourne l'``ImportDonnees`` créé, avec son bilan.
    """
    erreurs = erreurs or []
    apercu = apercu or {}
    crees = 0
    maj = 0

    with transaction.atomic():
        if remplacer:
            PointDonnee.objects.filter(serie=serie).delete()

        for obs in observations:
            _, cree = PointDonnee.objects.update_or_create(
                serie=serie,
                entite=obs["entite"],
                periode=obs["periode"],
                defaults={"valeur": obs["valeur"]},
            )
            if cree:
                crees += 1
            else:
                maj += 1

        # La périodicité observée corrige celle de la série si elle en diffère.
        periodicite = periodes.inferer([o["periode"] for o in observations])
        if periodicite and serie.periodicite != periodicite:
            serie.periodicite = periodicite
            serie.save(update_fields=["periodicite"])

        if erreurs:
            statut = ImportDonnees.Statut.PARTIEL if observations else ImportDonnees.Statut.REJETE
        else:
            statut = ImportDonnees.Statut.VALIDE

        enregistrement = ImportDonnees.objects.create(
            fichier=fichier or "",
            nom_fichier=nom_fichier or "sans-nom",
            serie=serie,
            importe_par=utilisateur,
            statut=statut,
            lignes_lues=lignes_lues or (len(observations) + len(erreurs)),
            lignes_importees=crees + maj,
            lignes_rejetees=len(erreurs),
            erreurs=erreurs[:100],
            apercu={**apercu, "crees": crees, "mis_a_jour": maj},
        )

    Journal.objects.create(
        utilisateur=utilisateur,
        action="Import de données",
        detail=(f"{nom_fichier} → {serie.code} : {crees} créés, {maj} mis à jour, "
                f"{len(erreurs)} rejetés"),
    )
    return enregistrement


def serie_depuis_observations(observations, code, libelle, **extra):
    """Crée (ou récupère) la série décrite par les métadonnées fournies."""
    periodicite = periodes.inferer([o["periode"] for o in observations])
    serie, _ = SerieDonnees.objects.get_or_create(
        code=code,
        defaults={
            "libelle": libelle,
            "periodicite": periodicite,
            "unite": extra.get("unite", ""),
            "source": extra.get("source", ""),
            "entite_type": extra.get("entite_type", ""),
            "nature": extra.get("nature", SerieDonnees.Nature.PUBLIQUE),
        },
    )
    return serie


def exporter_serie(serie):
    """Retourne les points d'une série, triés chronologiquement."""
    points = list(serie.points.all())
    points.sort(key=lambda p: (p.entite or "", periodes.cle_tri(p.periode)))
    return points


def exporter_csv(series):
    """Produit un CSV (texte) contenant les points des séries fournies."""
    import csv
    import io

    tampon = io.StringIO()
    writer = csv.writer(tampon, delimiter=";", lineterminator="\n")
    writer.writerow(["serie", "libelle", "entite", "periode", "valeur", "unite",
                     "periodicite", "source"])
    for serie in series:
        for p in exporter_serie(serie):
            writer.writerow([
                serie.code, serie.libelle, p.entite, p.periode,
                f"{p.valeur}".replace(".", ","),
                serie.unite, serie.get_periodicite_display(), serie.source,
            ])
    return tampon.getvalue()
