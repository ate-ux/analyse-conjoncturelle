"""Formulaires d'import et d'export de données."""
from django import forms

from .models import SerieDonnees


class FormulaireImport(forms.Form):
  """Dépôt d'un fichier CSV ou Excel et description de la série cible."""

  fichier = forms.FileField(
    label="Fichier à importer",
    help_text="Formats acceptés : CSV, TSV, Excel (.xlsx).",
    widget=forms.ClearableFileInput(attrs={
      "class": "champ", "accept": ".csv,.tsv,.txt,.xlsx,.xlsm",
    }),
  )
  serie_existante = forms.ModelChoiceField(
    label="Ajouter à une série existante",
    queryset=SerieDonnees.objects.all().order_by("libelle"),
    required=False,
    widget=forms.Select(attrs={"class": "champ"}),
  )
  nouvelle_serie = forms.BooleanField(
    label="Créer une nouvelle série", required=False, initial=True,
  )
  code = forms.SlugField(
    label="Code de la série", max_length=80, required=False,
    widget=forms.TextInput(attrs={"class": "champ", "placeholder": "inflation_alimentaire"}),
  )
  libelle = forms.CharField(
    label="Libellé", max_length=200, required=False,
    widget=forms.TextInput(attrs={"class": "champ",
                   "placeholder": "Inflation alimentaire, Cameroun"}),
  )
  unite = forms.CharField(
    label="Unité", max_length=30, required=False,
    widget=forms.TextInput(attrs={"class": "champ", "placeholder": "%, Mds FCFA, indice…"}),
  )
  source = forms.CharField(
    label="Source", max_length=200, required=False,
    widget=forms.TextInput(attrs={"class": "champ", "placeholder": "INS, BEAC, enquête interne…"}),
  )
  entite_type = forms.CharField(
    label="Type d'entité", max_length=20, required=False,
    widget=forms.TextInput(attrs={"class": "champ", "placeholder": "pays, région, ville…"}),
  )
  nature = forms.ChoiceField(
    label="Nature", choices=SerieDonnees.Nature.choices,
    initial=SerieDonnees.Nature.PUBLIQUE, required=False,
    widget=forms.Select(attrs={"class": "champ"}),
  )
  remplacer = forms.BooleanField(
    label="Remplacer les points existants de cette série (sinon, mise à jour)",
    required=False, initial=False,
  )

  def clean(self):
    donnees = super().clean()
    creation = donnees.get("nouvelle_serie")
    existante = donnees.get("serie_existante")
    if creation:
      if not donnees.get("code"):
        self.add_error("code", "Un code est requis pour créer une série.")
      elif SerieDonnees.objects.filter(code=donnees["code"]).exists():
        self.add_error("code", "Ce code est déjà utilisé.")
      if not donnees.get("libelle"):
        self.add_error("libelle", "Un libellé est requis pour créer une série.")
    elif not existante:
      self.add_error(
        "serie_existante",
        "Sélectionnez une série existante, ou cochez « Créer une nouvelle série ».",
      )
    if not donnees.get("nature"):
      donnees["nature"] = SerieDonnees.Nature.PUBLIQUE
    return donnees
