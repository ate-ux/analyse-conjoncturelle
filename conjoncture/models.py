"""Modèles de la plateforme « Analyse conjoncturelle »."""
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Utilisateur(AbstractUser):
  """Utilisateur à rôle : administrateur (max. 2) ou simple utilisateur.

  Les administrateurs accèdent aux données confidentielles ; les autres
  utilisateurs ne voient que les données publiques.
  """

  class Role(models.TextChoices):
    ADMIN = "admin", "Administrateur"
    UTILISATEUR = "utilisateur", "Utilisateur"

  role = models.CharField(
    max_length=20, choices=Role.choices, default=Role.UTILISATEUR,
    verbose_name="Rôle",
  )
  organisation = models.CharField(
    max_length=150, blank=True, verbose_name="Organisation",
  )
  fonction = models.CharField(
    max_length=150, blank=True, verbose_name="Fonction",
  )
  cree_le = models.DateTimeField(default=timezone.now, verbose_name="Créé le")

  class Meta:
    verbose_name = "Utilisateur"
    verbose_name_plural = "Utilisateurs"

  def __str__(self):
    return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

  @property
  def est_admin(self):
    return self.role == self.Role.ADMIN or self.is_superuser

  @property
  def nom_complet(self):
    return self.get_full_name() or self.username

  @property
  def initiales(self):
    prenom = (self.first_name or self.username or "?")[0]
    nom = (self.last_name or "")[:1]
    return (prenom + nom).upper()

  def clean(self):
    super().clean()
    if self.role == self.Role.ADMIN:
      qs = Utilisateur.objects.filter(role=self.Role.ADMIN)
      if self.pk:
        qs = qs.exclude(pk=self.pk)
      from django.conf import settings
      maximum = getattr(settings, "MAX_ADMINS", 2)
      if qs.count() >= maximum:
        raise ValidationError(
          f"Le nombre d'administrateurs est limité à {maximum}."
        )

  def save(self, *args, **kwargs):
    from django.conf import settings
    maximum = getattr(settings, "MAX_ADMINS", 2)
    if self.role == self.Role.ADMIN or self.is_superuser:
      qs = Utilisateur.objects.filter(
        models.Q(role=self.Role.ADMIN) | models.Q(is_superuser=True)
      )
      if self.pk:
        qs = qs.exclude(pk=self.pk)
      if qs.count() >= maximum:
        self.role = self.Role.UTILISATEUR
        self.is_superuser = False
        self.is_staff = False
    super().save(*args, **kwargs)


class Conversation(models.Model):
  """Fil de discussion entre un utilisateur et « Le Perpétuel »."""

  utilisateur = models.ForeignKey(
    Utilisateur, on_delete=models.CASCADE, related_name="conversations",
    verbose_name="Utilisateur",
  )
  titre = models.CharField(max_length=200, blank=True, verbose_name="Titre")
  cree_le = models.DateTimeField(auto_now_add=True, verbose_name="Créée le")
  maj_le = models.DateTimeField(auto_now=True, verbose_name="Mise à jour le")

  class Meta:
    ordering = ["-maj_le"]
    verbose_name = "Conversation"
    verbose_name_plural = "Conversations"

  def __str__(self):
    return self.titre or f"Conversation #{self.pk}"


class Message(models.Model):
  """Message échangé avec l'assistant."""

  class Role(models.TextChoices):
    UTILISATEUR = "utilisateur", "Utilisateur"
    ASSISTANT = "assistant", "Assistant"

  class Mode(models.TextChoices):
    EN_LIGNE = "en_ligne", "En ligne"
    HORS_LIGNE = "hors_ligne", "Hors ligne"

  conversation = models.ForeignKey(
    Conversation, on_delete=models.CASCADE, related_name="messages",
    verbose_name="Conversation",
  )
  role = models.CharField(max_length=20, choices=Role.choices, verbose_name="Rôle")
  mode = models.CharField(
    max_length=20, choices=Mode.choices, default=Mode.EN_LIGNE,
    verbose_name="Mode de réponse",
  )
  contenu = models.TextField(verbose_name="Contenu")
  sources = models.JSONField(default=list, blank=True, verbose_name="Sources")
  cree_le = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")

  class Meta:
    ordering = ["cree_le"]
    verbose_name = "Message"
    verbose_name_plural = "Messages"

  def __str__(self):
    return f"{self.get_role_display()}, {self.contenu[:50]}"


class Rapport(models.Model):
  """Rapport de conjoncture généré automatiquement en PDF."""

  class Type(models.TextChoices):
    SYNTHESE = "synthese", "Synthèse conjoncturelle"
    REGIONAL = "regional", "Profil régional"
    PAYS = "pays", "Profil pays CEMAC"
    STATISTIQUE = "statistique", "Note statistique"

  titre = models.CharField(max_length=250, verbose_name="Titre")
  type_rapport = models.CharField(
    max_length=20, choices=Type.choices, default=Type.SYNTHESE,
    verbose_name="Type de rapport",
  )
  cible = models.CharField(
    max_length=100, blank=True,
    verbose_name="Cible", help_text="Région ou pays concerné, si applicable.",
  )
  periode = models.CharField(
    max_length=60, blank=True, verbose_name="Période",
    help_text="Exemple : 2025 ou 2020-2025.",
  )
  genere_par = models.ForeignKey(
    Utilisateur, on_delete=models.SET_NULL, null=True,
    related_name="rapports", verbose_name="Généré par",
  )
  fichier = models.FileField(
    upload_to="rapports/%Y/%m/", blank=True, verbose_name="Fichier PDF",
  )
  donnees = models.JSONField(
    default=dict, blank=True, verbose_name="Données du rapport",
  )
  cree_le = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")

  class Meta:
    ordering = ["-cree_le"]
    verbose_name = "Rapport"
    verbose_name_plural = "Rapports"

  def __str__(self):
    return self.titre


class Journal(models.Model):
  """Trace des connexions et des actions sensibles."""

  utilisateur = models.ForeignKey(
    Utilisateur, on_delete=models.SET_NULL, null=True, blank=True,
    related_name="journaux", verbose_name="Utilisateur",
  )
  action = models.CharField(max_length=200, verbose_name="Action")
  detail = models.CharField(max_length=400, blank=True, verbose_name="Détail")
  adresse_ip = models.GenericIPAddressField(
    null=True, blank=True, verbose_name="Adresse IP",
  )
  cree_le = models.DateTimeField(auto_now_add=True, verbose_name="Date")

  class Meta:
    ordering = ["-cree_le"]
    verbose_name = "Entrée du journal"
    verbose_name_plural = "Journal"

  def __str__(self):
    return f"{self.cree_le:%d/%m/%Y %H:%M}, {self.action}"


# --- Catalogue de données génériques -----------------------------------------
class SerieDonnees(models.Model):
  """Description d'une série de données, quelle que soit son origine.

  Le modèle est volontairement générique : il accepte aussi bien une série
  annuelle du Cameroun qu'un indice mensuel régional importé d'un tableur.
  """

  class Periodicite(models.TextChoices):
    ANNUELLE = "annuelle", "Annuelle"
    SEMESTRIELLE = "semestrielle", "Semestrielle"
    TRIMESTRIELLE = "trimestrielle", "Trimestrielle"
    MENSUELLE = "mensuelle", "Mensuelle"

  class Nature(models.TextChoices):
    PUBLIQUE = "publique", "Publique"
    CONFIDENTIELLE = "confidentielle", "Confidentielle"

  code = models.SlugField(max_length=80, unique=True, verbose_name="Code")
  libelle = models.CharField(max_length=200, verbose_name="Libellé")
  unite = models.CharField(max_length=30, blank=True, verbose_name="Unité")
  periodicite = models.CharField(
    max_length=20, choices=Periodicite.choices,
    default=Periodicite.ANNUELLE, verbose_name="Périodicité",
  )
  nature = models.CharField(
    max_length=20, choices=Nature.choices, default=Nature.PUBLIQUE,
    verbose_name="Nature",
  )
  entite_type = models.CharField(
    max_length=20, blank=True, default="", verbose_name="Type d'entité",
    help_text="Pays, région, ville, secteur… Laissez vide si sans objet.",
  )
  source = models.CharField(max_length=200, blank=True, verbose_name="Source")
  commentaire = models.TextField(blank=True, verbose_name="Commentaire")
  cree_le = models.DateTimeField(auto_now_add=True, verbose_name="Créée le")

  class Meta:
    ordering = ["libelle"]
    verbose_name = "Série de données"
    verbose_name_plural = "Séries de données"

  def __str__(self):
    return self.libelle

  @property
  def nb_points(self):
    return self.points.count()


class PointDonnee(models.Model):
  """Une observation : une série, une entité, une période, une valeur."""

  serie = models.ForeignKey(
    SerieDonnees, on_delete=models.CASCADE, related_name="points",
    verbose_name="Série",
  )
  entite = models.CharField(
    max_length=120, blank=True, verbose_name="Entité",
    help_text="Pays, région ou ville concernée. Vide = ensemble.",
  )
  periode = models.CharField(
    max_length=20, verbose_name="Période",
    help_text="2024 (annuel), 2024-T1 (trimestriel), 2024-03 (mensuel).",
  )
  valeur = models.FloatField(verbose_name="Valeur")

  class Meta:
    ordering = ["serie", "periode"]
    unique_together = [("serie", "entite", "periode")]
    verbose_name = "Point de donnée"
    verbose_name_plural = "Points de données"

  def __str__(self):
    return f"{self.serie.code} · {self.entite or ', '} · {self.periode} = {self.valeur}"


class ImportDonnees(models.Model):
  """Trace d'un import de fichier : qui, quand, quoi, avec quel résultat."""

  class Statut(models.TextChoices):
    EN_ATTENTE = "en_attente", "En attente"
    VALIDE = "valide", "Validé"
    PARTIEL = "partiel", "Partiellement importé"
    REJETE = "rejete", "Rejeté"

  fichier = models.FileField(
    upload_to="imports/%Y/%m/", blank=True, verbose_name="Fichier source",
  )
  nom_fichier = models.CharField(max_length=255, verbose_name="Nom du fichier")
  serie = models.ForeignKey(
    SerieDonnees, on_delete=models.SET_NULL, null=True, blank=True,
    related_name="imports", verbose_name="Série cible",
  )
  importe_par = models.ForeignKey(
    Utilisateur, on_delete=models.SET_NULL, null=True,
    related_name="imports", verbose_name="Importé par",
  )
  statut = models.CharField(
    max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE,
    verbose_name="Statut",
  )
  lignes_lues = models.IntegerField(default=0, verbose_name="Lignes lues")
  lignes_importees = models.IntegerField(default=0, verbose_name="Lignes importées")
  lignes_rejetees = models.IntegerField(default=0, verbose_name="Lignes rejetées")
  erreurs = models.JSONField(default=list, blank=True, verbose_name="Erreurs")
  apercu = models.JSONField(default=dict, blank=True, verbose_name="Aperçu")
  cree_le = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")

  class Meta:
    ordering = ["-cree_le"]
    verbose_name = "Import de données"
    verbose_name_plural = "Imports de données"

  def __str__(self):
    return f"{self.nom_fichier}, {self.get_statut_display()}"
