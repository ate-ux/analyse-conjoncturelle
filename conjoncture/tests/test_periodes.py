"""Tests du module de gestion des périodicités."""
from django.test import SimpleTestCase

from conjoncture import periodes


class DecompositionTests(SimpleTestCase):
    def test_annee_simple(self):
        self.assertEqual(periodes.decomposer("2024"), (2024, 1, "annuelle"))

    def test_trimestre_avec_t(self):
        self.assertEqual(periodes.decomposer("2024-T3"), (2024, 3, "trimestrielle"))

    def test_trimestre_avec_q(self):
        self.assertEqual(periodes.decomposer("2024Q3"), (2024, 3, "trimestrielle"))

    def test_semestre(self):
        self.assertEqual(periodes.decomposer("2024-S2"), (2024, 2, "semestrielle"))

    def test_mois(self):
        self.assertEqual(periodes.decomposer("2024-07"), (2024, 7, "mensuelle"))

    def test_separateur_barre(self):
        self.assertEqual(periodes.decomposer("2024/T3"), (2024, 3, "trimestrielle"))

    def test_espaces_ignores(self):
        self.assertEqual(periodes.decomposer(" 2024-T1 "), (2024, 1, "trimestrielle"))

    def test_entree_invalide(self):
        for mauvais in ("", None, "abc", "2024-T9", "2024-13"):
            with self.subTest(valeur=mauvais):
                self.assertIsNone(periodes.decomposer(mauvais))


class FormatageTests(SimpleTestCase):
    def test_aller_retour(self):
        for periode in ("2024", "2024-T2", "2024-S1", "2024-11"):
            with self.subTest(periode=periode):
                annee, rang, per = periodes.decomposer(periode)
                self.assertEqual(periodes.formater(annee, rang, per), periode)

    def test_libelle_mois(self):
        self.assertEqual(periodes.libelle("2024-01"), "janvier 2024")
        self.assertEqual(periodes.libelle("2024-12"), "décembre 2024")

    def test_libelle_trimestre(self):
        self.assertEqual(periodes.libelle("2024-T3"), "T3 2024")


class InferenceTests(SimpleTestCase):
    def test_serie_annuelle(self):
        self.assertEqual(periodes.inferer(["2020", "2021", "2022"]), "annuelle")

    def test_serie_trimestrielle(self):
        self.assertEqual(
            periodes.inferer(["2020-T1", "2020-T2", "2020-T3"]), "trimestrielle"
        )

    def test_serie_mixte_retient_la_plus_fine(self):
        self.assertEqual(periodes.inferer(["2020", "2020-T2"]), "trimestrielle")

    def test_liste_vide(self):
        self.assertEqual(periodes.inferer([]), "annuelle")


class TriTests(SimpleTestCase):
    def test_ordre_chronologique(self):
        melange = ["2021", "2019", "2020"]
        self.assertEqual(sorted(melange, key=periodes.cle_tri),
                         ["2019", "2020", "2021"])

    def test_trimestres_avant_annee_suivante(self):
        melange = ["2021-T1", "2020-T4", "2020-T1"]
        self.assertEqual(sorted(melange, key=periodes.cle_tri),
                         ["2020-T1", "2020-T4", "2021-T1"])

    def test_rang_absolu_croissant(self):
        rangs = [periodes.rang_absolu(p) for p in
                 ("2020-T1", "2020-T2", "2020-T3", "2020-T4", "2021-T1")]
        self.assertEqual(rangs, sorted(rangs))
        self.assertAlmostEqual(rangs[1] - rangs[0], 0.25)


class GenerationTests(SimpleTestCase):
    def test_toutes_periodes_trimestrielles(self):
        liste = periodes.toutes_periodes(2020, 2021, "trimestrielle")
        self.assertEqual(len(liste), 8)
        self.assertEqual(liste[0], "2020-T1")
        self.assertEqual(liste[-1], "2021-T4")

    def test_toutes_periodes_annuelles(self):
        self.assertEqual(periodes.toutes_periodes(2020, 2022), ["2020", "2021", "2022"])
