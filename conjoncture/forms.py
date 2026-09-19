"""Formulaires de la plateforme."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Utilisateur


class FormulaireConnexion(AuthenticationForm):
  """Connexion par nom d'utilisateur et mot de passe, habillée par nos soins."""

  username = forms.CharField(
    label="Nom d'utilisateur",
    widget=forms.TextInput(attrs={
      "class": "champ", "placeholder": "votre identifiant",
      "autocomplete": "username", "autofocus": True,
    }),
  )
  password = forms.CharField(
    label="Mot de passe",
    widget=forms.PasswordInput(attrs={
      "class": "champ", "placeholder": "••••••••",
      "autocomplete": "current-password",
    }),
  )

  error_messages = {
    "invalid_login": "Identifiant ou mot de passe incorrect.",
    "inactive": "Ce compte est désactivé.",
  }


class FormulaireInscription(UserCreationForm):
  """Inscription d'un utilisateur (le rôle administrateur est restreint)."""

  prenom = forms.CharField(
    label="Prénom", max_length=150, required=False,
    widget=forms.TextInput(attrs={"class": "champ", "placeholder": "Prénom"}),
  )
  nom = forms.CharField(
    label="Nom", max_length=150, required=False,
    widget=forms.TextInput(attrs={"class": "champ", "placeholder": "Nom"}),
  )
  email = forms.EmailField(
    label="Adresse e-mail", required=False,
    widget=forms.EmailInput(attrs={"class": "champ", "placeholder": "vous@exemple.cm"}),
  )
  organisation = forms.CharField(
    label="Organisation", max_length=150, required=False,
    widget=forms.TextInput(attrs={"class": "champ", "placeholder": "ISSEA, DEUS Stat…"}),
  )

  class Meta:
    model = Utilisateur
    fields = ("username", "prenom", "nom", "email", "organisation")
    labels = {"username": "Nom d'utilisateur"}

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.fields["username"].widget.attrs.update({
      "class": "champ", "placeholder": "identifiant de connexion",
    })
    self.fields["password1"].widget.attrs.update({
      "class": "champ", "placeholder": "mot de passe",
    })
    self.fields["password2"].widget.attrs.update({
      "class": "champ", "placeholder": "confirmer le mot de passe",
    })
    self.fields["password1"].label = "Mot de passe"
    self.fields["password2"].label = "Confirmation"

  def save(self, commit=True):
    user = super().save(commit=False)
    user.first_name = self.cleaned_data.get("prenom", "")
    user.last_name = self.cleaned_data.get("nom", "")
    user.email = self.cleaned_data.get("email", "")
    user.organisation = self.cleaned_data.get("organisation", "")
    if commit:
      user.save()
    return user


class FormulaireRapport(forms.Form):
  """Paramètres de génération d'un rapport PDF."""

  TYPE_CHOIX = [
    ("synthese", "Synthèse conjoncturelle, Cameroun"),
    ("regional", "Profil régional, une région du Cameroun"),
    ("pays", "Profil pays, un pays de la CEMAC"),
    ("statistique", "Note statistique, tendances et corrélations"),
  ]

  type_rapport = forms.ChoiceField(
    label="Type de rapport", choices=TYPE_CHOIX,
    widget=forms.Select(attrs={"class": "champ"}),
  )
  cible = forms.ChoiceField(
  label="Cible (région ou pays)", required=False,
  choices=[],  # rempli dynamiquement dans __init__
  widget=forms.Select(attrs={"class": "champ"}),
)
  periode = forms.CharField(
    label="Période couverte", max_length=60, required=False,
    initial="2020-2025",
    widget=forms.TextInput(attrs={"class": "champ"}),
  )
  inclure_graphiques = forms.BooleanField(
    label="Inclure les graphiques", required=False, initial=True,
  )
  inclure_statistiques = forms.BooleanField(
    label="Inclure l'annexe statistique", required=False, initial=True,
  )
  confidentiel = forms.BooleanField(
    label="Marquer comme confidentiel (administrateurs uniquement)",
    required=False, initial=False,
  )
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    from .data import economie

    choix = [("", "— Aucune cible (pour synthèse et note statistique) —")]
    choix.append(("─── Régions du Cameroun ───", [
      (cle, r["nom_fr"]) for cle, r in economie.REGIONS.items()
    ]))
    choix.append(("─── Pays de la CEMAC ───", [
      (iso, info["nom_fr"]) for iso, info in economie.PAYS_CEMAC.items()
    ]))
    self.fields["cible"].choices = choix


class FormulaireAdministrateur(forms.Form):
  """Création ou promotion d'un administrateur (deux au maximum)."""

  utilisateur = forms.ModelChoiceField(
    label="Utilisateur à promouvoir",
    queryset=Utilisateur.objects.none(),
    widget=forms.Select(attrs={"class": "champ"}),
  )

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.fields["utilisateur"].queryset = Utilisateur.objects.filter(
      role=Utilisateur.Role.UTILISATEUR
    ).order_by("username")
