"""
Génération automatique des rapports de conjoncture en PDF.

Quatre types de rapports sont produits :

* ``synthese``  , synthèse conjoncturelle du Cameroun (indicateurs + lecture) ;
* ``regional``  , profil d'une région (population, densité, pauvreté) ;
* ``pays``    , profil d'un pays de la CEMAC ;
* ``statistique`` , note statistique (tendances MCO, prévisions, corrélations).

La mise en page est réalisée avec ReportLab ; les graphiques sont tracés
directement en vectoriel (barres et courbes), sans dépendance externe.
"""
from __future__ import annotations

import io
import os
from datetime import datetime

from django.conf import settings
from django.core.files.base import ContentFile
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
  HRFlowable,
  PageBreak,
  Paragraph,
  SimpleDocTemplate,
  Spacer,
  Table,
  TableStyle,
)

from . import stats
from .data import economie

# --- Charte graphique du document -------------------------------------------
BLEU = colors.HexColor("#0f3d5c")
BLEU_CLAIR = colors.HexColor("#1d6fa5")
ACCENT = colors.HexColor("#c9a227")
GRIS = colors.HexColor("#55606b")
GRIS_CLAIR = colors.HexColor("#eef2f5")
ROUGE = colors.HexColor("#b23a48")
VERT = colors.HexColor("#2f7d54")

MARGE = 18 * mm


def _styles():
  base = getSampleStyleSheet()
  return {
    "titre": ParagraphStyle(
      "titre", parent=base["Title"], fontName="Helvetica-Bold",
      fontSize=20, leading=24, textColor=BLEU, spaceAfter=2,
    ),
    "sous_titre": ParagraphStyle(
      "sous_titre", parent=base["Normal"], fontName="Helvetica",
      fontSize=10.5, leading=14, textColor=GRIS, spaceAfter=10,
    ),
    "h1": ParagraphStyle(
      "h1", parent=base["Heading1"], fontName="Helvetica-Bold",
      fontSize=14, leading=18, textColor=BLEU, spaceBefore=12, spaceAfter=6,
    ),
    "h2": ParagraphStyle(
      "h2", parent=base["Heading2"], fontName="Helvetica-Bold",
      fontSize=11.5, leading=15, textColor=BLEU_CLAIR,
      spaceBefore=9, spaceAfter=4,
    ),
    "corps": ParagraphStyle(
      "corps", parent=base["BodyText"], fontName="Helvetica",
      fontSize=9.8, leading=14, textColor=colors.HexColor("#24292f"),
      alignment=4, spaceAfter=6,
    ),
    "puce": ParagraphStyle(
      "puce", parent=base["BodyText"], fontName="Helvetica",
      fontSize=9.6, leading=13.5, leftIndent=10, bulletIndent=2,
      textColor=colors.HexColor("#24292f"), spaceAfter=3,
    ),
    "note": ParagraphStyle(
      "note", parent=base["Normal"], fontName="Helvetica-Oblique",
      fontSize=8.4, leading=11.5, textColor=GRIS,
    ),
    "cellule": ParagraphStyle(
      "cellule", parent=base["Normal"], fontName="Helvetica",
      fontSize=8.6, leading=11,
    ),
  }


def _entete_pied(canvas, doc, titre_doc=""):
  canvas.saveState()
  largeur, hauteur = A4
  # Bandeau supérieur
  canvas.setFillColor(BLEU)
  canvas.rect(0, hauteur - 16 * mm, largeur, 16 * mm, stroke=0, fill=1)
  canvas.setFillColor(colors.white)
  canvas.setFont("Helvetica-Bold", 10.5)
  canvas.drawString(MARGE, hauteur - 10.6 * mm, "ANALYSE CONJONCTURELLE")
  canvas.setFont("Helvetica", 8.6)
  canvas.drawRightString(
    largeur - MARGE, hauteur - 10.6 * mm,
    "Cameroun · Zone CEMAC",
  )
  # Pied de page
  canvas.setStrokeColor(GRIS_CLAIR)
  canvas.setLineWidth(0.6)
  canvas.line(MARGE, 14 * mm, largeur - MARGE, 14 * mm)
  canvas.setFillColor(GRIS)
  canvas.setFont("Helvetica", 7.6)
  canvas.drawString(MARGE, 10 * mm, getattr(settings, "RAPPORT_ORGANISATION", ""))
  canvas.drawRightString(largeur - MARGE, 10 * mm, f"Page {doc.page}")
  canvas.drawCentredString(
    largeur / 2, 10 * mm,
    datetime.now().strftime("Généré le %d/%m/%Y à %H:%M"),
  )
  canvas.restoreState()


# --- Graphiques vectoriels ---------------------------------------------------
def _graphique_lignes(serie, largeur=165 * mm, hauteur=48 * mm,
           couleur=BLEU_CLAIR, titre="", unite="", seuil=None):
  """Courbe d'évolution d'une série {année: valeur}, tracée en vectoriel."""
  from reportlab.graphics.shapes import Drawing, Line, PolyLine, String, Rect

  annees = sorted(int(a) for a in serie)
  valeurs = [float(serie[a]) for a in annees]
  if not valeurs:
    return Spacer(1, 1)
  mini, maxi = min(valeurs), max(valeurs)
  if seuil is not None:
    mini = min(mini, seuil)
    maxi = max(maxi, seuil)
  if maxi == mini:
    maxi = mini + 1

  marge_g, marge_d, marge_h, marge_b = 14, 6, 12, 12
  zone_l = largeur - marge_g - marge_d
  zone_h = hauteur - marge_h - marge_b

  d = Drawing(largeur, hauteur)
  # Axes
  d.add(Line(marge_g, marge_b, marge_g, marge_b + zone_h,
        strokeColor=GRIS, strokeWidth=0.6))
  d.add(Line(marge_g, marge_b, marge_g + zone_l, marge_b,
        strokeColor=GRIS, strokeWidth=0.6))

  def px(i):
    return marge_g + (zone_l * i / max(1, len(annees) - 1))

  def py(v):
    return marge_b + zone_h * (v - mini) / (maxi - mini)

  # Ligne de seuil
  if seuil is not None:
    y = py(seuil)
    d.add(Line(marge_g, y, marge_g + zone_l, y,
          strokeColor=ACCENT, strokeWidth=0.7, strokeDashArray=[2, 2]))
    d.add(String(marge_g + zone_l - 32, y + 1.5,
           f"seuil {seuil:g}{unite}", fontSize=6.4, fillColor=ACCENT))

  pts = []
  for i, v in enumerate(valeurs):
    pts.extend([px(i), py(v)])
  d.add(PolyLine(pts, strokeColor=couleur, strokeWidth=1.4))
  for i, v in enumerate(valeurs):
    d.add(Line(px(i) - 1.2, py(v), px(i) + 1.2, py(v),
          strokeColor=couleur, strokeWidth=2.2))
    d.add(String(px(i) - 4.5, py(v) + 2.4, f"{v:g}",
           fontSize=5.6, fillColor=GRIS))
    d.add(String(px(i) - 5, marge_b - 8, str(annees[i]),
           fontSize=6, fillColor=GRIS))
  return d


def _graphique_barres(paires, largeur=165 * mm, hauteur=52 * mm,
           couleur=BLEU_CLAIR, unite="", titre=""):
  """Barres horizontales : paires [(libellé, valeur), ...], triées."""
  from reportlab.graphics.shapes import Drawing, Line, Rect, String

  if not paires:
    return Spacer(1, 1)
  paires = sorted(paires, key=lambda p: (p[1] is None, p[1] or 0), reverse=True)
  maxi = max((p[1] or 0) for p in paires) or 1

  marge_g, marge_d = 62, 22
  zone_l = largeur - marge_g - marge_d
  interligne = hauteur / max(1, len(paires))
  barre_h = min(9, interligne * 0.58)

  d = Drawing(largeur, hauteur)
  for i, (libelle, valeur) in enumerate(paires):
    y = hauteur - (i + 1) * interligne + (interligne - barre_h) / 2
    d.add(Rect(marge_g, y, zone_l, barre_h,
          fillColor=GRIS_CLAIR, strokeColor=None))
    if valeur is None:
      continue
    lg = max(1.2, zone_l * abs(float(valeur)) / maxi)
    d.add(Rect(marge_g, y, lg, barre_h, fillColor=couleur, strokeColor=None))
    d.add(String(marge_g - 4, y + barre_h * 0.28, str(libelle)[:26],
           fontSize=6.8, fillColor=colors.HexColor("#24292f"),
           textAnchor="end"))
    d.add(String(marge_g + lg + 3, y + barre_h * 0.28,
           f"{float(valeur):g}{unite}", fontSize=6.6, fillColor=GRIS))
  return d


def _tableau(entetes, lignes, largeurs=None, styles=None):
  st = styles or _styles()
  donnees = [[Paragraph(f"<b>{e}</b>", st["cellule"]) for e in entetes]]
  for ligne in lignes:
    donnees.append([
      c if hasattr(c, "wrap") else Paragraph(str(c), st["cellule"])
      for c in ligne
    ])
  t = Table(donnees, colWidths=largeurs, hAlign="LEFT", repeatRows=1)
  t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), BLEU),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 3.4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3.4),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cfd8de")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_CLAIR]),
  ]))
  return t


# --- Blocs de contenu --------------------------------------------------------
def _bloc_entete(type_rapport, cible, periode, confidentiel):
  st = _styles()
  libelles = dict(Rapport_type_labels())
  flux = [
    Paragraph(libelles.get(type_rapport, "Rapport"), st["titre"]),
    Paragraph(
      f"{cible or 'Cameroun · Zone CEMAC'}, période {periode or 'à jour'}",
      st["sous_titre"],
    ),
  ]
  if confidentiel:
    bandeau = Table(
      [[Paragraph(
        "<b>DOCUMENT CONFIDENTIEL</b>, réservé aux administrateurs de "
        "la plateforme. Ne pas diffuser.",
        ParagraphStyle("conf", parent=st["note"], textColor=colors.white,
                fontSize=8.2),
      )]],
      colWidths=[165 * mm], hAlign="LEFT",
    )
    bandeau.setStyle(TableStyle([
      ("BACKGROUND", (0, 0), (-1, -1), ROUGE),
      ("TOPPADDING", (0, 0), (-1, -1), 4),
      ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
      ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    flux += [bandeau, Spacer(1, 6)]
  flux.append(HRFlowable(width="100%", thickness=1.1, color=ACCENT, spaceAfter=8))
  return flux


def Rapport_type_labels():
  return [
    ("synthese", "Synthèse conjoncturelle du Cameroun"),
    ("regional", "Profil régional"),
    ("pays", "Profil pays, CEMAC"),
    ("statistique", "Note statistique"),
  ]


def _bloc_synthese(inclure_graphiques, inclure_statistiques):
  st = _styles()
  flux = [Paragraph("1. Vue d'ensemble", st["h1"])]
  tot = economie.totaux_cemac("2025")
  flux.append(Paragraph(
    f"Le Cameroun demeure la première économie de la CEMAC, avec environ "
    f"44 % du PIB de la zone. En 2025, le PIB nominal atteint "
    f"{economie.INDICATEURS_NATIONAUX['pib_usd']['serie'][2025]:.1f} Mds USD, "
    f"la croissance s'établit à "
    f"{economie.INDICATEURS_NATIONAUX['pib_croissance']['serie'][2025]:.1f} % "
    f"et l'inflation revient à "
    f"{economie.INDICATEURS_NATIONAUX['inflation']['serie'][2025]:.1f} %. "
    f"L'espace communautaire réunit {tot['nb_pays']} pays, "
    f"{tot['population_millions']:.1f} millions d'habitants et un PIB cumulé "
    f"de {tot['pib_mds_usd']:.1f} Mds USD.", st["corps"]))

  flux.append(Paragraph("2. Principaux indicateurs", st["h1"]))
  lignes = []
  for cle, ind in economie.INDICATEURS_NATIONAUX.items():
    d = economie.derniere_valeur(cle)
    var = economie.variation(cle)
    lignes.append([
      ind["libelle"], f"{d['valeur']} {ind['unite']}", str(d["annee"]),
      f"{var:+.2f}" if var is not None else ", ",
      economie.SOURCES.get(ind["source"], {}).get("nom", "").split(", ")[0].strip(),
    ])
  flux += [_tableau(
    ["Indicateur", "Valeur", "Année", "Var. 1 an", "Source"],
    lignes,
    largeurs=[58 * mm, 28 * mm, 14 * mm, 18 * mm, 47 * mm],
  ), Spacer(1, 8)]

  if inclure_graphiques:
    flux.append(Paragraph("3. Évolution des séries", st["h1"]))
    for cle in ("pib_croissance", "inflation", "pib_usd"):
      ind = economie.INDICATEURS_NATIONAUX[cle]
      flux.append(Paragraph(
        f"{ind['libelle']} ({ind['unite']})", st["h2"]))
      flux.append(_graphique_lignes(
        ind["serie"], unite=ind["unite"], seuil=ind.get("seuil")))
      flux.append(Spacer(1, 4))
    flux.append(Paragraph("Disparités régionales de la pauvreté (2022)", st["h2"]))
    flux.append(_graphique_barres(
      [(r["nom"], r["pauvrete"]) for r in economie.tableau_regions()],
      unite=" %", couleur=ACCENT))
    flux.append(PageBreak())

  if inclure_statistiques:
    flux.append(Paragraph("4. Annexe statistique", st["h1"]))
    analyse = stats.analyse_indicateur("pib_croissance")
    t = analyse["tendance"]
    flux.append(Paragraph(
      f"La régression MCO sur la croissance du PIB réel "
      f"({t['debut']}-{t['fin']}) donne une pente de {t['pente']:+.3f} point "
      f"par an, un R² de {t['r2']:.3f} et une p-value de "
      f"{t['p_value'] if t['p_value'] is not None else 'n.d.'}. "
      f"La tendance est donc {'significative' if t['significatif'] else 'non significative'} "
      f"au seuil de 5 %.", st["corps"]))
    flux.append(_tableau(
      ["Indicateur", "Moyenne", "Écart-type", "CV (%)", "Min", "Max"],
      [
        [
          ind["libelle"],
          f"{stats.descriptives(list(ind['serie'].values()))['moyenne']}",
          f"{stats.descriptives(list(ind['serie'].values()))['ecart_type']}",
          f"{stats.descriptives(list(ind['serie'].values()))['cv']}",
          f"{stats.descriptives(list(ind['serie'].values()))['minimum']}",
          f"{stats.descriptives(list(ind['serie'].values()))['maximum']}",
        ]
        for ind in economie.INDICATEURS_NATIONAUX.values()
      ],
      largeurs=[58 * mm, 22 * mm, 22 * mm, 18 * mm, 20 * mm, 25 * mm],
    ))
    flux.append(Spacer(1, 8))
    corr = stats.correlations_principales()
    if corr:
      flux.append(Paragraph("Corrélations entre indicateurs", st["h2"]))
      flux.append(_tableau(
        ["Indicateur A", "Indicateur B", "r", "p-value", "Lecture"],
        [[c["a"], c["b"], f"{c['r']:+.3f}",
         f"{c['p_value']}" if c["p_value"] is not None else "n.d.",
         f"{c['sens']} {c['force']}"] for c in corr],
        largeurs=[52 * mm, 52 * mm, 14 * mm, 18 * mm, 29 * mm],
      ))
  return flux


def _bloc_region(cible, inclure_graphiques):
  st = _styles()
  cle = None
  for k, r in economie.REGIONS.items():
    if cible and (cible.lower() in k.lower() or cible.lower() in r["nom_fr"].lower()):
      cle = k
      break
  if cle is None:
    cle = "Littoral"
  r = economie.REGIONS[cle]
  densite = round(r["population"] / r["superficie_km2"], 1)
  moy = stats.descriptives([x["pauvrete"] for x in economie.tableau_regions()])

  flux = [
    Paragraph("1. Identité de la région", st["h1"]),
    _tableau(
      ["Caractéristique", "Valeur"],
      [
        ["Région", r["nom_fr"]],
        ["Chef-lieu", r["chef_lieu"]],
        ["Population", f"{r['population']:,} habitants".replace(",", " ")],
        ["Superficie", f"{r['superficie_km2']:,} km²".replace(",", " ")],
        ["Densité", f"{densite} hab/km²"],
        ["Taux de pauvreté (2022)", f"{r['pauvrete_2022']} %"],
        ["Note de lecture", r.get("note", ", ")],
      ],
      largeurs=[62 * mm, 103 * mm],
    ),
    Spacer(1, 8),
    Paragraph("2. Lecture conjoncturelle", st["h1"]),
    Paragraph(
      f"La région du {r['nom_fr']} compte {r['population']:,} habitants, "
      f"soit une densité de {densite} habitants au km². Son taux de pauvreté "
      f"de {r['pauvrete_2022']} % se situe "
      f"{'au-dessus' if r['pauvrete_2022'] > moy['moyenne'] else 'en dessous'} "
      f"de la moyenne nationale des régions ({moy['moyenne']} %), pour un "
      f"écart-type inter-régional de {moy['ecart_type']} points. "
      f"Source : INS Cameroun, ECAM 5 (2022) et RGPH."
      .replace(",", " "), st["corps"]),
  ]
  if inclure_graphiques:
    flux.append(Paragraph("Pauvreté : la région dans son contexte", st["h2"]))
    flux.append(_graphique_barres(
      [(x["nom"], x["pauvrete"]) for x in economie.tableau_regions()],
      unite=" %", couleur=BLEU_CLAIR))
  return flux


def _bloc_pays(cible, inclure_graphiques):
  st = _styles()
  iso = None
  for code, info in economie.PAYS_CEMAC.items():
    if cible and (cible.lower() in code.lower()
           or cible.lower() in info["nom_fr"].lower()):
      iso = code
      break
  if iso is None:
    iso = "GAB"
  info = economie.PAYS_CEMAC[iso]
  lignes = economie.tableau_cemac("2025")
  ligne = next((l for l in lignes if l["iso"] == iso), None)
  analyse = stats.analyse_cemac()

  flux = [
    Paragraph("1. Fiche pays", st["h1"]),
    _tableau(
      ["Indicateur", "Valeur (2025)"],
      [
        ["Pays", info["nom_fr"]],
        ["Capitale", info["capital"]],
        ["Code ISO", iso],
        ["PIB nominal", f"{ligne['pib_mds']} Mds USD" if ligne else "n.d."],
        ["Croissance du PIB réel", f"{ligne['croissance']} %" if ligne else "n.d."],
        ["Inflation", f"{ligne['inflation']} %" if ligne else "n.d."],
        ["Population", f"{ligne['population']} millions" if ligne else "n.d."],
        ["PIB par habitant", f"{ligne['pib_hab']} USD" if ligne else "n.d."],
      ],
      largeurs=[62 * mm, 103 * mm],
    ),
    Spacer(1, 8),
    Paragraph("2. Positionnement dans la zone CEMAC", st["h1"]),
  ]
  if ligne:
    flux.append(Paragraph(
      f"Avec un PIB de {ligne['pib_mds']} Mds USD, le {info['nom_fr']} "
      f"représente environ "
      f"{(ligne['pib_mds'] / analyse['totaux']['pib_mds_usd'] * 100):.1f} % "
      f"du PIB de la CEMAC. La croissance de {ligne['croissance']} % se "
      f"compare à la moyenne de la zone ({analyse['totaux']['croissance_moyenne']} %) "
      f"et l'inflation de {ligne['inflation']} % à une moyenne régionale de "
      f"{analyse['totaux']['inflation_moyenne']} %. "
      f"Source : Banque mondiale ; BEAC.", st["corps"]))
    if ligne["inflation"] and ligne["inflation"] > 3:
      flux.append(Paragraph(
        "L'inflation dépasse le critère de convergence communautaire fixé "
        "à 3 %.", st["note"]))
  if inclure_graphiques:
    flux.append(Paragraph("PIB nominal des pays de la zone (Mds USD)", st["h2"]))
    flux.append(_graphique_barres(
      [(l["nom"], l["pib_mds"]) for l in lignes], couleur=BLEU_CLAIR))
  return flux


def _bloc_statistique():
  st = _styles()
  flux = [
    Paragraph("1. Méthode", st["h1"]),
    Paragraph(
      "La note mobilise trois outils : statistiques descriptives (moyenne, "
      "écart-type, coefficient de variation) ; régression linéaire par les "
      "moindres carrés ordinaires pour la tendance et la prévision "
      "(pente, R², erreur type, p-value de Student) ; corrélation de Pearson "
      "avec test de significativité au seuil de 5 %.", st["corps"]),
    Paragraph("2. Tendances et prévisions", st["h1"]),
  ]
  lignes = []
  for cle, ind in economie.INDICATEURS_NATIONAUX.items():
    t = stats.tendance(ind["serie"])
    p = stats.prevision(ind["serie"], 2)
    cible = ""
    if p and p["points"]:
      point = p["points"][-1]
      cible = f"{point['valeur']} [{point['bas']} ; {point['haut']}] ({point['annee']})"
    lignes.append([
      ind["libelle"],
      f"{t['pente']:+.3f}" if t else ", ",
      f"{t['r2']:.3f}" if t else ", ",
      f"{t['p_value']:.4f}" if t and t["p_value"] is not None else "n.d.",
      "oui" if t and t["significatif"] else "non",
      cible or ", ",
    ])
  flux += [_tableau(
    ["Indicateur", "Pente/an", "R²", "p-value", "Signif.", "Prévision (IC 80 %)"],
    lignes,
    largeurs=[46 * mm, 17 * mm, 13 * mm, 16 * mm, 14 * mm, 59 * mm],
  ), Spacer(1, 9)]

  reg = stats.analyse_regionale()
  flux.append(Paragraph("3. Structure régionale", st["h1"]))
  flux.append(Paragraph(
    f"Sur les dix régions du Cameroun, la population moyenne s'établit à "
    f"{reg['population']['moyenne']} habitants pour un écart-type de "
    f"{reg['population']['ecart_type']}, soit un coefficient de variation de "
    f"{reg['population']['cv']} %. L'indice de concentration de Herfindahl "
    f"de la population atteint {reg['concentration_population']['valeur']} "
    f"({reg['concentration_population']['lecture']}). Le taux de pauvreté "
    f"varie de {reg['ecart_pauvrete']['min']['pauvrete']} % "
    f"({reg['ecart_pauvrete']['min']['nom']}) à "
    f"{reg['ecart_pauvrete']['max']['pauvrete']} % "
    f"({reg['ecart_pauvrete']['max']['nom']}).", st["corps"]))

  corr = stats.correlations_principales()
  if corr:
    flux.append(Paragraph("4. Corrélations", st["h1"]))
    flux.append(_tableau(
      ["Indicateur A", "Indicateur B", "r", "p-value", "Lecture"],
      [[c["a"], c["b"], f"{c['r']:+.3f}",
       f"{c['p_value']}" if c["p_value"] is not None else "n.d.",
       f"{c['sens']} {c['force']}"] for c in corr],
      largeurs=[52 * mm, 52 * mm, 14 * mm, 18 * mm, 29 * mm],
    ))
  return flux


def _bloc_sources():
  st = _styles()
  flux = [
    Paragraph("Sources et avertissement", st["h1"]),
    Paragraph(
      "Les données reproduites proviennent de sources publiques. Elles sont "
      "citées par indicateur dans les tableaux ci-dessus.", st["corps"]),
  ]
  for cle, s in economie.SOURCES.items():
    flux.append(Paragraph(f"• <b>{s['nom']}</b>, {s['url']}", st["puce"]))
  flux.append(Spacer(1, 4))
  flux.append(Paragraph(
    "Les projections et prévisions sont des extrapolations statistiques ; "
    "elles ne constituent ni une prévision officielle ni un conseil "
    "d'investissement. Rapport produit automatiquement par la plateforme.",
    st["note"]))
  return flux


# --- Point d'entrée ----------------------------------------------------------
def generer_rapport(type_rapport, cible="", periode="2020-2025",
          inclure_graphiques=True, inclure_statistiques=True,
          confidentiel=False, utilisateur=None):
  """Génère le PDF, l'enregistre dans le modèle Rapport et le retourne."""
  from .models import Rapport

  libelles = dict(Rapport_type_labels())
  base_titre = libelles.get(type_rapport, "Rapport de conjoncture")
  titre = f"{base_titre}, {cible}" if cible else base_titre

  tampon = io.BytesIO()
  doc = SimpleDocTemplate(
    tampon, pagesize=A4,
    leftMargin=MARGE, rightMargin=MARGE,
    topMargin=22 * mm, bottomMargin=18 * mm,
    title=titre, author=getattr(settings, "RAPPORT_ORGANISATION", ""),
    subject="Analyse conjoncturelle, Cameroun / CEMAC",
  )

  flux = _bloc_entete(type_rapport, cible, periode, confidentiel)
  if type_rapport == "synthese":
    flux += _bloc_synthese(inclure_graphiques, inclure_statistiques)
  elif type_rapport == "regional":
    flux += _bloc_region(cible, inclure_graphiques)
  elif type_rapport == "pays":
    flux += _bloc_pays(cible, inclure_graphiques)
  elif type_rapport == "statistique":
    flux += _bloc_statistique()
  else:
    flux += _bloc_synthese(inclure_graphiques, inclure_statistiques)
  flux += [Spacer(1, 10)] + _bloc_sources()

  doc.build(flux, onFirstPage=lambda c, d: _entete_pied(c, d, titre),
       onLaterPages=lambda c, d: _entete_pied(c, d, titre))

  contenu = tampon.getvalue()
  horodatage = datetime.now().strftime("%Y%m%d-%H%M")
  nom_fichier = f"rapport_{type_rapport}_{horodatage}.pdf"

  rapport = Rapport.objects.create(
    titre=titre,
    type_rapport=type_rapport,
    cible=cible,
    periode=periode,
    genere_par=utilisateur if getattr(utilisateur, "is_authenticated", False) or utilisateur else None,
    donnees={
      "confidentiel": bool(confidentiel),
      "inclure_graphiques": bool(inclure_graphiques),
      "inclure_statistiques": bool(inclure_statistiques),
      "octets": len(contenu),
    },
  )
  rapport.fichier.save(nom_fichier, ContentFile(contenu), save=True)
  return rapport
