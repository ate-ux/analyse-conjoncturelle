"""Contextes partagés par tous les gabarits."""
from django.conf import settings

from .data import economie


def assistant_etat(request):
    """Expose l'état de l'assistant et les métadonnées du site."""
    return {
        "assistant_en_ligne": bool(getattr(settings, "ASSISTANT_API_KEY", "")),
        "assistant_nom": "Le Perpétuel",
        "site_nom": "Analyse conjoncturelle",
        "sources_meta": economie.SOURCES,
        "est_admin": bool(
            request.user.is_authenticated
            and getattr(request.user, "est_admin", False)
        ),
    }
