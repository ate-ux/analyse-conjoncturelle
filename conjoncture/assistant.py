"""
« Le Perpétuel », assistant conversationnel de la plateforme.

Fonctionne selon deux modes :

* EN LIGNE, si une clé API compatible OpenAI est configurée (Groq par défaut),
 la question est envoyée au modèle avec le contexte factuel de la plateforme.
 Le cloisonnement public / confidentiel est appliqué en amont du prompt :
 un simple utilisateur ne reçoit jamais les données réservées aux admins.
* HORS LIGNE, sans clé, ou si l'appel échoue (réseau indisponible), l'assistant
 bascule automatiquement sur le moteur de règles local, adossé à la base de
 connaissances embarquée. La réponse reste utile et traçable, sans réseau.

Le module ne lève jamais d'exception vers la vue : toute erreur devient un
repli hors ligne, afin que l'application reste utilisable sans connexion.
"""
from __future__ import annotations

import json
import logging

import requests
from django.conf import settings

from .data import economie

logger = logging.getLogger(__name__)

# Données réservées aux administrateurs (jamais envoyées à un simple utilisateur).
FICHES_CONFIDENTIELLES = [
  {
    "id": "note_interne_dette",
    "titre": "Note interne, soutenabilité de la dette",
    "niveau": "confidentiel",
    "contenu": (
      "Note réservée à l'administration : le ratio du service de la dette "
      "rapporté aux recettes publiques dépasse le seuil critique du FMI, "
      "signalant un risque élevé de surendettement à moyen terme malgré une "
      "dette jugée soutenable. Le besoin de financement 2026 est attendu à "
      "3 104,2 Mds FCFA (+39 %). Recommandation interne : prioriser les "
      "financements concessionnels et surveiller l'exposition des banques "
      "au souverain (37 % des actifs)."
    ),
  },
  {
    "id": "note_interne_regions",
    "titre": "Note interne, régions sous tension",
    "niveau": "confidentiel",
    "contenu": (
      "Note réservée à l'administration : trois régions concentrent la "
      "pauvreté (Extrême-Nord 69,2 %, Nord-Ouest 66,8 %, Nord 61,1 %) et "
      "conjuguent faible densité administrative et pression sécuritaire. "
      "Toute allocation budgétaire non fléchée vers ces territoires "
      "reproduira l'écart régional observé entre 2014 et 2022."
    ),
  },
]

SYSTEME = (
  "Tu es « Le Perpétuel », l'assistant d'analyse conjoncturelle de la "
  "plateforme Cameroun / CEMAC. Tu réponds en français, de façon claire, "
  "rigoureuse et concise (150 mots maximum sauf demande explicite). "
  "Tu t'appuies exclusivement sur les données fournies dans le contexte ; "
  "si une donnée n'y figure pas, dis-le franchement au lieu d'inventer. "
  "Tu cites toujours la source et l'année d'un chiffre que tu avances. "
  "Tu n'inventes jamais de statistique."
)


def _appel_llm(question, historique, contexte, niveau):
  """Interroge le fournisseur LLM. Retourne (texte, erreur)."""
  cle = getattr(settings, "ASSISTANT_API_KEY", "")
  if not cle:
    return None, "aucune clé API configurée"

  url = settings.ASSISTANT_BASE_URL.rstrip("/") + "/chat/completions"
  messages = [{"role": "system", "content": SYSTEME}]
  messages.append({
    "role": "system",
    "content": "CONTEXTE FACTUEL DE LA PLATEFORME :\n\n" + contexte,
  })
  if niveau == "admin":
    messages.append({
      "role": "system",
      "content": (
        "L'utilisateur est administrateur : tu peux mobiliser les notes "
        "internes confidentielles ci-dessous, en précisant qu'elles sont "
        "réservées à l'administration.\n\n"
        + "\n\n".join(f["contenu"] for f in FICHES_CONFIDENTIELLES)
      ),
    })
  else:
    messages.append({
      "role": "system",
      "content": (
        "L'utilisateur est un simple utilisateur : ne divulgue AUCUNE "
        "donnée confidentielle, note interne ou information réservée à "
        "l'administration. Reste strictement sur les données publiques."
      ),
    })
  for m in historique[-8:]:
    messages.append({
      "role": "user" if m["role"] == "utilisateur" else "assistant",
      "content": m["contenu"],
    })
  messages.append({"role": "user", "content": question})

  try:
    r = requests.post(
      url,
      headers={
        "Authorization": f"Bearer {cle}",
        "Content-Type": "application/json",
      },
      json={
        "model": settings.ASSISTANT_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 900,
      },
      timeout=getattr(settings, "ASSISTANT_TIMEOUT", 30),
    )
    if r.status_code != 200:
      return None, f"réponse HTTP {r.status_code}"
    data = r.json()
    texte = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    if not texte or not texte.strip():
      return None, "réponse vide du modèle"
    return texte.strip(), None
  except requests.Timeout:
    return None, "délai d'attente dépassé"
  except Exception as exc: # réseau, DNS, JSON…
    logger.warning("Assistant en ligne indisponible : %s", exc)
    return None, str(exc)


def repondre(question, historique=None, niveau="public", forcer_hors_ligne=False):
  """Point d'entrée unique de l'assistant.

  Retourne un dictionnaire : {texte, mode, sources_fiches, avertissement}.
  """
  historique = historique or []
  question = (question or "").strip()

  if not question:
    return {
      "texte": "Posez-moi une question sur la conjoncture du Cameroun "
           "ou de la zone CEMAC.",
      "mode": "en_ligne" if not forcer_hors_ligne else "hors_ligne",
      "sources_fiches": [],
      "avertissement": None,
    }

  if not forcer_hors_ligne:
    contexte = economie.contexte_donnees()
    texte, erreur = _appel_llm(question, historique, contexte, niveau)
    if texte:
      return {
        "texte": texte,
        "mode": "en_ligne",
        "sources_fiches": [],
        "avertissement": None,
      }
    # Repli : le mode hors ligne prend le relais, l'utilisateur est informé.
    rep = economie.reponse_hors_ligne(question, niveau)
    rep["avertissement"] = (
      "Réponse produite hors ligne : le service en ligne est "
      f"indisponible ({erreur})."
    )
    if niveau == "admin":
      rep["sources_fiches"] += [
        {"id": f["id"], "titre": f["titre"]}
        for f in FICHES_CONFIDENTIELLES
        if any(
          mot in question.lower()
          for mot in f["titre"].lower().split()
        )
      ]
    return rep

  rep = economie.reponse_hors_ligne(question, niveau)
  rep["avertissement"] = None
  return rep


def notes_confidentielles(mots_cles=""):
  """Notes internes visibles par les administrateurs uniquement."""
  q = (mots_cles or "").lower()
  if not q:
    return FICHES_CONFIDENTIELLES
  return [
    f for f in FICHES_CONFIDENTIELLES
    if any(mot in q for mot in f["titre"].lower().split())
  ]
