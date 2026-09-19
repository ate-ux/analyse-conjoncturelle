"""Tests de la prévision multivariée (régression multiple).

Deux jeux de données servent aux tests, et la distinction est volontaire :

- une série **exacte**, sans bruit, pour vérifier que les coefficients sont
  retrouvés au chiffre près ;
- une série **bruitée**, réaliste, pour vérifier les diagnostics et la
  prévision. Sur un ajustement parfait, le résidu est nul : Fisher est infini,
  l'intervalle de prévision est de largeur nulle, et le test ne prouverait rien.
"""
from django.test import SimpleTestCase

from conjoncture import multivarie


def modele_exact(n=24, a=3.0, b=-2.0, constante=10.0):
    """Construit y = constante + a·x1 + b·x2, sans aucun bruit."""
    x1, x2, y = {}, {}, {}
    for i in range(n):
        annee = str(2002 + i)
        v1 = 50.0 + 1.5 * i + (i % 4) * 2.0
        v2 = 2.0 + 0.1 * i - (i % 3) * 0.5
        x1[annee], x2[annee] = round(v1, 4), round(v2, 4)
        y[annee] = round(constante + a * v1 + b * v2, 6)
    return x1, x2, y


def modele_bruite(n=24, a=3.0, b=-2.0, constante=10.0, amplitude=1.5):
    """Même modèle, avec un résidu déterministe mais non reproductible par lui."""
    x1, x2, y = {}, {}, {}
    for i in range(n):
        annee = str(2002 + i)
        v1 = 50.0 + 1.5 * i + (i % 4) * 2.0
        v2 = 2.0 + 0.1 * i - (i % 3) * 0.5
        # Résidu en dents de scie, d'amplitude modérée
        bruit = amplitude * (1 if i % 3 == 0 else (-0.5 if i % 3 == 1 else -0.2))
        x1[annee], x2[annee] = round(v1, 4), round(v2, 4)
        y[annee] = round(constante + a * v1 + b * v2 + bruit, 6)
    return x1, x2, y


class AjustementExactTests(SimpleTestCase):
    def test_coefficients_exacts(self):
        """Sans bruit, la régression doit retrouver les coefficients construits."""
        x1, x2, y = modele_exact()
        r = multivarie.ajuster(y, [("x1", x1), ("x2", x2)])
        self.assertTrue(r["disponible"])
        par_nom = {c["nom"]: c for c in r["coefficients"]}
        self.assertAlmostEqual(par_nom["x1"]["valeur"], 3.0, places=3)
        self.assertAlmostEqual(par_nom["x2"]["valeur"], -2.0, places=3)
        self.assertAlmostEqual(par_nom["constante"]["valeur"], 10.0, places=3)
        self.assertAlmostEqual(r["r2"], 1.0, places=6)

    def test_ordonnee_a_l_origine_en_unites_d_origine(self):
        """La constante doit être exprimée dans les unités de y, pas standardisées."""
        x1, x2, y = modele_exact(constante=250.0)
        r = multivarie.ajuster(y, [("x1", x1), ("x2", x2)])
        constante = next(c for c in r["coefficients"] if c["nom"] == "constante")
        self.assertAlmostEqual(constante["valeur"], 250.0, places=3)

    def test_ajustement_parfait_ne_divise_pas_par_zero(self):
        """Un R² de 1 rend Fisher infini : le calcul ne doit pas lever d'erreur."""
        x1, x2, y = modele_exact()
        r = multivarie.ajuster(y, [("x1", x1), ("x2", x2)])
        self.assertEqual(r["p_fisher"], 0.0)


class DiagnosticsTests(SimpleTestCase):
    def test_diagnostics_presents_sur_serie_bruitee(self):
        x1, x2, y = modele_bruite()
        r = multivarie.ajuster(y, [("x1", x1), ("x2", x2)])
        self.assertTrue(r["disponible"])
        for cle in ("r2", "r2_ajuste", "f", "p_fisher", "durbin_watson",
                    "ecart_residuel", "n_observations", "degres_liberte"):
            with self.subTest(cle=cle):
                self.assertIsNotNone(r.get(cle))

    def test_r2_eleve_sur_modele_bien_specifie(self):
        x1, x2, y = modele_bruite()
        r = multivarie.ajuster(y, [("x1", x1), ("x2", x2)])
        self.assertGreater(r["r2"], 0.9)

    def test_ecart_residuel_positif_sur_serie_bruitee(self):
        x1, x2, y = modele_bruite()
        r = multivarie.ajuster(y, [("x1", x1), ("x2", x2)])
        self.assertGreater(r["ecart_residuel"], 0)

    def test_nombre_de_coefficients(self):
        """Une constante plus un coefficient par régresseur."""
        x1, x2, y = modele_bruite()
        r = multivarie.ajuster(y, [("x1", x1), ("x2", x2)])
        self.assertEqual(len(r["coefficients"]), 3)


class CasLimitesTests(SimpleTestCase):
    def test_echantillon_trop_court(self):
        r = multivarie.ajuster({"2020": 1.0, "2021": 2.0},
                               [("x", {"2020": 1.0, "2021": 2.0})])
        self.assertFalse(r["disponible"])
        self.assertIn("huit", r["raison"])

    def test_sans_regresseur(self):
        x1, x2, y = modele_exact()
        r = multivarie.ajuster(y, [])
        self.assertFalse(r["disponible"])
        self.assertIn("aucune variable", r["raison"])

    def test_plus_de_variables_que_d_observations(self):
        y = {str(2000 + i): float(i) for i in range(8)}
        expl = [(f"v{j}", {str(2000 + i): float(i + j) for i in range(8)})
                for j in range(8)]
        r = multivarie.ajuster(y, expl)
        self.assertFalse(r["disponible"])

    def test_alignement_sur_periodes_communes(self):
        """Seules les périodes présentes partout doivent servir."""
        y = {str(2000 + i): float(i) for i in range(12)}
        x = {str(2000 + i): float(i * 2) for i in range(10)}
        r = multivarie.ajuster(y, [("x", x)])
        self.assertEqual(r["n_observations"], 10)


class VifTests(SimpleTestCase):
    def test_vif_sous_le_seuil_si_pas_de_colinearite(self):
        """Deux régresseurs distincts restent sous le seuil d'alerte.

        Le VIF de 3 environ est normal ici : x1 et x2 croissent toutes deux dans
        le temps, donc elles partagent un peu de variance. Ce qui compte est
        qu'elles restent loin du seuil de 10 qui déclenche l'alerte.
        """
        x1, x2, y = modele_exact()
        r = multivarie.ajuster(y, [("x1", x1), ("x2", x2)])
        par_nom = {c["nom"]: c for c in r["coefficients"]}
        for nom in ("x1", "x2"):
            with self.subTest(variable=nom):
                self.assertLess(par_nom[nom]["vif"], multivarie.SEUIL_VIF)
        self.assertFalse(any("Colinéarité" in a for a in r["alertes"]))

    def test_vif_eleve_si_colineaires(self):
        """Deux régresseurs quasi identiques doivent déclencher l'alerte."""
        x1, x2, y = modele_bruite()
        doublon = {p: v * 1.001 + 0.01 for p, v in x1.items()}
        r = multivarie.ajuster(y, [("x1", x1), ("presque_x1", doublon)])
        par_nom = {c["nom"]: c for c in r["coefficients"]}
        self.assertGreater(par_nom["presque_x1"]["vif"], multivarie.SEUIL_VIF)
        self.assertTrue(any("Colinéarité" in a for a in r["alertes"]))


class DurbinWatsonTests(SimpleTestCase):
    def test_serie_trop_courte(self):
        self.assertIsNone(multivarie.durbin_watson([1.0]))

    def test_residus_nuls(self):
        self.assertIsNone(multivarie.durbin_watson([0.0, 0.0, 0.0]))

    def test_residus_alternes_donnent_dw_eleve(self):
        """Des résidus qui changent de signe à chaque pas donnent un DW > 3."""
        dw = multivarie.durbin_watson([5.0, -5.0, 5.0, -5.0, 5.0, -5.0])
        self.assertGreater(dw, multivarie.DW_HAUT)

    def test_residus_en_marche_donnent_dw_faible(self):
        """Des résidus qui persistent donnent un DW nettement sous 1."""
        dw = multivarie.durbin_watson([1.0, 0.9, 1.1, 0.95, 1.05, 1.0])
        self.assertLess(dw, multivarie.DW_BAS)

    def test_residus_non_correles_tombent_dans_la_plage(self):
        """Une suite sans structure temporelle donne un DW proche de 2.

        La suite est centrée et non corrélée : c'est la référence qui doit
        tomber entre les bornes usuelles, sans quoi la statistique serait
        inutilisable comme critère.
        """
        residus = [0.423, -0.335, -0.676, 0.138, -0.259, -0.719,
                   0.765, 0.479, -0.886, 0.105, -0.043, 1.007]
        dw = multivarie.durbin_watson(residus)
        self.assertGreater(dw, multivarie.DW_BAS)
        self.assertLess(dw, multivarie.DW_HAUT)


class PrevisionTests(SimpleTestCase):
    def test_prevision_disponible_et_intervalle_non_degenere(self):
        x1, x2, y = modele_bruite()
        p = multivarie.prevoir(y, [("x1", x1), ("x2", x2)], horizon=3)
        self.assertTrue(p["disponible"])
        self.assertEqual(len(p["points"]), 3)
        for point in p["points"]:
            with self.subTest(periode=point["periode"]):
                # L'intervalle doit être strictement ouvert : un ajustement
                # parfait le réduirait à un point, ce qui serait trompeur.
                self.assertLess(point["bas"], point["valeur"])
                self.assertLess(point["valeur"], point["haut"])

    def test_horizon_annuel_incremente_les_annees(self):
        x1, x2, y = modele_bruite()
        p = multivarie.prevoir(y, [("x1", x1), ("x2", x2)], horizon=2)
        self.assertEqual([pt["periode"] for pt in p["points"]], ["2026", "2027"])

    def test_avertissement_sur_les_regresseurs(self):
        """L'extrapolation des variables explicatives doit être signalée."""
        x1, x2, y = modele_bruite()
        p = multivarie.prevoir(y, [("x1", x1), ("x2", x2)], horizon=2)
        self.assertTrue(any("extrapol" in a for a in p["alertes"]))

    def test_modele_indisponible_remonte_la_raison(self):
        p = multivarie.prevoir({"2020": 1.0}, [("x", {"2020": 2.0})])
        self.assertFalse(p["disponible"])
        self.assertIn("raison", p)

    def test_prevision_proche_de_la_vraie_valeur(self):
        """Sur un modèle bien spécifié, la prévision doit rester plausible."""
        x1, x2, y = modele_bruite()
        p = multivarie.prevoir(y, [("x1", x1), ("x2", x2)], horizon=1)
        derniere = y[max(y, key=lambda k: int(k))]
        self.assertLess(abs(p["points"][0]["valeur"] - derniere), 20.0)


class SyntheseTests(SimpleTestCase):
    def test_phrase_avec_r2(self):
        x1, x2, y = modele_bruite()
        p = multivarie.prevoir(y, [("x1", x1), ("x2", x2)], horizon=2)
        texte = multivarie.synthese(p)
        self.assertIn("variance", texte)

    def test_modele_indisponible(self):
        texte = multivarie.synthese({"disponible": False, "raison": "trop court"})
        self.assertEqual(texte, "trop court")
