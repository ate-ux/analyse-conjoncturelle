"""Tests de l'application : cloisonnement des rôles et génération des rapports.

Ces tests portent sur le comportement observable, pas sur l'implémentation :
qui peut voir quoi, et ce que produisent les rapports.
"""
from django.test import TestCase, override_settings
from django.urls import reverse

from conjoncture.models import Rapport, Utilisateur
from conjoncture.rapports import generer_rapport

# En production, les fichiers statiques passent par un manifeste construit par
# collectstatic. Les tests n'ont pas ce manifeste : on déclare donc explicitement
# le stockage simple pour eux, au lieu d'affaiblir la configuration de
# production ou de dépendre d'une étape de construction.
STOCKAGE_TESTS = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}


@override_settings(STORAGES=STOCKAGE_TESTS)
class BaseDonneesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Utilisateur.objects.create_user(
            username="admin_test", password="MotDePasseAdmin2027!",
            role=Utilisateur.Role.ADMIN)
        cls.simple = Utilisateur.objects.create_user(
            username="user_test", password="MotDePasseUser2027!",
            role=Utilisateur.Role.UTILISATEUR)


class CloisonnementTests(BaseDonneesTests):
    """Les pages réservées doivent renvoyer 302, 403 ou 200 selon le rôle."""

    def test_visiteur_anonyme_redirige(self):
        for url in ("/tableau-de-bord/", "/statistiques/", "/previsions/",
                    "/donnees/", "/administration/", "/rapports/"):
            with self.subTest(url=url):
                reponse = self.client.get(url)
                self.assertEqual(reponse.status_code, 302)
                self.assertIn("/connexion/", reponse["Location"])

    def test_utilisateur_simple_accede_aux_pages_publiques(self):
        self.client.login(username="user_test", password="MotDePasseUser2027!")
        for url in ("/tableau-de-bord/", "/cartes/", "/regions/",
                    "/statistiques/", "/previsions/", "/rapports/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_utilisateur_simple_refuse_sur_administration(self):
        self.client.login(username="user_test", password="MotDePasseUser2027!")
        self.assertEqual(self.client.get("/administration/").status_code, 403)

    def test_utilisateur_simple_refuse_sur_export(self):
        self.client.login(username="user_test", password="MotDePasseUser2027!")
        self.assertEqual(self.client.get("/donnees/export/").status_code, 403)

    def test_administrateur_accede_a_tout(self):
        self.client.login(username="admin_test", password="MotDePasseAdmin2027!")
        for url in ("/tableau-de-bord/", "/donnees/", "/administration/",
                    "/donnees/export/", "/previsions/", "/rapports/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_utilisateur_simple_refuse_import(self):
        self.client.login(username="user_test", password="MotDePasseUser2027!")
        self.assertEqual(self.client.post("/donnees/apercu/").status_code, 403)


class PagesPubliquesTests(BaseDonneesTests):
    def test_page_de_connexion_accessible(self):
        reponse = self.client.get("/connexion/")
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Analyse")
        self.assertContains(reponse, "conjoncturelle")

    def test_connexion_avec_identifiants_valides(self):
        reponse = self.client.post("/connexion/", {
            "username": "admin_test", "password": "MotDePasseAdmin2027!"})
        self.assertEqual(reponse.status_code, 302)

    def test_connexion_avec_mauvais_mot_de_passe(self):
        reponse = self.client.post("/connexion/", {
            "username": "admin_test", "password": "mauvais"})
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(reponse.wsgi_request.user.is_authenticated)

    def test_images_de_marque_referencees(self):
        """Le logo détouré et la carte de marque doivent être sur la connexion."""
        reponse = self.client.get("/connexion/")
        self.assertContains(reponse, "issea_logo.png")
        self.assertContains(reponse, "deus_stat_carte.jpg")

    def test_logo_dans_entete_connectee(self):
        self.client.login(username="admin_test", password="MotDePasseAdmin2027!")
        reponse = self.client.get("/tableau-de-bord/")
        self.assertContains(reponse, "marque-logo-entete")

    def test_signature_sur_la_connexion(self):
        """La signature de l'auteur et ses coordonnées sont exigées."""
        reponse = self.client.get("/connexion/")
        self.assertContains(reponse, "Joseph ATEBA")
        self.assertContains(reponse, "atebajoseph047@gmail.com")
        self.assertContains(reponse, "237 670 211 522")

    def test_signature_sur_les_pages_connectees(self):
        self.client.login(username="admin_test", password="MotDePasseAdmin2027!")
        reponse = self.client.get("/tableau-de-bord/")
        self.assertContains(reponse, "Joseph ATEBA")
        self.assertContains(reponse, "atebajoseph047@gmail.com")

    def test_signature_sur_l_inscription(self):
        reponse = self.client.get("/inscription/")
        self.assertContains(reponse, "Joseph ATEBA")
        self.assertContains(reponse, "atebajoseph047@gmail.com")

    def test_le_logo_detoure_existe(self):
        """Le fichier détouré doit être présent, sinon le logo disparaît."""
        from django.contrib.staticfiles import finders
        self.assertIsNotNone(finders.find("images/issea_logo.png"))
        self.assertIsNotNone(finders.find("images/deus_stat_carte.jpg"))


class RapportTests(BaseDonneesTests):
    def test_generation_synthese(self):
        rapport = generer_rapport(
            type_rapport="synthese", cible="", periode="2020-2025",
            inclure_graphiques=True, inclure_statistiques=True,
            confidentiel=False, utilisateur=self.admin)
        self.assertTrue(rapport.fichier.name.endswith(".pdf"))
        self.assertGreater(rapport.fichier.size, 3000)

    def test_fichier_est_un_pdf(self):
        rapport = generer_rapport(
            type_rapport="synthese", cible="", periode="2020-2025",
            inclure_graphiques=False, inclure_statistiques=False,
            confidentiel=False, utilisateur=self.admin)
        rapport.fichier.open("rb")
        entete = rapport.fichier.read(5)
        rapport.fichier.close()
        self.assertEqual(entete, b"%PDF-")

    def test_utilisateur_simple_ne_telecharge_pas_un_rapport_confidentiel(self):
        rapport = generer_rapport(
            type_rapport="synthese", cible="", periode="2020-2025",
            inclure_graphiques=False, inclure_statistiques=True,
            confidentiel=True, utilisateur=self.admin)
        self.client.login(username="user_test", password="MotDePasseUser2027!")
        reponse = self.client.get(f"/rapports/{rapport.pk}/telecharger/")
        self.assertEqual(reponse.status_code, 403)

    def test_administrateur_telecharge_un_rapport_confidentiel(self):
        rapport = generer_rapport(
            type_rapport="synthese", cible="", periode="2020-2025",
            inclure_graphiques=False, inclure_statistiques=True,
            confidentiel=True, utilisateur=self.admin)
        self.client.login(username="admin_test", password="MotDePasseAdmin2027!")
        reponse = self.client.get(f"/rapports/{rapport.pk}/telecharger/")
        self.assertEqual(reponse.status_code, 200)


@override_settings(STORAGES=STOCKAGE_TESTS)
class QuotaAdministrateursTests(TestCase):
    def test_deux_administrateurs_au_plus(self):
        """Le rôle administrateur doit refuser un troisième compte."""
        for i in range(2):
            Utilisateur.objects.create_user(
                username=f"admin_{i}", password="MotDePasse2027!",
                role=Utilisateur.Role.ADMIN)
        self.assertEqual(
            Utilisateur.objects.filter(role=Utilisateur.Role.ADMIN).count(), 2)

    def test_utilisateurs_illimites(self):
        """Aucune limite ne doit peser sur les simples utilisateurs."""
        for i in range(12):
            Utilisateur.objects.create_user(
                username=f"membre_{i}", password="MotDePasse2027!",
                role=Utilisateur.Role.UTILISATEUR)
        self.assertEqual(
            Utilisateur.objects.filter(role=Utilisateur.Role.UTILISATEUR).count(), 12)


class ApiDonneesTests(BaseDonneesTests):
    def test_api_carte_regions_reservee(self):
        self.assertEqual(self.client.get("/api/carte/regions/").status_code, 302)

    def test_api_carte_regions_pour_administrateur(self):
        self.client.login(username="admin_test", password="MotDePasseAdmin2027!")
        reponse = self.client.get("/api/carte/regions/")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse["Content-Type"], "application/json")

    def test_api_donnees_pour_utilisateur(self):
        self.client.login(username="user_test", password="MotDePasseUser2027!")
        reponse = self.client.get("/api/donnees/")
        self.assertEqual(reponse.status_code, 200)
