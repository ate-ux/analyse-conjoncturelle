"""Tests de la désaisonnalisation.

Les séries de test sont construites à la main, avec une tendance linéaire et
une saisonnalité connue : on peut donc vérifier que le module retrouve
exactement les coefficients qu'on y a mis.
"""
from django.test import SimpleTestCase

from conjoncture import saisonnalite


def serie_additive(n_annees=6, depart=100.0, pas=2.5,
                   coefs=(2.0, 0.0, -1.0, -1.0)):
    """Série trimestrielle à tendance linéaire et saisonnalité additive connue."""
    serie = {}
    for i in range(n_annees):
        for t in range(1, 5):
            rang_global = i * 4 + (t - 1)
            serie[f"{2020 + i}-T{t}"] = depart + rang_global * pas + coefs[t - 1]
    return serie


class MoyenneMobileTests(SimpleTestCase):
    def test_serie_trop_courte(self):
        couples = [(str(2020 + i), float(i)) for i in range(3)]
        self.assertEqual(saisonnalite.moyenne_mobile(couples, 4), {})

    def test_tendance_lineaire_exacte(self):
        """Sur une droite, la moyenne mobile doit redonner la droite elle-même."""
        couples = [(str(2000 + i), 10.0 + 2.0 * i) for i in range(12)]
        moyennes = saisonnalite.moyenne_mobile(couples, 4)
        for i, valeur in moyennes.items():
            with self.subTest(indice=i):
                self.assertAlmostEqual(valeur, 10.0 + 2.0 * i, places=6)

    def test_fenetre_impaire(self):
        couples = [(str(2000 + i), 5.0 + i) for i in range(9)]
        moyennes = saisonnalite.moyenne_mobile(couples, 3)
        for i, valeur in moyennes.items():
            with self.subTest(indice=i):
                self.assertAlmostEqual(valeur, 5.0 + i, places=6)

    def test_extremites_absentes(self):
        couples = [(str(2000 + i), float(i)) for i in range(10)]
        moyennes = saisonnalite.moyenne_mobile(couples, 4)
        self.assertNotIn(0, moyennes)
        self.assertNotIn(9, moyennes)


class CoefficientsTests(SimpleTestCase):
    def test_coefficients_retrouves(self):
        """Les coefficients estimés doivent être ceux construits."""
        serie = serie_additive(coefs=(2.0, 0.0, -1.0, -1.0))
        estimation = saisonnalite.coefficients_saisonniers(serie, "additif")
        attendus = {1: 2.0, 2: 0.0, 3: -1.0, 4: -1.0}
        for rang, attendu in attendus.items():
            with self.subTest(rang=rang):
                self.assertAlmostEqual(estimation["coefficients"][rang], attendu,
                                       places=6)

    def test_somme_nulle_en_additif(self):
        """Le recentrage additif impose une somme de coefficients nulle."""
        serie = serie_additive(coefs=(5.0, 1.0, -2.0, -3.0), pas=4.0)
        estimation = saisonnalite.coefficients_saisonniers(serie, "additif")
        total = sum(estimation["coefficients"].values())
        self.assertAlmostEqual(total, 0.0, places=6)

    def test_moyenne_unite_en_multiplicatif(self):
        serie = {f"{2020 + i}-T{t}": (100.0 + i * 10) * (1.0 + 0.1 * (t == 1))
                 for i in range(5) for t in range(1, 5)}
        estimation = saisonnalite.coefficients_saisonniers(serie, "multiplicatif")
        moyenne = sum(estimation["coefficients"].values()) / 4
        self.assertAlmostEqual(moyenne, 1.0, places=6)

    def test_serie_annuelle_sans_coefficient(self):
        estimation = saisonnalite.coefficients_saisonniers(
            {"2020": 1.0, "2021": 2.0, "2022": 3.0})
        self.assertEqual(estimation["coefficients"], {})


class DessaisonalisationTests(SimpleTestCase):
    def test_cvs_egale_tendance(self):
        """Sur une série additive pure, la série CVS doit coller à la tendance."""
        serie = serie_additive()
        d = saisonnalite.decomposer(serie, modele="additif")
        self.assertTrue(d["disponible"])
        for ligne in d["lignes"]:
            if ligne["tendance"] is not None:
                with self.subTest(periode=ligne["periode"]):
                    self.assertAlmostEqual(ligne["cvs"], ligne["tendance"], places=6)

    def test_etendue_preservee(self):
        serie = serie_additive()
        cvs = saisonnalite.dessaisonaliser(serie, "additif")
        self.assertEqual(set(cvs), set(serie))
        self.assertEqual(len(cvs), len(serie))

    def test_serie_vide(self):
        self.assertEqual(saisonnalite.dessaisonaliser({}), {})

    def test_valeurs_invalides_ignorees(self):
        serie = {"2020-T1": 10.0, "2020-T2": None, "2020-T3": "abc", "2020-T4": 13.0}
        cvs = saisonnalite.dessaisonaliser(serie, "additif")
        self.assertNotIn("2020-T2", cvs)
        self.assertNotIn("2020-T3", cvs)


class DecompositionTests(SimpleTestCase):
    def test_serie_annuelle_refusee(self):
        d = saisonnalite.decomposer({str(2015 + i): 100.0 + i for i in range(10)})
        self.assertFalse(d["disponible"])
        self.assertIn("annuelle", d["raison"])

    def test_une_seule_annee_refusee(self):
        d = saisonnalite.decomposer({f"2024-T{t}": 10.0 + t for t in range(1, 5)})
        self.assertFalse(d["disponible"])
        self.assertIn("deux", d["raison"])

    def test_serie_vide(self):
        self.assertFalse(saisonnalite.decomposer({})["disponible"])

    def test_amplitude_egale_aux_coefficients(self):
        serie = serie_additive(coefs=(2.0, 0.0, -1.0, -1.0))
        d = saisonnalite.decomposer(serie, modele="additif")
        self.assertAlmostEqual(d["amplitude_saisonniere"], 3.0, places=6)

    def test_lignes_completes(self):
        d = saisonnalite.decomposer(serie_additive(), modele="additif")
        for ligne in d["lignes"]:
            with self.subTest(periode=ligne["periode"]):
                for cle in ("periode", "libelle", "observee", "tendance",
                            "coef", "cvs", "residu"):
                    self.assertIn(cle, ligne)


class ChoixModeleTests(SimpleTestCase):
    def test_serie_courte_retenue_additive(self):
        court = {f"2020-T{t}": 10.0 + t for t in range(1, 5)}
        modele, _ = saisonnalite.choisir_modele(court)
        self.assertEqual(modele, "additif")

    def test_amplitude_croissante_donne_multiplicatif(self):
        serie = {}
        for i in range(8):
            for t in range(1, 5):
                niveau = 100.0 * (1.6 ** i)
                serie[f"{2016 + i}-T{t}"] = niveau * (1.0 + 0.2 * (t == 1))
        modele, raison = saisonnalite.choisir_modele(serie)
        self.assertEqual(modele, "multiplicatif")
        self.assertIn("croissante", raison)

    def test_serie_annuelle(self):
        modele, raison = saisonnalite.choisir_modele({str(2015 + i): 1.0 for i in range(10)})
        self.assertEqual(modele, "additif")
        self.assertIn("annuelle", raison)
