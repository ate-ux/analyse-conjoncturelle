"""Tests du module d'import (lecture des fichiers CSV et Excel).

L'interface réelle du module est en deux temps :
    lignes, erreur = imports.lire_fichier(fichier)
    observations, format, periodicite, erreurs = imports.analyser(lignes)
"""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from conjoncture import imports


def csv_fichier(contenu, nom="donnees.csv"):
    return SimpleUploadedFile(nom, contenu.encode("utf-8"), content_type="text/csv")


def analyser_texte(contenu, nom="donnees.csv"):
    """Raccourci : lit puis analyse, et retourne le quadruplet d'analyse."""
    fichier = csv_fichier(contenu, nom)
    lignes, erreur = imports.lire_fichier(fichier)
    if erreur:
        return [], "inconnu", "annuelle", [{"ligne": 0, "motif": erreur}]
    return imports.analyser(lignes)


class LectureCsvTests(SimpleTestCase):
    def test_lecture_renvoie_lignes_et_entetes(self):
        f = csv_fichier("periode;entite;valeur\n2023;Cameroun;3,5\n")
        lignes, erreur = imports.lire_fichier(f)
        self.assertIsNone(erreur)
        self.assertEqual(len(lignes), 1)
        self.assertIn("_entetes", lignes[0])
        self.assertEqual(lignes[0]["valeur"], "3,5")

    def test_lecture_nombre_de_lignes(self):
        f = csv_fichier("periode;entite;valeur\n2023;Cameroun;3,5\n2024;Cameroun;4,2\n")
        lignes, erreur = imports.lire_fichier(f)
        self.assertIsNone(erreur)
        self.assertEqual(len(lignes), 2)

    def test_fichier_trop_court_signale(self):
        f = csv_fichier("periode;entite;valeur\n")
        lignes, erreur = imports.lire_fichier(f)
        self.assertIsNotNone(erreur)

    def test_extension_refusee(self):
        f = SimpleUploadedFile("note.pdf", b"%PDF-1.4", content_type="application/pdf")
        lignes, erreur = imports.lire_fichier(f)
        self.assertEqual(lignes, [])
        self.assertIn("non pris en charge", erreur)


class AnalyseFormatLongTests(SimpleTestCase):
    def test_point_virgule_et_virgule_decimale(self):
        obs, fmt, per, err = analyser_texte(
            "periode;entite;valeur\n2023;Cameroun;3,5\n")
        self.assertEqual(len(obs), 1)
        self.assertAlmostEqual(obs[0]["valeur"], 3.5)
        self.assertEqual(fmt, "long")

    def test_virgule_comme_separateur(self):
        obs, fmt, per, err = analyser_texte(
            "periode,entite,valeur\n2023,Cameroun,3.5\n")
        self.assertEqual(len(obs), 1)
        self.assertAlmostEqual(obs[0]["valeur"], 3.5)

    def test_entite_conservee(self):
        obs, *_ = analyser_texte(
            "periode;entite;valeur\n2023;Cameroun;3,5\n2023;Gabon;2,8\n")
        self.assertEqual({o["entite"] for o in obs}, {"Cameroun", "Gabon"})

    def test_periodicite_annuelle_deduite(self):
        obs, fmt, per, err = analyser_texte(
            "periode;entite;valeur\n2022;Cameroun;3,1\n2023;Cameroun;3,5\n")
        self.assertEqual(per, "annuelle")

    def test_periodes_trimestrielles_reconnues(self):
        obs, fmt, per, err = analyser_texte(
            "periode;entite;valeur\n"
            "2023-T1;Cameroun;1,0\n2023-T2;Cameroun;1,5\n"
            "2023-T3;Cameroun;1,2\n2023-T4;Cameroun;1,8\n")
        self.assertEqual(len(obs), 4)
        self.assertEqual(per, "trimestrielle")
        self.assertEqual(obs[0]["periode"], "2023-T1")

    def test_periodes_mensuelles_reconnues(self):
        lignes = ["periode;entite;valeur"]
        for m in range(1, 7):
            lignes.append(f"2023-{m:02d};Cameroun;{m}.0")
        obs, fmt, per, err = analyser_texte("\n".join(lignes))
        self.assertEqual(len(obs), 6)
        self.assertEqual(per, "mensuelle")

    def test_lignes_invalides_signalees_avec_numero(self):
        obs, fmt, per, err = analyser_texte(
            "periode;entite;valeur\n"
            "2023;Cameroun;3,5\n"
            "pas-une-periode;Cameroun;4,0\n"
            "2024;Cameroun;abc\n")
        self.assertEqual(len(obs), 1)
        self.assertEqual(len(err), 2)
        for rejet in err:
            self.assertIn("ligne", rejet)
            self.assertIn("motif", rejet)
        # La numérotation suit celle du fichier, en-tête comprise
        self.assertEqual([r["ligne"] for r in err], [3, 4])

    def test_periode_normalisee(self):
        """Une période écrite autrement doit être rangée sous sa forme canonique."""
        obs, *_ = analyser_texte("periode;entite;valeur\n2023/T2;Cameroun;1,5\n")
        self.assertEqual(obs[0]["periode"], "2023-T2")


class AnalyseFormatLargeTests(SimpleTestCase):
    def test_une_colonne_par_annee(self):
        obs, fmt, per, err = analyser_texte(
            "entite;2022;2023;2024\n"
            "Cameroun;3,1;3,5;4,2\n"
            "Gabon;2,8;2,9;3,0\n")
        self.assertEqual(fmt, "large")
        self.assertEqual(len(obs), 6)
        self.assertEqual(per, "annuelle")

    def test_entites_reconnues_en_format_large(self):
        obs, *_ = analyser_texte(
            "entite;2022;2023\nCameroun;3,1;3,5\nGabon;2,8;2,9\n")
        self.assertEqual({o["entite"] for o in obs}, {"Cameroun", "Gabon"})

    def test_valeurs_manquantes_ignorees(self):
        """Une cellule vide ne produit pas d'observation, sans être une erreur."""
        obs, fmt, per, err = analyser_texte(
            "entite;2022;2023\nCameroun;3,1;\n")
        self.assertEqual(len(obs), 1)
        self.assertEqual(err, [])


class FormatInconnuTests(SimpleTestCase):
    def test_aucune_colonne_reconnaissable(self):
        obs, fmt, per, err = analyser_texte("a;b;c\n1;2;3\n4;5;6\n")
        self.assertEqual(obs, [])
        self.assertEqual(fmt, "inconnu")
        self.assertTrue(err)
        self.assertIn("motif", err[0])


class ApercuTests(SimpleTestCase):
    def test_resume_complet(self):
        obs, *_ = analyser_texte(
            "periode;entite;valeur\n"
            "2022;Cameroun;3,1\n2023;Cameroun;3,5\n2023;Gabon;2,8\n")
        resume = imports.apercu(obs, [])
        self.assertEqual(resume["nb_observations"], 3)
        self.assertEqual(resume["nb_entites"], 2)
        self.assertEqual(resume["debut"], "2022")
        self.assertEqual(resume["fin"], "2023")
        self.assertAlmostEqual(resume["min"], 2.8)
        self.assertAlmostEqual(resume["max"], 3.5)
        self.assertIn("echantillon", resume)

    def test_apercu_vide(self):
        resume = imports.apercu([], [])
        self.assertEqual(resume["nb_observations"], 0)
        self.assertIsNone(resume["debut"])
        self.assertIsNone(resume["min"])


class LectureExcelTests(SimpleTestCase):
    def _classeur(self, lignes, nom="donnees.xlsx"):
        import openpyxl
        classeur = openpyxl.Workbook()
        feuille = classeur.active
        for ligne in lignes:
            feuille.append(ligne)
        flux = io.BytesIO()
        classeur.save(flux)
        return SimpleUploadedFile(
            nom, flux.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument"
                         ".spreadsheetml.sheet")

    def test_lecture_puis_analyse(self):
        f = self._classeur([["periode", "entite", "valeur"],
                            ["2023", "Cameroun", 3.5],
                            ["2024", "Cameroun", 4.2]])
        lignes, erreur = imports.lire_fichier(f)
        self.assertIsNone(erreur)
        obs, fmt, per, err = imports.analyser(lignes)
        self.assertEqual(len(obs), 2)
        self.assertAlmostEqual(obs[0]["valeur"], 3.5)

    def test_excel_format_large(self):
        f = self._classeur([["entite", 2022, 2023],
                            ["Cameroun", 3.1, 3.5],
                            ["Gabon", 2.8, 2.9]])
        lignes, erreur = imports.lire_fichier(f)
        obs, fmt, per, err = imports.analyser(lignes)
        self.assertEqual(fmt, "large")
        self.assertEqual(len(obs), 4)

    def test_entetes_numeriques_excel(self):
        """Excel peut livrer les années en nombres : elles doivent être lues."""
        f = self._classeur([["entite", 2022, 2023], ["Cameroun", 3.1, 3.5]])
        lignes, erreur = imports.lire_fichier(f)
        obs, fmt, per, err = imports.analyser(lignes)
        self.assertEqual(len(obs), 2)
        self.assertEqual({o["periode"] for o in obs}, {"2022", "2023"})
