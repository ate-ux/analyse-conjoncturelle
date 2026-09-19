"""Vues de la désaisonnalisation et de la prévision multivariée."""
from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from . import multivarie, periodes, saisonnalite
from .data import economie
from .models import SerieDonnees, Utilisateur


def _niveau(request):
    """Niveau d'accès : « admin » ou « public »."""
    if request.user.is_authenticated and getattr(request.user, "est_admin", False):
        return "admin"
    return "public"


def _catalogue(request):
    """Séries analysables : indicateurs nationaux puis séries importées."""
    catalogue = []
    for k, ind in economie.INDICATEURS_NATIONAUX.items():
        catalogue.append({
            "cle": f"nat:{k}",
            "libelle": ind["libelle"],
            "unite": ind["unite"],
            "periodicite": "annuelle",
            "groupe": "Indicateurs nationaux",
            "source": economie.SOURCES.get(ind["source"], {}).get("nom", ""),
        })
    series = SerieDonnees.objects.all()
    if _niveau(request) != "admin":
        series = series.exclude(nature=SerieDonnees.Nature.CONFIDENTIELLE)
    for s in series:
        catalogue.append({
            "cle": f"imp:{s.pk}",
            "libelle": s.libelle,
            "unite": s.unite,
            "periodicite": s.get_periodicite_display(),
            "groupe": "Séries importées",
            "source": s.source,
        })
    return catalogue


def _charger_serie(request, cle):
    """Retourne ``(serie, libelle, unite, source)`` pour une clé de catalogue."""
    if cle.startswith("nat:"):
        ind = economie.INDICATEURS_NATIONAUX.get(cle.split(":", 1)[1])
        if ind:
            return (ind["serie"], ind["libelle"], ind["unite"],
                    economie.SOURCES.get(ind["source"], {}).get("nom", ""))
    elif cle.startswith("imp:"):
        requete = SerieDonnees.objects.filter(pk=cle.split(":", 1)[1])
        if _niveau(request) != "admin":
            requete = requete.exclude(nature=SerieDonnees.Nature.CONFIDENTIELLE)
        s = requete.first()
        if s:
            serie = {p.periode: p.valeur for p in s.points.all()}
            return serie, s.libelle, s.unite, s.source
    return {}, "", "", ""


@login_required
def saisonnalite_vue(request):
    """Décompose une série infra-annuelle : tendance, saisonnalité, résidu."""
    catalogue = _catalogue(request)
    cle = request.GET.get("serie", "") or (catalogue[0]["cle"] if catalogue else "")
    modele = request.GET.get("modele", "")

    serie, libelle, unite, source = _charger_serie(request, cle)
    periodicite = periodes.inferer(list(serie)) if serie else "annuelle"

    modele_conseille, justification = ("additif", "série vide")
    decomposition = None
    if serie:
        modele_conseille, justification = saisonnalite.choisir_modele(serie)
        if modele not in ("additif", "multiplicatif"):
            modele = modele_conseille
        decomposition = saisonnalite.decomposer(serie, modele=modele or modele_conseille)

    # Graphique : série observée, série CVS et tendance sur le même axe.
    graphique = {"periode": [], "observee": [], "cvs": [], "tendance": []}
    if decomposition and decomposition.get("disponible"):
        for ligne in decomposition["lignes"]:
            graphique["periode"].append(ligne["libelle"])
            graphique["observee"].append(ligne["observee"])
            graphique["cvs"].append(ligne["cvs"])
            graphique["tendance"].append(ligne["tendance"])

    return render(request, "conjoncture/saisonnalite.html", {
        "page": "saisonnalite",
        "catalogue": catalogue,
        "cle": cle,
        "libelle": libelle,
        "unite": unite,
        "source": source,
        "periodicite": periodicite,
        "modele": modele or modele_conseille,
        "modele_conseille": modele_conseille,
        "justification": justification,
        "decomposition": decomposition,
        "graphique_json": json.dumps(graphique),
        "modes": [("additif", "Additif"), ("multiplicatif", "Multiplicatif")],
    })


@login_required
def multivarie_vue(request):
    """Ajuste une régression multiple et projette la cible."""
    catalogue = _catalogue(request)

    # Les séries annuelles se prêtent le mieux au modèle, faute de quoi
    # l'alignement des périodes communes devient trop court.
    candidates = [c for c in catalogue if c["periodicite"] in ("annuelle", "Annuelle")]
    if not candidates:
        candidates = catalogue

    cle_cible = request.GET.get("cible", "") or (candidates[0]["cle"] if candidates else "")
    choisies = request.GET.getlist("explicative")
    choix_utilisateur = bool(choisies)

    serie_cible, libelle, unite, source = _charger_serie(request, cle_cible)

    # Les indicateurs n'ont pas tous la même couverture : le PIB nominal existe
    # depuis 2019, la pauvreté seulement par enquêtes espacées. Prendre les
    # « trois premières » séries ferait tomber l'intersection des périodes sous
    # le minimum requis. On retient donc les variables dont le recouvrement avec
    # la cible dépasse le seuil du modèle.
    seuil = 8
    if not choisies:
        compatibles = []
        for c in candidates:
            if c["cle"] == cle_cible:
                continue
            serie, _, _, _ = _charger_serie(request, c["cle"])
            if serie and multivarie.periodes_communes(serie_cible, [(c["libelle"], serie)]) >= seuil:
                compatibles.append(c["cle"])
        choisies = compatibles[:3]
    choisies = [c for c in choisies if c != cle_cible][:5]

    explicatives = []
    for c in choisies:
        serie, nom, unite_expl, _ = _charger_serie(request, c)
        if serie:
            explicatives.append((f"{nom} ({unite_expl})" if unite_expl else nom, serie))

    resultat = None
    if serie_cible and explicatives:
        resultat = multivarie.ajuster(serie_cible, explicatives)

    return render(request, "conjoncture/multivarie.html", {
        "page": "multivarie",
        "catalogue": candidates,
        "cible": cle_cible,
        "choisies": choisies,
        "libelle": libelle,
        "unite": unite,
        "source": source,
        "n_explicatives": len(explicatives),
        "resultat": resultat,
        "synthese": multivarie.synthese(resultat) if resultat else "",
        "selection_par_defaut": not choix_utilisateur,
    })


@login_required
def multivarie_prevision(request):
    """Projette la cible à partir du modèle multivarié ajusté."""
    catalogue = _catalogue(request)
    candidates = [c for c in catalogue if c["periodicite"] in ("annuelle", "Annuelle")]
    if not candidates:
        candidates = catalogue

    cle_cible = request.GET.get("cible", "") or (candidates[0]["cle"] if candidates else "")
    choisies = request.GET.getlist("explicative")
    serie_cible, libelle, unite, source = _charger_serie(request, cle_cible)

    # Sans choix explicite, on reprend la même règle qu'à l'ajustement : des
    # variables dont le recouvrement avec la cible dépasse le seuil du modèle.
    if not choisies:
        for c in candidates:
            if c["cle"] == cle_cible:
                continue
            serie, _, _, _ = _charger_serie(request, c["cle"])
            if serie and multivarie.periodes_communes(serie_cible, [(c["libelle"], serie)]) >= 8:
                choisies.append(c["cle"])
        choisies = choisies[:3]
    choisies = [c for c in choisies if c != cle_cible][:5]

    try:
        horizon = max(1, min(10, int(request.GET.get("horizon", "3"))))
    except (TypeError, ValueError):
        horizon = 3

    explicatives = []
    for c in choisies:
        serie, nom, unite_expl, _ = _charger_serie(request, c)
        if serie:
            explicatives.append((f"{nom} ({unite_expl})" if unite_expl else nom, serie))

    resultat = None
    if serie_cible and explicatives:
        resultat = multivarie.prevoir(serie_cible, explicatives, horizon=horizon)

    periodes_triees = sorted(serie_cible, key=periodes.cle_tri)
    return render(request, "conjoncture/multivarie_prevision.html", {
        "page": "multivarie",
        "cible": cle_cible,
        "libelle": libelle,
        "unite": unite,
        "source": source,
        "horizon": horizon,
        "horizons": list(range(1, 11)),
        "n_explicatives": len(explicatives),
        "resultat": resultat,
        "synthese": multivarie.synthese(resultat) if resultat else "",
        "historique_json": json.dumps({
            "periodes": periodes_triees,
            "valeurs": [serie_cible[p] for p in periodes_triees],
        }),
        "projection_json": json.dumps(
            resultat["points"] if resultat and resultat.get("disponible") else []
        ),
    })
