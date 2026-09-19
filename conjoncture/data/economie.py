"""
Base de données conjoncturelle de la plateforme.

Toutes les séries sont des données publiques, sourcées et datées :
- Banque mondiale (API ouverte, World Development Indicators), séries longues ;
- INS Cameroun (ECAM 5, RGPH), pauvreté et population ;
- BEAC / CEMAC, convergence et politique monétaire ;
- DG Trésor (France), conjoncture et finances publiques du Cameroun.

Chaque indicateur porte sa source, son unité et l'année de dernière mise à
jour, afin que le jury et les utilisateurs puissent tracer chaque chiffre.
"""

# --- Métadonnées des sources -------------------------------------------------
SOURCES = {
  "bm": {
    "nom": "Banque mondiale, World Development Indicators",
    "url": "https://donnees.banquemondiale.org/pays/cameroun",
  },
  "ins": {
    "nom": "INS Cameroun, ECAM 5 (2022) & RGPH",
    "url": "https://ins-cameroun.cm/",
  },
  "beac": {
    "nom": "BEAC / CEMAC, Surveillance multilatérale",
    "url": "https://www.beac.int/",
  },
  "tresor": {
    "nom": "Direction générale du Trésor (France)",
    "url": "https://www.tresor.economie.gouv.fr/Pays/CM/indicateurs-et-conjoncture",
  },
}

# --- Indicateurs nationaux du Cameroun --------------------------------------
# Série annuelle : {année: valeur}. Unité et source déclarées par indicateur.
INDICATEURS_NATIONAUX = {
  "pib_croissance": {
    "libelle": "Croissance du PIB réel",
    "unite": "%",
    "source": "bm",
    "sens": "hausse",
    "serie": {
      2015: 5.6, 2016: 4.5, 2017: 3.5, 2018: 4.2, 2019: 4.6,
      2020: 0.3, 2021: 3.6, 2022: 3.6, 2023: 3.35, 2024: 3.52, 2025: 3.20,
    },
    "commentaire": "La croissance reste portée par le secteur non pétrolier "
            "(services, agriculture, BTP), alors que la production "
            "pétrolière recule.",
  },
  "inflation": {
    "libelle": "Taux d'inflation (prix à la consommation)",
    "unite": "%",
    "source": "bm",
    "sens": "baisse",
    "seuil": 3.0,
    "seuil_libelle": "Critère de convergence CEMAC (3 %)",
    "serie": {
      2015: 2.7, 2016: 0.9, 2017: 0.6, 2018: 1.1, 2019: 2.5,
      2020: 2.4, 2021: 2.3, 2022: 4.9, 2023: 7.38, 2024: 4.53, 2025: 3.40,
    },
    "commentaire": "Le pic de 2023 (7,4 %) est résorbé ; le taux revient sous "
            "la barre des 4 % en 2025 sous l'effet de la politique "
            "monétaire restrictive de la BEAC.",
  },
  "pib_usd": {
    "libelle": "PIB nominal",
    "unite": "Mds USD",
    "source": "bm",
    "sens": "hausse",
    "serie": {
      2019: 38.8, 2020: 40.7, 2021: 45.0, 2022: 44.3,
      2023: 49.3, 2024: 53.3, 2025: 58.9,
    },
    "commentaire": "Le Cameroun pèse plus de 44 % du PIB de la CEMAC.",
  },
  "pib_par_habitant": {
    "libelle": "PIB par habitant",
    "unite": "USD",
    "source": "bm",
    "sens": "hausse",
    "serie": {
      2019: 1524, 2020: 1540, 2021: 1652, 2022: 1594,
      2023: 1732, 2024: 1830, 2025: 1972,
    },
    "commentaire": "Progression nominale, à relativiser par la démographie "
            "(près de 2,6 % de croissance annuelle de la population).",
  },
  "population": {
    "libelle": "Population totale",
    "unite": "millions",
    "source": "bm",
    "sens": "hausse",
    "serie": {
      2019: 25.9, 2020: 26.5, 2021: 27.2, 2022: 27.9,
      2023: 28.6, 2024: 29.1, 2025: 29.9,
    },
    "commentaire": "Population estimée à environ 30,3 millions d'habitants "
            "début 2026 (projections BUCREP).",
  },
  "chomage": {
    "libelle": "Taux de chômage (BIT)",
    "unite": "%",
    "source": "bm",
    "sens": "baisse",
    "serie": {
      2019: 3.5, 2020: 3.8, 2021: 3.9, 2022: 3.8,
      2023: 3.61, 2024: 3.60, 2025: 3.60,
    },
    "commentaire": "Le taux BIT masque le sous-emploi et l'informalité : "
            "la part des salariés reste minoritaire dans l'emploi total.",
  },
  "pauvrete": {
    "libelle": "Incidence de la pauvreté monétaire",
    "unite": "%",
    "source": "ins",
    "sens": "baisse",
    "serie": {2001: 40.2, 2007: 39.9, 2014: 37.5, 2021: 38.6, 2022: 37.7},
    "commentaire": "En 2022, 10,1 millions de personnes vivent sous le seuil "
            "de 813 FCFA par jour (296 691 FCFA par an). La nouvelle "
            "série ECAM 5 n'est pas comparable aux précédentes.",
  },
  "gini": {
    "libelle": "Indice de Gini",
    "unite": "points",
    "source": "ins",
    "sens": "baisse",
    "serie": {2001: 40.8, 2007: 42.3, 2014: 40.1, 2022: 40.1},
    "commentaire": "Les inégalités sont stables ; le rapport de consommation "
            "entre le quintile le plus riche et le plus pauvre est de 7,8.",
  },
}

# --- Six pays de la CEMAC ----------------------------------------------------
# Croissance du PIB réel (%), Banque mondiale, 2025 = estimation.
CEMAC_CROISSANCE = {
  "CMR": {"2019": 4.6, "2020": 0.3, "2021": 3.6, "2022": 3.6, "2023": 3.35, "2024": 3.52, "2025": 3.20},
  "GAB": {"2019": 3.9, "2020": -1.9, "2021": 1.9, "2022": 3.0, "2023": 2.44, "2024": 3.39, "2025": 2.47},
  "COG": {"2019": 0.0, "2020": -6.2, "2021": 0.6, "2022": 1.5, "2023": 1.91, "2024": 2.10, "2025": 3.08},
  "TCD": {"2019": 3.5, "2020": -1.6, "2021": -1.1, "2022": 2.2, "2023": 4.00, "2024": 4.95, "2025": 5.59},
  "CAF": {"2019": 3.0, "2020": 0.9, "2021": 0.9, "2022": 0.5, "2023": 0.70, "2024": 1.50, "2025": 4.50},
  "GNQ": {"2019": -4.9, "2020": -4.8, "2021": 0.9, "2022": 3.1, "2023": -7.43, "2024": 0.40, "2025": -5.85},
}

# Inflation (%), Banque mondiale.
CEMAC_INFLATION = {
  "CMR": {"2019": 2.5, "2020": 2.4, "2021": 2.3, "2022": 4.9, "2023": 7.38, "2024": 4.53, "2025": 3.40},
  "GAB": {"2019": 2.0, "2020": 1.7, "2021": 4.1, "2022": 4.3, "2023": 3.63, "2024": 1.17, "2025": 1.77},
  "COG": {"2019": 2.2, "2020": 1.4, "2021": 2.0, "2022": 3.0, "2023": 4.30, "2024": 3.09, "2025": 2.40},
  "TCD": {"2019": -1.0, "2020": 4.5, "2021": 1.6, "2022": 5.3, "2023": 10.84, "2024": 8.90, "2025": -3.91},
  "CAF": {"2019": 2.7, "2020": 0.9, "2021": 1.5, "2022": 5.6, "2023": 2.98, "2024": 1.48, "2025": 1.00},
  "GNQ": {"2019": 0.7, "2020": 4.8, "2021": -0.1, "2022": 4.79, "2023": 2.86, "2024": 2.92, "2025": 2.60},
}

# PIB nominal (Mds USD), Banque mondiale.
CEMAC_PIB = {
  "CMR": {"2023": 49.3, "2024": 53.3, "2025": 58.9},
  "GAB": {"2023": 20.5, "2024": 20.9, "2025": 21.4},
  "COG": {"2023": 15.3, "2024": 15.7, "2025": 16.3},
  "TCD": {"2023": 17.6, "2024": 19.9, "2025": 21.5},
  "CAF": {"2023": 2.6, "2024": 2.8, "2025": 3.1},
  "GNQ": {"2023": 12.7, "2024": 13.3, "2025": 12.8},
}

# Population (millions), Banque mondiale.
CEMAC_POPULATION = {
  "CMR": {"2024": 29.1, "2025": 29.9},
  "GAB": {"2024": 2.5, "2025": 2.6},
  "COG": {"2024": 6.3, "2025": 6.5},
  "TCD": {"2024": 20.3, "2025": 21.0},
  "CAF": {"2024": 5.3, "2025": 5.5},
  "GNQ": {"2024": 1.9, "2025": 1.9},
}

# PIB par habitant (USD), Banque mondiale.
CEMAC_PIB_HAB = {
  "CMR": {"2024": 1830, "2025": 1972},
  "GAB": {"2024": 8230, "2025": 8263},
  "COG": {"2024": 2482, "2025": 2515},
  "TCD": {"2024": 981, "2025": 1022},
  "CAF": {"2024": 516, "2025": 556},
  "GNQ": {"2024": 7004, "2025": 6615},
}

PAYS_CEMAC = {
  "CMR": {"nom_fr": "Cameroun", "capital": "Yaoundé", "geo": "Cameroun"},
  "GAB": {"nom_fr": "Gabon", "capital": "Libreville", "geo": "Gabon"},
  "COG": {"nom_fr": "Congo", "capital": "Brazzaville", "geo": "Congo"},
  "TCD": {"nom_fr": "Tchad", "capital": "N'Djaména", "geo": "Chad"},
  "CAF": {"nom_fr": "République Centrafricaine", "capital": "Bangui",
      "geo": "Central African Rep."},
  "GNQ": {"nom_fr": "Guinée équatoriale", "capital": "Malabo",
      "geo": "Eq. Guinea"},
}

# --- Régions du Cameroun -----------------------------------------------------
# Clé = nom du contour géographique (geoBoundaries ADM1).
REGIONS = {
  "Adamaoua": {
    "nom_fr": "Adamaoua", "chef_lieu": "Ngaoundéré",
    "population": 884289, "superficie_km2": 63701,
    "pauvrete_2022": 45.1,
  },
  "Centre": {
    "nom_fr": "Centre", "chef_lieu": "Yaoundé",
    "population": 3098044, "superficie_km2": 68953,
    "pauvrete_2022": 19.1, "note": "Hors ville de Yaoundé (10,8 %).",
  },
  "East": {
    "nom_fr": "Est", "chef_lieu": "Bertoua",
    "population": 771755, "superficie_km2": 109002,
    "pauvrete_2022": 41.5,
  },
  "Far North": {
    "nom_fr": "Extrême-Nord", "chef_lieu": "Maroua",
    "population": 3111792, "superficie_km2": 34263,
    "pauvrete_2022": 69.2,
  },
  "Littoral": {
    "nom_fr": "Littoral", "chef_lieu": "Douala",
    "population": 2510283, "superficie_km2": 20248,
    "pauvrete_2022": 23.8, "note": "Hors ville de Douala (8,3 %).",
  },
  "North": {
    "nom_fr": "Nord", "chef_lieu": "Garoua",
    "population": 1687859, "superficie_km2": 66000,
    "pauvrete_2022": 61.1,
  },
  "North-West": {
    "nom_fr": "Nord-Ouest", "chef_lieu": "Bamenda",
    "population": 1728953, "superficie_km2": 17300,
    "pauvrete_2022": 66.8,
  },
  "West": {
    "nom_fr": "Ouest", "chef_lieu": "Bafoussam",
    "population": 1720047, "superficie_km2": 13892,
    "pauvrete_2022": 30.4,
  },
  "South": {
    "nom_fr": "Sud", "chef_lieu": "Ebolowa",
    "population": 634855, "superficie_km2": 47191,
    "pauvrete_2022": 14.9,
  },
  "South-West": {
    "nom_fr": "Sud-Ouest", "chef_lieu": "Buéa",
    "population": 1318079, "superficie_km2": 26410,
    "pauvrete_2022": 20.4,
  },
}

# Villes à statut particulier, suivies séparément dans l'ECAM 5.
VILLES = {
  "Yaoundé": {"population": 3098044, "pauvrete_2022": 10.8, "region": "Centre"},
  "Douala": {"population": 2510283, "pauvrete_2022": 8.3, "region": "Littoral"},
}

# --- Indicateurs complémentaires (conjoncture) -------------------------------
INDICATEURS_COMPLEMENTAIRES = {
  "dette_publique": {
    "libelle": "Dette publique",
    "valeur": 43.9, "unite": "% du PIB", "annee": "sept. 2025",
    "source": "tresor",
    "detail": "Encours de 14 591 Mds FCFA, dont 63 % de dette extérieure. "
         "Le FMI juge la dette soutenable, avec un objectif sous 50 % du PIB.",
  },
  "solde_budgetaire": {
    "libelle": "Solde budgétaire global",
    "valeur": -0.8, "unite": "% du PIB", "annee": "2025",
    "source": "tresor",
    "detail": "Amélioration après -1,5 % en 2024, liée à la quasi-suppression "
         "des subventions aux hydrocarbures (15 Mds FCFA contre 640 Mds en 2023).",
  },
  "exportations_pib": {
    "libelle": "Exportations de biens et services",
    "valeur": 13.1, "unite": "% du PIB", "annee": "2025",
    "source": "bm",
    "detail": "Environ 85 % des exportations sont des produits peu ou pas "
         "transformés (pétrole brut, cacao, bois, GNL, coton).",
  },
  "urbanisation": {
    "libelle": "Taux d'urbanisation",
    "valeur": 55.7, "unite": "%", "annee": "2025",
    "source": "bm",
    "detail": "La pauvreté reste très inégale entre ville (21,6 %) et "
         "campagne (56,3 %).",
  },
  "part_agriculture": {
    "libelle": "Poids de l'agriculture",
    "valeur": 16.8, "unite": "% du PIB", "annee": "2025",
    "source": "bm",
    "detail": "Secteur primaire : 17 % du PIB, 41,5 % de la population active, "
         "et 64,9 % des personnes pauvres.",
  },
  "acces_banque": {
    "libelle": "Population avec un compte ou mobile money",
    "valeur": 45.7, "unite": "% (15 ans et plus)", "annee": "2022",
    "source": "ins",
    "detail": "61,0 % en milieu urbain contre 25,2 % en milieu rural ; "
         "42,7 % utilisent le mobile money.",
  },
}


def serie_annees(indicateur):
  """Retourne les années triées d'un indicateur national."""
  return sorted(int(a) for a in INDICATEURS_NATIONAUX[indicateur]["serie"])


def derniere_valeur(indicateur):
  """Dernière valeur disponible d'un indicateur national."""
  s = INDICATEURS_NATIONAUX[indicateur]["serie"]
  annee = max(s)
  return {"annee": annee, "valeur": s[annee]}


def variation(indicateur, periode=1):
  """Variation en points entre la dernière valeur et celle d'il y a `periode` ans."""
  s = INDICATEURS_NATIONAUX[indicateur]["serie"]
  annees = sorted(s)
  if len(annees) <= periode:
    return None
  return round(s[annees[-1]] - s[annees[-1 - periode]], 2)


def totaux_cemac(annee="2025"):
  """Agrège les six pays de la CEMAC pour une année donnée."""
  pib = sum(CEMAC_PIB[c].get(annee, 0) for c in CEMAC_PIB)
  pop = sum(CEMAC_POPULATION[c].get(annee, 0) for c in CEMAC_POPULATION)
  croiss = [CEMAC_CROISSANCE[c].get(annee) for c in CEMAC_CROISSANCE]
  croiss = [v for v in croiss if v is not None]
  infl = [CEMAC_INFLATION[c].get(annee) for c in CEMAC_INFLATION]
  infl = [v for v in infl if v is not None]
  return {
    "annee": annee,
    "pib_mds_usd": round(pib, 1),
    "population_millions": round(pop, 1),
    "croissance_moyenne": round(sum(croiss) / len(croiss), 2) if croiss else None,
    "inflation_moyenne": round(sum(infl) / len(infl), 2) if infl else None,
    "pib_par_habitant": round(pib * 1e9 / (pop * 1e6), 0) if pop else None,
    "nb_pays": len(PAYS_CEMAC),
  }


def tableau_cemac(annee="2025"):
  """Tableau pays par pays prêt à afficher."""
  lignes = []
  for iso, info in PAYS_CEMAC.items():
    lignes.append({
      "iso": iso,
      "nom": info["nom_fr"],
      "capital": info["capital"],
      "croissance": CEMAC_CROISSANCE[iso].get(annee),
      "inflation": CEMAC_INFLATION[iso].get(annee),
      "pib_mds": CEMAC_PIB[iso].get(annee),
      "population": CEMAC_POPULATION[iso].get(annee),
      "pib_hab": CEMAC_PIB_HAB[iso].get(annee),
    })
  lignes.sort(key=lambda x: x["pib_mds"] or 0, reverse=True)
  return lignes


def tableau_regions():
  """Tableau des régions du Cameroun, avec densité calculée."""
  lignes = []
  for cle, r in REGIONS.items():
    densite = round(r["population"] / r["superficie_km2"], 1)
    lignes.append({
      "cle": cle,
      "nom": r["nom_fr"],
      "chef_lieu": r["chef_lieu"],
      "population": r["population"],
      "superficie": r["superficie_km2"],
      "densite": densite,
      "pauvrete": r["pauvrete_2022"],
    })
  lignes.sort(key=lambda x: x["population"], reverse=True)
  return lignes


# --- Base de connaissances de l'assistant (mode hors ligne) ------------------
# Utilisée par « Le Perpétuel » quand aucune connexion à un LLM n'est possible.
FICHES = [
  {
    "id": "croissance",
    "titre": "Croissance économique du Cameroun",
    "mots_cles": ["croissance", "pib", "produit intérieur", "activité",
           "expansion", "récession", "croissance du pib"],
    "niveau": "public",
    "contenu": (
      "Le Cameroun a enregistré une croissance du PIB réel de 3,5 % en 2024 "
      "puis 3,2 % en 2025, selon la Banque mondiale. La croissance est portée "
      "par les activités non pétrolières (services, agriculture, élevage, "
      "manufacturier), tandis que les activités pétrolières reculent d'environ "
      "9,2 %. Pour 2026, les autorités projettent 3,3 %, très en deçà de "
      "l'ambition de la SND30 (8,1 % de moyenne sur 2020-2030). "
      "Source : Banque mondiale ; DG Trésor."
    ),
  },
  {
    "id": "inflation",
    "titre": "Inflation et prix",
    "mots_cles": ["inflation", "prix", "coût de la vie", "cherté", "ipc",
           "pouvoir d'achat"],
    "niveau": "public",
    "contenu": (
      "L'inflation est revenue de 7,4 % en 2023 à 4,5 % en 2024, puis 3,4 % "
      "en 2025, sous l'effet de la politique monétaire restrictive de la BEAC, "
      "de la consolidation budgétaire et du ralentissement des prix "
      "alimentaires. Elle reste proche du critère de convergence CEMAC fixé à "
      "3 %. Le FMI anticipe 3,5 % en 2026. "
      "Source : Banque mondiale ; BEAC ; FMI."
    ),
  },
  {
    "id": "pauvrete",
    "titre": "Pauvreté et inégalités",
    "mots_cles": ["pauvreté", "pauvre", "gini", "inégalité", "seuil",
           "conditions de vie", "ecam"],
    "niveau": "public",
    "contenu": (
      "Selon l'ECAM 5 (2022), 37,7 % de la population est pauvre, soit "
      "10,1 millions de personnes vivant sous le seuil de 813 FCFA par jour "
      "(296 691 FCFA par an). La pauvreté est de 21,6 % en ville contre "
      "56,3 % à la campagne. Elle est la plus forte à l'Extrême-Nord (69,2 %), "
      "au Nord-Ouest (66,8 %) et au Nord (61,1 %), et la plus faible à Douala "
      "(8,3 %) et Yaoundé (10,8 %). L'indice de Gini est de 40,1. "
      "Source : INS Cameroun, ECAM 5."
    ),
  },
  {
    "id": "dette",
    "titre": "Dette publique",
    "mots_cles": ["dette", "endettement", "financement", "budget", "déficit",
           "fmi", "soutenabilité"],
    "niveau": "public",
    "contenu": (
      "À fin septembre 2025, la dette publique du Cameroun atteignait "
      "14 591 Mds FCFA, soit 43,9 % du PIB, dont 63 % de dette extérieure. "
      "Le déficit budgétaire global s'est établi à -0,8 % du PIB en 2025 "
      "(contre -1,5 % en 2024). Le FMI juge la dette soutenable, avec une "
      "trajectoire vers 35 % du PIB à moyen terme ; le service de la dette "
      "pourrait toutefois absorber près de 35 % des recettes en 2026. "
      "Source : DG Trésor ; FMI."
    ),
  },
  {
    "id": "cemac",
    "titre": "Zone CEMAC",
    "mots_cles": ["cemac", "beac", "zone", "région", "sous-région", "union",
           "convergence", "franc cfa"],
    "niveau": "public",
    "contenu": (
      "La CEMAC réunit six pays : Cameroun, Gabon, Congo, Tchad, République "
      "Centrafricaine et Guinée équatoriale. Son PIB cumulé atteint environ "
      "134 milliards de dollars en 2025 pour 67 millions d'habitants. Le "
      "Cameroun y pèse plus de 44 %. La BEAC prévoit un ralentissement de la "
      "croissance à 2,4 % et une inflation ramenée à 2,2 % à l'horizon 2026. "
      "Source : BEAC ; Banque mondiale ; CEMAC."
    ),
  },
  {
    "id": "region",
    "titre": "Disparités régionales",
    "mots_cles": ["région", "régional", "extrême-nord", "littoral", "centre",
           "disparité", "territoire", "carte", "décentralisation"],
    "niveau": "public",
    "contenu": (
      "Les dix régions du Cameroun présentent de fortes disparités. En "
      "population, le Centre (3,1 M), l'Extrême-Nord (3,1 M) et le Littoral "
      "(2,5 M) concentrent le plus d'habitants, alors que le Sud (0,63 M) et "
      "l'Est (0,77 M) sont les moins peuplés. En densité, le Littoral (124 "
      "hab/km²) et l'Ouest (124 hab/km²) contrastent avec l'Est (7 hab/km²) et "
      "le Sud (13 hab/km²). En pauvreté, l'écart va de 8,3 % à Douala à 69,2 % "
      "à l'Extrême-Nord. "
      "Source : INS Cameroun (ECAM 5, RGPH)."
    ),
  },
  {
    "id": "marche_travail",
    "titre": "Marché du travail",
    "mots_cles": ["emploi", "chômage", "travail", "salarié", "informel",
           "activité", "salaire", "smig"],
    "niveau": "public",
    "contenu": (
      "Le taux de chômage au sens du BIT est de 3,8 % (2022), mais le taux "
      "d'activité est de 62,3 % et le taux de salarisation seulement 27,6 %, "
      "ce qui traduit le poids de l'informalité. La pauvreté est très liée au "
      "secteur : 59,0 % des actifs du secteur primaire sont pauvres, contre "
      "18,9 % dans le tertiaire. Le SMIG est de 36 270 FCFA par mois. "
      "Source : INS Cameroun, ECAM 5."
    ),
  },
  {
    "id": "methodologie",
    "titre": "Méthodologie statistique",
    "mots_cles": ["méthode", "statistique", "modèle", "régression", "tendance",
           "prévision", "corrélation"],
    "niveau": "public",
    "contenu": (
      "La plateforme applique trois familles de méthodes : (1) analyse "
      "descriptive, moyennes, écarts-types, indices de concentration ; "
      "(2) analyse de tendance, régression linéaire par les moindres carrés "
      "ordinaires sur les séries annuelles, avec R², p-value et prévision à "
      "court terme ; (3) analyse de corrélation, coefficient de Pearson entre "
      "indicateurs. Les tests sont assortis de leurs hypothèses et d'un niveau "
      "de signification de 5 %."
    ),
  },
]


def reponse_hors_ligne(question, niveau="public"):
  """Moteur de règles utilisé quand le LLM en ligne est indisponible.

  Recherche par mots-clés sur la base de fiches, puis renvoie la meilleure
  correspondance. Retourne toujours un texte, jamais d'erreur.
  """
  q = (question or "").lower()
  scores = []
  for fiche in FICHES:
    if fiche["niveau"] == "confidentiel" and niveau != "admin":
      continue
    if niveau == "admin" and fiche["niveau"] == "confidentiel":
      pass
    score = 0
    for mot in fiche["mots_cles"]:
      if mot in q:
        score += len(mot)
    if fiche["titre"].lower() in q:
      score += 10
    if score:
      scores.append((score, fiche))
  if not scores:
    return {
      "texte": (
        "Je fonctionne actuellement en mode hors ligne : je réponds à "
        "partir de la base de connaissances locale de la plateforme, sans "
        "connexion à un modèle externe. Je peux vous renseigner sur la "
        "croissance, l'inflation, la pauvreté, la dette, la zone CEMAC, les "
        "disparités régionales, le marché du travail ou la méthodologie "
        "statistique. Reformulez votre question avec l'un de ces thèmes."
      ),
      "sources_fiches": [],
      "mode": "hors_ligne",
    }
  scores.sort(key=lambda x: -x[0])
  meilleures = [f for _, f in scores[:2]]
  texte = "\n\n".join(f["contenu"] for f in meilleures)
  return {
    "texte": texte,
    "sources_fiches": [{"id": f["id"], "titre": f["titre"]} for f in meilleures],
    "mode": "hors_ligne",
  }


# --- Contexte transmis au LLM en ligne ---------------------------------------
def contexte_donnees():
  """Résumé factuel des données, injecté dans le prompt du LLM."""
  tot = totaux_cemac("2025")
  lignes = [
    "DONNÉES DE LA PLATEFORME « ANALYSE CONJONCTURELLE » (Cameroun / CEMAC)",
    "",
    "Cameroun, indicateurs nationaux :",
  ]
  for cle, ind in INDICATEURS_NATIONAUX.items():
    d = derniere_valeur(cle)
    lignes.append(
      f"- {ind['libelle']} : {d['valeur']} {ind['unite']} ({d['annee']})"
    )
  lignes += [
    "",
    f"CEMAC {tot['annee']} : {tot['nb_pays']} pays, PIB cumulé "
    f"{tot['pib_mds_usd']} Mds USD, population {tot['population_millions']} M, "
    f"croissance moyenne {tot['croissance_moyenne']} %, inflation moyenne "
    f"{tot['inflation_moyenne']} %.",
    "",
    "Pays de la CEMAC (2025) :",
  ]
  for l in tableau_cemac("2025"):
    lignes.append(
      f"- {l['nom']} : croissance {l['croissance']} %, inflation "
      f"{l['inflation']} %, PIB {l['pib_mds']} Mds USD, "
      f"{l['population']} M habitants."
    )
  lignes += ["", "Régions du Cameroun (population et pauvreté 2022) :"]
  for r in tableau_regions():
    lignes.append(
      f"- {r['nom']} : {r['population']} habitants, densité {r['densite']} "
      f"hab/km², pauvreté {r['pauvrete']} %."
    )
  return "\n".join(lignes)
