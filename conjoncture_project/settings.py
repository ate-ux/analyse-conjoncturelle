"""
Configuration Django, Plateforme « Analyse conjoncturelle ».

Cameroun / CEMAC : cartes, tableau de bord, module statistique,
assistant « Le Perpétuel » et génération automatique de rapports PDF.

La même configuration sert en développement et en production : tout ce qui
change d'un environnement à l'autre passe par des variables d'environnement.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Charge les variables d'environnement depuis .env (développement local).
# En production, ces variables sont fournies par la plateforme d'hébergement.
load_dotenv(BASE_DIR / ".env")


def _verite(nom, defaut="False"):
  """Interprète une variable d'environnement comme un booléen."""
  return os.environ.get(nom, defaut).strip().lower() in ("1", "true", "oui", "yes", "on")


# --- Réglages de base --------------------------------------------------------
SECRET_KEY = os.environ.get(
  "DJANGO_SECRET_KEY",
  "dev-seulement-changez-moi-en-production-analyse-conjoncturelle",
)
DEBUG = _verite("DJANGO_DEBUG", "True")

# En production, ALLOWED_HOSTS doit lister le domaine Render.
# La valeur « * » n'est tolérée que hors production : on l'écarte quand DEBUG
# est désactivé s'il n'y a rien d'autre à mettre.
_hotes = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
if not _hotes:
  _hotes = ["*"] if DEBUG else ["localhost", "127.0.0.1"]
ALLOWED_HOSTS = _hotes

# Render fournit automatiquement le domaine public de l'application.
_domaine_render = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if _domaine_render and _domaine_render not in ALLOWED_HOSTS:
  ALLOWED_HOSTS.append(_domaine_render)

# Origines de confiance pour le CSRF : indispensable derrière le proxy de Render.
CSRF_TRUSTED_ORIGINS = [
  o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]
if _domaine_render:
  for schema in ("https", "http"):
    origine = f"{schema}://{_domaine_render}"
    if origine not in CSRF_TRUSTED_ORIGINS:
      CSRF_TRUSTED_ORIGINS.append(origine)

INSTALLED_APPS = [
  "django.contrib.admin",
  "django.contrib.auth",
  "django.contrib.contenttypes",
  "django.contrib.sessions",
  "django.contrib.messages",
  "django.contrib.staticfiles",
  "django.contrib.humanize",
  "conjoncture",
]

MIDDLEWARE = [
  "django.middleware.security.SecurityMiddleware",
  # WhiteNoise sert les fichiers statiques depuis l'application elle-même :
  # sur l'offre gratuite de Render, il n'y a pas de serveur web séparé.
  "whitenoise.middleware.WhiteNoiseMiddleware",
  "django.contrib.sessions.middleware.SessionMiddleware",
  "django.middleware.locale.LocaleMiddleware",
  "django.middleware.common.CommonMiddleware",
  "django.middleware.csrf.CsrfViewMiddleware",
  "django.contrib.auth.middleware.AuthenticationMiddleware",
  "django.contrib.messages.middleware.MessageMiddleware",
  "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "conjoncture_project.urls"

TEMPLATES = [
  {
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {
      "context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "conjoncture.context_processors.assistant_etat",
      ],
    },
  },
]

WSGI_APPLICATION = "conjoncture_project.wsgi.application"

# --- Base de données ---------------------------------------------------------
# En production : PostgreSQL via DATABASE_URL (fourni par Render).
# En développement : SQLite, sans configuration.
_url_base = os.environ.get("DATABASE_URL", "").strip()

if _url_base:
  import dj_database_url

  DATABASES = {
    "default": dj_database_url.parse(
      _url_base,
      conn_max_age=600,     # connexions persistantes
      conn_health_checks=True,
      ssl_require=not DEBUG,
    )
  }
else:
  DATABASES = {
    "default": {
      "ENGINE": "django.db.backends.sqlite3",
      "NAME": BASE_DIR / "db.sqlite3",
    }
  }

AUTH_USER_MODEL = "conjoncture.Utilisateur"

AUTH_PASSWORD_VALIDATORS = [
  {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
  {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
  {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
  {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Douala"
USE_I18N = True
USE_TZ = True

# --- Fichiers statiques ------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise compresse et met en cache les fichiers statiques.
#
# WHITENOISE_MANIFEST_STRICT = False est indispensable ici : les bibliothèques
# tierces (Leaflet) référencent des fichiers annexes, cartes sources, polices, 
# que nous ne distribuons pas. En mode strict, collectstatic s'arrête sur la
# première référence manquante et l'application ne démarre pas du tout.
STORAGES = {
  "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
  "staticfiles": {
    "BACKEND": (
      "django.contrib.staticfiles.storage.StaticFilesStorage"
      if DEBUG
      else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    ),
  },
}
WHITENOISE_MANIFEST_STRICT = False
WHITENOISE_MAX_AGE = 31536000 # un an, grâce à l'empreinte dans le nom de fichier

# --- Fichiers déposés (imports de données, rapports PDF générés) -------------
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("DJANGO_MEDIA_ROOT", BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Authentification -------------------------------------------------------
LOGIN_URL = "conjoncture:connexion"
LOGIN_REDIRECT_URL = "conjoncture:tableau_de_bord"
LOGOUT_REDIRECT_URL = "conjoncture:connexion"

# Nombre maximal d'administrateurs autorisés sur la plateforme.
MAX_ADMINS = int(os.environ.get("MAX_ADMINS", "2"))

# --- Sécurité en production --------------------------------------------------
# Ces réglages ne s'activent qu'hors DEBUG : en local, aucun HTTPS n'existe.
if not DEBUG:
  SECURE_SSL_REDIRECT = _verite("DJANGO_SECURE_SSL_REDIRECT", "True")
  SESSION_COOKIE_SECURE = True
  CSRF_COOKIE_SECURE = True
  SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
  SECURE_HSTS_INCLUDE_SUBDOMAINS = True
  SECURE_HSTS_PRELOAD = True
  SECURE_CONTENT_TYPE_NOSNIFF = True
  SECURE_REFERRER_POLICY = "same-origin"
  X_FRAME_OPTIONS = "DENY"
  # Render place un proxy devant l'application : on lui fait confiance pour
  # l'en-tête qui indique le protocole d'origine.
  SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Journalisation ----------------------------------------------------------
# Les erreurs partent sur la sortie standard, où Render les collecte.
LOGGING = {
  "version": 1,
  "disable_existing_loggers": False,
  "handlers": {"console": {"class": "logging.StreamHandler"}},
  "root": {"handlers": ["console"], "level": "INFO"},
}

# --- Assistant « Le Perpétuel » ---------------------------------------------
# Fournisseur compatible OpenAI. Groq propose une offre gratuite :
# console.groq.com, collez la clé dans .env (GROQ_API_KEY=...)
ASSISTANT_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
ASSISTANT_BASE_URL = os.environ.get(
  "ASSISTANT_BASE_URL", "https://api.groq.com/openai/v1"
)
ASSISTANT_MODEL = os.environ.get("ASSISTANT_MODEL", "llama-3.3-70b-versatile")
ASSISTANT_TIMEOUT = int(os.environ.get("ASSISTANT_TIMEOUT", "30"))

# --- Rapports PDF -----------------------------------------------------------
RAPPORT_ORGANISATION = os.environ.get(
  "RAPPORT_ORGANISATION", "DEUS STAT, Analyse conjoncturelle"
)
