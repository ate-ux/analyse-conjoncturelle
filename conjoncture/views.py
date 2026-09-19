"""Vues de la plateforme « Analyse conjoncturelle »."""
from __future__ import annotations

import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import assistant, imports, periodes, previsions, service_import, stats
from .data import economie
from .forms import (
  FormulaireAdministrateur,
  FormulaireConnexion,
  FormulaireInscription,
  FormulaireRapport,
)
from .forms_import import FormulaireImport
from .models import (
  Conversation,
  ImportDonnees,
  Journal,
  Message,
  Rapport,
  SerieDonnees,
  Utilisateur,
)


# --- Utilitaires -------------------------------------------------------------
def _ip(request):
  xff = request.META.get("HTTP_X_FORWARDED_FOR")
  if xff:
    return xff.split(",")[0].strip()
  return request.META.get("REMOTE_ADDR")


def _journaliser(request, action, detail=""):
  Journal.objects.create(
    utilisateur=request.user if request.user.is_authenticated else None,
    action=action, detail=detail, adresse_ip=_ip(request),
  )


def _niveau(request):
  """Niveau d'accès de l'utilisateur : admin ou public."""
  return "admin" if getattr(request.user, "est_admin", False) else "public"


# --- Authentification --------------------------------------------------------
class ConnexionView(LoginView):
  """Page de connexion, « Analyse conjoncturelle » en fond, design soigné."""

  template_name = "conjoncture/connexion.html"
  authentication_form = FormulaireConnexion
  redirect_authenticated_user = True

  def form_valid(self, form):
    reponse = super().form_valid(form)
    _journaliser(self.request, "Connexion", f"Rôle : {self.request.user.get_role_display()}")
    return reponse

  def form_invalid(self, form):
    _journaliser(self.request, "Échec de connexion",
           form.data.get("username", "")[:60])
    return super().form_invalid(form)

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx["totaux"] = economie.totaux_cemac("2025")
    ctx["apercu"] = [
      {"libelle": "Croissance PIB", "valeur": "3,2 %", "annee": "2025"},
      {"libelle": "Inflation", "valeur": "3,4 %", "annee": "2025"},
      {"libelle": "Pauvreté", "valeur": "37,7 %", "annee": "2022"},
      {"libelle": "Pays CEMAC", "valeur": "6", "annee": "2025"},
    ]
    return ctx


def inscription(request):
  """Création d'un compte utilisateur (accès public)."""
  if request.user.is_authenticated:
    return redirect("conjoncture:tableau_de_bord")
  if request.method == "POST":
    form = FormulaireInscription(request.POST)
    if form.is_valid():
      user = form.save()
      _journaliser(request, "Inscription", user.username)
      messages.success(
        request,
        "Votre compte est créé. Vous accédez aux données publiques ; "
        "un administrateur peut vous élever au rôle d'administrateur.",
      )
      return redirect("conjoncture:connexion")
  else:
    form = FormulaireInscription()
  return render(request, "conjoncture/inscription.html", {"form": form})


def deconnexion(request):
  if request.user.is_authenticated:
    _journaliser(request, "Déconnexion", request.user.username)
  logout(request)
  return redirect("conjoncture:connexion")


# --- Pages principales -------------------------------------------------------
def accueil(request):
  """Page d'accueil publique."""
  if request.user.is_authenticated:
    return redirect("conjoncture:tableau_de_bord")
  return render(request, "conjoncture/accueil.html", {
    "totaux": economie.totaux_cemac("2025"),
    "pays": economie.tableau_cemac("2025"),
  })


@login_required
def tableau_de_bord(request):
  """Tableau de bord, indicateurs clés, séries, comparaisons."""
  cles = ["pib_croissance", "inflation", "pib_usd", "pib_par_habitant",
      "chomage", "pauvrete"]
  cartes = []
  for cle in cles:
    ind = economie.INDICATEURS_NATIONAUX[cle]
    d = economie.derniere_valeur(cle)
    cartes.append({
      "cle": cle,
      "libelle": ind["libelle"],
      "unite": ind["unite"],
      "valeur": d["valeur"],
      "annee": d["annee"],
      "variation": economie.variation(cle),
      "sens": ind["sens"],
      "source": economie.SOURCES.get(ind["source"], {}).get("nom", ""),
      "serie": ind["serie"],
      "serie_json": json.dumps({str(a): v for a, v in sorted(ind["serie"].items())}),
      "commentaire": ind.get("commentaire", ""),
      "seuil": ind.get("seuil"),
      "seuil_libelle": ind.get("seuil_libelle"),
    })
  return render(request, "conjoncture/tableau_de_bord.html", {
    "page": "tableau_de_bord",
    "cartes": cartes,
    "regions": economie.tableau_regions(),
    "totaux": economie.totaux_cemac("2025"),
    "pays": economie.tableau_cemac("2025"),
    "complementaires": economie.INDICATEURS_COMPLEMENTAIRES,
    "annees_serie": sorted(economie.INDICATEURS_NATIONAUX["pib_croissance"]["serie"]),
  })


@login_required
def cartes(request):
  """Cartes interactives : régions du Cameroun et pays de la CEMAC."""
  return render(request, "conjoncture/cartes.html", {
    "page": "cartes",
    "regions": economie.tableau_regions(),
    "pays": economie.tableau_cemac("2025"),
    "totaux": economie.totaux_cemac("2025"),
  })


@login_required
def statistiques(request):
  """Module statistique : descriptif, tendances, prévisions, corrélations."""
  cle = request.GET.get("indicateur", "pib_croissance")
  if cle not in economie.INDICATEURS_NATIONAUX:
    cle = "pib_croissance"
  analyse = stats.analyse_indicateur(cle)
  return render(request, "conjoncture/statistiques.html", {
    "page": "statistiques",
    "analyse": analyse,
    "serie_json": json.dumps({str(a): v for a, v in sorted(analyse["serie"].items())}),
    "indicateurs": {
      k: v["libelle"] for k, v in economie.INDICATEURS_NATIONAUX.items()
    },
    "cle_active": cle,
    "regionale": stats.analyse_regionale(),
    "cemac": stats.analyse_cemac(),
    "correlations": stats.correlations_principales(),
  })


@login_required
def regions(request):
  """Profil détaillé d'une région (ou vue d'ensemble)."""
  code = request.GET.get("region")
  donnees = None
  if code and code in economie.REGIONS:
    r = economie.REGIONS[code]
    donnees = {
      "cle": code,
      "nom": r["nom_fr"],
      "chef_lieu": r["chef_lieu"],
      "population": r["population"],
      "superficie": r["superficie_km2"],
      "densite": round(r["population"] / r["superficie_km2"], 1),
      "pauvrete": r["pauvrete_2022"],
      "note": r.get("note", ""),
    }
  return render(request, "conjoncture/regions.html", {
    "page": "regions",
    "regions": economie.tableau_regions(),
    "selection": donnees,
    "region_analyse": stats.analyse_regionale(),
  })


# --- Assistant « Le Perpétuel » ---------------------------------------------
@login_required
def assistant_vue(request):
  """Interface conversationnelle de l'assistant."""
  conversations = Conversation.objects.filter(utilisateur=request.user)
  conv_id = request.GET.get("conversation")
  conversation = None
  if conv_id:
    conversation = conversations.filter(pk=conv_id).first()
  if conversation is None:
    conversation = conversations.first()
  msgs = conversation.messages.all() if conversation else []
  return render(request, "conjoncture/assistant.html", {
    "page": "assistant",
    "conversations": conversations[:20],
    "conversation": conversation,
    "messages_": msgs,
    "en_ligne": bool(settings.ASSISTANT_API_KEY),
    "notes_admin": (
      assistant.notes_confidentielles() if _niveau(request) == "admin" else []
    ),
  })


@login_required
@require_POST
def assistant_message(request):
  """Traite un message et renvoie la réponse de l'assistant (JSON)."""
  try:
    charge = json.loads(request.body.decode("utf-8"))
  except (ValueError, UnicodeDecodeError):
    charge = request.POST

  question = (charge.get("message") or "").strip()
  if not question:
    return JsonResponse({"erreur": "Message vide."}, status=400)

  conv_id = charge.get("conversation")
  conversation = None
  if conv_id:
    conversation = Conversation.objects.filter(
      pk=conv_id, utilisateur=request.user
    ).first()
  if conversation is None:
    conversation = Conversation.objects.create(
      utilisateur=request.user,
      titre=question[:80],
    )

  Message.objects.create(
    conversation=conversation, role=Message.Role.UTILISATEUR,
    contenu=question, mode=Message.Mode.EN_LIGNE,
  )
  historique = [
    {"role": m.role, "contenu": m.contenu}
    for m in conversation.messages.all()[:40]
  ]

  reponse = assistant.repondre(
    question,
    historique=historique,
    niveau=_niveau(request),
    forcer_hors_ligne=(charge.get("mode") == "hors_ligne"),
  )

  Message.objects.create(
    conversation=conversation,
    role=Message.Role.ASSISTANT,
    contenu=reponse["texte"],
    mode=(Message.Mode.EN_LIGNE if reponse["mode"] == "en_ligne"
       else Message.Mode.HORS_LIGNE),
    sources=reponse.get("sources_fiches", []),
  )
  conversation.save(update_fields=["maj_le"])

  return JsonResponse({
    "conversation": conversation.pk,
    "reponse": reponse["texte"],
    "mode": reponse["mode"],
    "avertissement": reponse.get("avertissement"),
    "sources": reponse.get("sources_fiches", []),
  })


@login_required
@require_POST
def assistant_nouvelle(request):
  """Crée une nouvelle conversation."""
  conversation = Conversation.objects.create(
    utilisateur=request.user, titre="Nouvelle conversation",
  )
  return JsonResponse({"conversation": conversation.pk})


# --- Rapports PDF ------------------------------------------------------------
@login_required
def rapports(request):
  """Liste et génération des rapports de conjoncture."""
  if request.method == "POST":
    form = FormulaireRapport(request.POST)
    if form.is_valid():
      from .rapports import generer_rapport

      try:
        rapport = generer_rapport(
          type_rapport=form.cleaned_data["type_rapport"],
          cible=form.cleaned_data.get("cible", ""),
          periode=form.cleaned_data.get("periode", ""),
          inclure_graphiques=form.cleaned_data.get("inclure_graphiques", True),
          inclure_statistiques=form.cleaned_data.get("inclure_statistiques", True),
          confidentiel=form.cleaned_data.get("confidentiel", False),
          utilisateur=request.user,
        )
      except Exception as exc: # pragma: no cover, message utilisateur
        messages.error(request, f"La génération a échoué : {exc}")
      else:
        _journaliser(request, "Rapport généré", rapport.titre)
        messages.success(
          request,
          "Le rapport est généré. Le fichier est disponible dans la liste "
          "ci-dessous.",
        )
        return redirect("conjoncture:rapports")
  else:
    form = FormulaireRapport()

  qs = Rapport.objects.select_related("genere_par")
  if _niveau(request) != "admin":
    qs = qs.exclude(donnees__confidentiel=True)
  return render(request, "conjoncture/rapports.html", {
    "page": "rapports",
    "form": form,
    "rapports": qs[:40],
  })


@login_required
def rapport_telecharger(request, pk):
  rapport = get_object_or_404(Rapport, pk=pk)
  if rapport.donnees.get("confidentiel") and _niveau(request) != "admin":
    raise PermissionDenied("Rapport réservé aux administrateurs.")
  if not rapport.fichier:
    raise Http404("Fichier indisponible.")
  _journaliser(request, "Téléchargement de rapport", rapport.titre)
  return FileResponse(
    rapport.fichier.open("rb"),
    as_attachment=True,
    filename=f"{rapport.titre.replace(' ', '_')}.pdf",
  )


# --- Aide & administration ---------------------------------------------------
@login_required
def methodologie(request):
  """Note méthodologique : sources, définitions, méthodes statistiques."""
  return render(request, "conjoncture/methodologie.html", {
    "page": "methodologie",
    "sources": economie.SOURCES,
    "indicateurs": economie.INDICATEURS_NATIONAUX,
    "complementaires": economie.INDICATEURS_COMPLEMENTAIRES,
  })


@login_required
def administration(request):
  """Console d'administration : utilisateurs, journal, notes confidentielles."""
  if _niveau(request) != "admin":
    raise PermissionDenied("Espace réservé aux administrateurs.")

  form = FormulaireAdministrateur(request.POST or None)
  if request.method == "POST":
    if "promouvoir" in request.POST and form.is_valid():
      cible = form.cleaned_data["utilisateur"]
      admins = Utilisateur.objects.filter(role=Utilisateur.Role.ADMIN).count()
      if admins >= settings.MAX_ADMINS:
        messages.error(
          request,
          f"Limite atteinte : {settings.MAX_ADMINS} administrateurs maximum.",
        )
      else:
        cible.role = Utilisateur.Role.ADMIN
        cible.save(update_fields=["role"])
        _journaliser(request, "Promotion administrateur", cible.username)
        messages.success(request, f"{cible.nom_complet} est désormais administrateur.")
        return redirect("conjoncture:administration")
    elif "retrograder" in request.POST:
      cible_id = request.POST.get("retrograder")
      if str(request.user.pk) == str(cible_id):
        messages.error(request, "Vous ne pouvez pas retirer votre propre rôle.")
      else:
        cible = Utilisateur.objects.filter(pk=cible_id).first()
        if cible:
          cible.role = Utilisateur.Role.UTILISATEUR
          cible.save(update_fields=["role"])
          _journaliser(request, "Rétrogradation", cible.username)
          messages.success(request, f"{cible.nom_complet} repasse utilisateur.")
      return redirect("conjoncture:administration")

  return render(request, "conjoncture/administration.html", {
    "page": "administration",
    "form": form,
    "utilisateurs": Utilisateur.objects.all().order_by("role", "username"),
    "admins": Utilisateur.objects.filter(role=Utilisateur.Role.ADMIN),
    "nb_admins": Utilisateur.objects.filter(role=Utilisateur.Role.ADMIN).count(),
    "max_admins": settings.MAX_ADMINS,
    "journal": Journal.objects.select_related("utilisateur")[:40],
    "rapports": Rapport.objects.all()[:15],
    "stats": {
      "utilisateurs": Utilisateur.objects.count(),
      "conversations": Conversation.objects.count(),
      "messages": Message.objects.count(),
      "rapports": Rapport.objects.count(),
    },
    "notes": assistant.notes_confidentielles(),
  })


# --- API données (pour les graphiques du navigateur) ------------------------
@login_required
def api_donnees(request):
  """Séries et tableaux au format JSON, consommés par les graphiques."""
  return JsonResponse({
    "indicateurs": {
      cle: {
        "libelle": ind["libelle"],
        "unite": ind["unite"],
        "source": economie.SOURCES.get(ind["source"], {}).get("nom", ""),
        "serie": {str(a): v for a, v in sorted(ind["serie"].items())},
      }
      for cle, ind in economie.INDICATEURS_NATIONAUX.items()
    },
    "regions": economie.tableau_regions(),
    "pays_cemac": economie.tableau_cemac("2025"),
    "totaux": economie.totaux_cemac("2025"),
  })


@login_required
def api_carte_regions(request):
  """Contours et indicateurs des régions du Cameroun."""
  from pathlib import Path
  chemin = Path(settings.BASE_DIR) / "static" / "data" / "cameroun_regions.geojson"
  geo = json.loads(chemin.read_text(encoding="utf-8"))
  par_nom = {r["cle"]: r for r in economie.tableau_regions()}
  for f in geo["features"]:
    nom = f["properties"].get("shapeName")
    info = par_nom.get(nom)
    f["properties"]["nom_fr"] = info["nom"] if info else nom
    if info:
      f["properties"]["population"] = info["population"]
      f["properties"]["pauvrete"] = info["pauvrete"]
      f["properties"]["densite"] = info["densite"]
      f["properties"]["chef_lieu"] = info["chef_lieu"]
  return JsonResponse(geo)


@login_required
def api_carte_pays(request):
  """Contours et indicateurs des pays de la CEMAC."""
  from pathlib import Path
  chemin = Path(settings.BASE_DIR) / "static" / "data" / "cemac_pays.geojson"
  geo = json.loads(chemin.read_text(encoding="utf-8"))
  par_iso = {p["iso"]: p for p in economie.tableau_cemac("2025")}
  for f in geo["features"]:
    iso = f["properties"].get("iso")
    info = par_iso.get(iso)
    if info:
      f["properties"].update({
        "nom_fr": info["nom"],
        "croissance": info["croissance"],
        "inflation": info["inflation"],
        "pib_mds": info["pib_mds"],
        "population": info["population"],
        "pib_hab": info["pib_hab"],
      })
  return JsonResponse(geo)


# --- Import et export de données (administrateurs) ---------------------------
def _donnees_import_requises(request):
  if _niveau(request) != "admin":
    raise PermissionDenied("L'import de données est réservé aux administrateurs.")


@login_required
def donnees(request):
  """Catalogue des séries importées, avec leur volumétrie."""
  series = SerieDonnees.objects.all().prefetch_related("points")
  if _niveau(request) != "admin":
    series = series.exclude(nature=SerieDonnees.Nature.CONFIDENTIELLE)
  lignes = []
  for s in series:
    points = list(s.points.all())
    periodes_serie = sorted({p.periode for p in points}, key=periodes.cle_tri)
    lignes.append({
      "serie": s,
      "nb_points": len(points),
      "debut": periodes_serie[0] if periodes_serie else None,
      "fin": periodes_serie[-1] if periodes_serie else None,
      "entites": sorted({p.entite for p in points if p.entite}),
    })
  return render(request, "conjoncture/donnees.html", {
    "page": "donnees",
    "lignes": lignes,
    "imports": ImportDonnees.objects.select_related("serie", "importe_par")[:25],
    "periodicites": periodes.PERIODICITES,
    "peut_importer": _niveau(request) == "admin",
  })


@login_required
@require_POST
def donnees_apercu(request):
  """Étape 1 de l'import : analyse le fichier et montre l'aperçu, sans écrire."""
  _donnees_import_requises(request)
  form = FormulaireImport(request.POST, request.FILES)
  if not form.is_valid():
    return render(request, "conjoncture/donnees_import.html", {
      "page": "donnees", "form": form, "etape": "depot",
    })
  fichier = form.cleaned_data["fichier"]
  lignes, erreur = imports.lire_fichier(fichier)
  if erreur:
    messages.error(request, erreur)
    return render(request, "conjoncture/donnees_import.html", {
      "page": "donnees", "form": form, "etape": "depot",
    })
  observations, format_detecte, periodicite, erreurs = imports.analyser(lignes)
  resume = imports.apercu(observations, erreurs)
  request.session["import_en_cours"] = {
    "observations": observations,
    "erreurs": erreurs,
    "nom_fichier": fichier.name,
    "format": format_detecte,
    "periodicite": periodicite,
    "lignes_lues": len(lignes),
    "meta": {
      "serie_existante": form.cleaned_data["serie_existante"].pk if form.cleaned_data.get("serie_existante") else None,
      "nouvelle_serie": form.cleaned_data.get("nouvelle_serie"),
      "code": form.cleaned_data.get("code", ""),
      "libelle": form.cleaned_data.get("libelle", ""),
      "unite": form.cleaned_data.get("unite", ""),
      "source": form.cleaned_data.get("source", ""),
      "entite_type": form.cleaned_data.get("entite_type", ""),
      "nature": form.cleaned_data.get("nature", "publique"),
      "remplacer": form.cleaned_data.get("remplacer", False),
    },
  }
  return render(request, "conjoncture/donnees_import.html", {
    "page": "donnees",
    "etape": "apercu",
    "resume": resume,
    "format": format_detecte,
    "periodicite": periodicite,
    "nom_fichier": fichier.name,
  })


@login_required
@require_POST
def donnees_confirmer(request):
  """Étape 2 de l'import : écrit réellement les observations validées."""
  _donnees_import_requises(request)
  paquet = request.session.get("import_en_cours")
  if not paquet:
    messages.error(request, "Aucun import en attente. Déposez à nouveau le fichier.")
    return redirect("conjoncture:donnees")

  observations = paquet["observations"]
  meta = paquet["meta"]
  if not observations:
    messages.error(request, "Aucune observation exploitable dans ce fichier.")
    return redirect("conjoncture:donnees")

  if meta.get("nouvelle_serie"):
    serie = service_import.serie_depuis_observations(
      observations, meta["code"], meta["libelle"],
      unite=meta.get("unite", ""), source=meta.get("source", ""),
      entite_type=meta.get("entite_type", ""), nature=meta.get("nature", "publique"),
    )
  else:
    serie = get_object_or_404(SerieDonnees, pk=meta["serie_existante"])

  enregistrement = service_import.executer_import(
    observations=observations, serie=serie, utilisateur=request.user,
    nom_fichier=paquet["nom_fichier"], remplacer=meta.get("remplacer", False),
    lignes_lues=paquet.get("lignes_lues", 0),
    erreurs=paquet.get("erreurs", []),
    apercu={"format": paquet.get("format"), "periodicite": paquet.get("periodicite")},
  )
  request.session.pop("import_en_cours", None)
  messages.success(
    request,
    f"Import terminé : {enregistrement.lignes_importees} point(s) dans « {serie.libelle} »"
    + (f", {enregistrement.lignes_rejetees} ligne(s) rejetée(s)."
      if enregistrement.lignes_rejetees else "."),
  )
  return redirect("conjoncture:donnees")


@login_required
def donnees_export(request):
  """Export CSV de tout le catalogue de données."""
  _donnees_import_requises(request)
  series = SerieDonnees.objects.all().prefetch_related("points")
  contenu = service_import.exporter_csv(series)
  if not contenu.strip():
    messages.error(request, "Aucune donnée à exporter pour l'instant.")
    return redirect("conjoncture:donnees")
  reponse = HttpResponse(contenu, content_type="text/csv; charset=utf-8")
  reponse["Content-Disposition"] = 'attachment; filename="donnees_conjoncture.csv"'
  _journaliser(request, "Export des données", f"{series.count()} série(s)")
  return reponse


@login_required
def donnees_modele(request):
  """Renvoie un modèle CSV vide, pour guider les utilisateurs."""
  _donnees_import_requises(request)
  contenu = (
    "periode;entite;valeur\r\n"
    "2023;Extrême-Nord;4,5\r\n"
    "2024;Extrême-Nord;4,4\r\n"
    "2024-T1;Cameroun;0,9\r\n"
    "2024-T2;Cameroun;1,4\r\n"
    "2024-01;Cameroun;1,6\r\n"
  )
  reponse = HttpResponse(contenu, content_type="text/csv; charset=utf-8")
  reponse["Content-Disposition"] = 'attachment; filename="modele_import.csv"'
  return reponse


# --- Prédictions comparées ----------------------------------------------------
@login_required
def previsions_vue(request):
  """Compare quatre modèles de prévision sur une série et projette l'horizon."""
  cle = request.GET.get("serie", "")
  horizon = request.GET.get("horizon", "3")
  try:
    horizon = max(1, min(12, int(horizon)))
  except (TypeError, ValueError):
    horizon = 3

  # Catalogue des séries analysables : indicateurs nationaux + séries importées.
  catalogue = []
  for k, ind in economie.INDICATEURS_NATIONAUX.items():
    catalogue.append({
      "cle": f"nat:{k}", "libelle": ind["libelle"],
      "unite": ind["unite"], "source": economie.SOURCES.get(ind["source"], {}).get("nom", ""),
      "periodicite": "annuelle", "groupe": "Indicateurs nationaux",
    })
  series_importees = SerieDonnees.objects.all()
  if _niveau(request) != "admin":
    series_importees = series_importees.exclude(
      nature=SerieDonnees.Nature.CONFIDENTIELLE)
  for s in series_importees:
    catalogue.append({
      "cle": f"imp:{s.pk}", "libelle": s.libelle, "unite": s.unite,
      "source": s.source, "periodicite": s.get_periodicite_display(),
      "groupe": "Séries importées",
    })

  if not cle and catalogue:
    cle = catalogue[0]["cle"]

  serie, libelle, unite, source = {}, "", "", ""
  if cle.startswith("nat:"):
    k = cle.split(":", 1)[1]
    ind = economie.INDICATEURS_NATIONAUX.get(k)
    if ind:
      serie, libelle, unite = ind["serie"], ind["libelle"], ind["unite"]
      source = economie.SOURCES.get(ind["source"], {}).get("nom", "")
  elif cle.startswith("imp:"):
    requete = SerieDonnees.objects.filter(pk=cle.split(":", 1)[1])
    if _niveau(request) != "admin":
      requete = requete.exclude(nature=SerieDonnees.Nature.CONFIDENTIELLE)
    s = requete.first()
    if s:
      libelle, unite, source = s.libelle, s.unite, s.source
      for p in s.points.select_related("serie"):
        # Une entité vide ou l'unique entité existante : série directe.
        serie[p.periode] = p.valeur

  comparaison = previsions.comparer_modeles(serie, horizon=horizon) if serie else None

  periodes_triees = sorted(serie, key=periodes.cle_tri)
  return render(request, "conjoncture/previsions.html", {
    "page": "previsions",
    "catalogue": catalogue,
    "cle": cle,
    "horizon": horizon,
    "horizons": list(range(1, 13)),
    "libelle": libelle,
    "unite": unite,
    "source": source,
    "comparaison": comparaison,
    "synthese": previsions.synthese(comparaison),
    "serie_json": json.dumps({
      "periodes": periodes_triees,
      "valeurs": [serie[x] for x in periodes_triees],
    }),
    "projection_json": json.dumps(
      comparaison["projection"]["points"] if comparaison and comparaison.get("projection") else []
    ),
  })
