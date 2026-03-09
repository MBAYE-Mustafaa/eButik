from django.contrib import admin
from django.utils.html import format_html
from .models import Commande, ItemCommande

# customize admin to display useful information
class ItemCommandeInline(admin.TabularInline):
    model = ItemCommande
    extra = 0
    readonly_fields = ('produit','quantite','prix_unitaire','prix_total')

@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ('id','core_order','user','email_livraison','telephone_livraison','date_commande','total','status')
    search_fields = ('core_order__id','user__username','email_livraison','telephone_livraison')
    list_filter = ('date_commande',)
    inlines = [ItemCommandeInline]
    readonly_fields = ('date_commande','core_order')
    date_hierarchy = 'date_commande'
    ordering = ('-date_commande',)
    list_per_page = 50  # Show more items per page to reduce pagination
    
    def get_queryset(self, request):
        """Override to ensure all commandes are visible"""
        qs = super().get_queryset(request)
        return qs.select_related('core_order', 'user').prefetch_related('items')

    def status(self, obj):
        if obj.core_order:
            status = obj.core_order.status
            if status == 'paid':
                return format_html('<span style="color: green; font-weight: bold;">Payé</span>')
            elif status == 'pending':
                return format_html('<span style="color: orange; font-weight: bold;">En attente</span>')
            elif status == 'cancelled':
                return format_html('<span style="color: red; font-weight: bold;">Annulé</span>')
            else:
                return obj.core_order.get_status_display()
        return 'N/A'
    status.short_description = 'Statut paiement'

    def payment_method(self, obj):
        if obj.core_order:
            return obj.core_order.get_payment_method_display()
        return 'N/A'
    payment_method.short_description = 'Méthode paiement'

@admin.register(ItemCommande)
class ItemCommandeAdmin(admin.ModelAdmin):
    list_display = ('id','commande','produit','quantite','prix_total')
    search_fields = ('commande__id','produit__name')
    list_filter = ('commande',)

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
