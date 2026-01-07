from django.contrib import admin
from .models import Commande, ItemCommande

# Enregistrer les modèles principaux dans l’admin
admin.site.register(Commande)
admin.site.register(ItemCommande)

# Enregistrer ProfilLivraison seulement s’il existe
try:
    from .models import ProfilLivraison

    @admin.register(ProfilLivraison)
    class ProfilLivraisonAdmin(admin.ModelAdmin):
        list_display = ('user', 'telephone', 'adresse', 'ville', 'pays', 'codePostale')
        search_fields = ('user__username', 'telephone', 'ville', 'adresse')
        readonly_fields = ('user',)
        list_filter = ('ville', 'pays')

except ImportError:
    pass
