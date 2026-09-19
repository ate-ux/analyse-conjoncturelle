"""Administration Django de la plateforme."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Conversation, Journal, Message, Rapport, Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = ("username", "nom_complet", "role", "organisation", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email", "organisation")
    fieldsets = UserAdmin.fieldsets + (
        ("Profil conjoncturel", {
            "fields": ("role", "organisation", "fonction"),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Profil conjoncturel", {
            "fields": ("role", "organisation", "fonction"),
        }),
    )


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("titre", "utilisateur", "cree_le", "maj_le")
    list_filter = ("cree_le",)
    search_fields = ("titre", "utilisateur__username")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "role", "mode", "cree_le")
    list_filter = ("role", "mode", "cree_le")
    search_fields = ("contenu",)


@admin.register(Rapport)
class RapportAdmin(admin.ModelAdmin):
    list_display = ("titre", "type_rapport", "cible", "periode", "genere_par", "cree_le")
    list_filter = ("type_rapport", "cree_le")
    search_fields = ("titre", "cible")


@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ("cree_le", "utilisateur", "action", "adresse_ip")
    list_filter = ("action", "cree_le")
    search_fields = ("action", "detail", "utilisateur__username")
