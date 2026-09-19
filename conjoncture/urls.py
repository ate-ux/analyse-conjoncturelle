"""Routage de l'application."""
from django.urls import path

from . import views, vues_analyses

app_name = "conjoncture"

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("connexion/", views.ConnexionView.as_view(), name="connexion"),
    path("inscription/", views.inscription, name="inscription"),
    path("deconnexion/", views.deconnexion, name="deconnexion"),
    path("tableau-de-bord/", views.tableau_de_bord, name="tableau_de_bord"),
    path("cartes/", views.cartes, name="cartes"),
    path("regions/", views.regions, name="regions"),
    path("statistiques/", views.statistiques, name="statistiques"),
    path("previsions/", views.previsions_vue, name="previsions"),
    path("saisonnalite/", vues_analyses.saisonnalite_vue, name="saisonnalite"),
    path("multivarie/", vues_analyses.multivarie_vue, name="multivarie"),
    path("multivarie/prevision/", vues_analyses.multivarie_prevision,
         name="multivarie_prevision"),
    path("assistant/", views.assistant_vue, name="assistant"),
    path("assistant/message/", views.assistant_message, name="assistant_message"),
    path("assistant/nouvelle/", views.assistant_nouvelle, name="assistant_nouvelle"),
    path("rapports/", views.rapports, name="rapports"),
    path("rapports/<int:pk>/telecharger/", views.rapport_telecharger, name="rapport_telecharger"),
    path("methodologie/", views.methodologie, name="methodologie"),
    path("donnees/", views.donnees, name="donnees"),
    path("donnees/apercu/", views.donnees_apercu, name="donnees_apercu"),
    path("donnees/confirmer/", views.donnees_confirmer, name="donnees_confirmer"),
    path("donnees/export/", views.donnees_export, name="donnees_export"),
    path("donnees/modele/", views.donnees_modele, name="donnees_modele"),
    path("administration/", views.administration, name="administration"),
    path("api/donnees/", views.api_donnees, name="api_donnees"),
    path("api/carte/regions/", views.api_carte_regions, name="api_carte_regions"),
    path("api/carte/pays/", views.api_carte_pays, name="api_carte_pays"),
]
