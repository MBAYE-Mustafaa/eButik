from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, Customer, Order, OrderItem, Profil, Size, ProductSize, ShippingOption
from django.contrib.auth.models import User

# Register your models here
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock', 'is_shoe')
    list_filter = ('category', 'is_shoe')
    search_fields = ('name',)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'telephone')
    search_fields = ('first_name','last_name','email')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'customer_email', 'order_date', 'total_amount', 'colored_payment_status', 'colored_delivery_status', 'payment_method')
    list_filter = ('status', 'delivery_status', 'payment_method', 'order_date')
    search_fields = ('customer__first_name','customer__last_name','customer__email','payment_reference', 'tracking_number', 'id')
    inlines = [OrderItemInline]
    readonly_fields = ('order_date','payment_reference', 'user')
    date_hierarchy = 'order_date'
    ordering = ('-order_date',)
    list_per_page = 50  # Show more items per page
    fieldsets = (
        (None, {
            'fields': ('user', 'customer','order_date','status','delivery_status','payment_method','payment_reference')
        }),
        ('Suivi de Livraison', {
            'fields': ('tracking_number', 'shipped_date', 'delivered_date'),
        }),
        ('Adresse & contact', {
            'fields': ('address',),
        }),
        ('Montants', {
            'fields': ('total_amount',),
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries"""
        qs = super().get_queryset(request)
        return qs.select_related('customer', 'user')

    def customer_email(self, obj):
        return obj.customer.email
    customer_email.short_description = 'Email client'
    customer_email.admin_order_field = 'customer__email'

    def colored_payment_status(self, obj):
        status = obj.status
        if status == 'paid':
            return format_html('<span style="color: green; font-weight: bold;">✓ Payé</span>')
        elif status == 'pending':
            return format_html('<span style="color: orange; font-weight: bold;">⏳ En attente</span>')
        elif status == 'cancelled':
            return format_html('<span style="color: red; font-weight: bold;">✕ Annulé</span>')
        else:
            return obj.get_status_display()
    colored_payment_status.short_description = 'Paiement'
    colored_payment_status.admin_order_field = 'status'
    
    def colored_delivery_status(self, obj):
        status = obj.delivery_status
        if status == 'pending':
            return format_html('<span style="color: #6c757d; font-weight: bold;">📦 En attente</span>')
        elif status == 'processing':
            return format_html('<span style="color: #0d6efd; font-weight: bold;">⚙️ En traitement</span>')
        elif status == 'shipped':
            return format_html('<span style="color: #6f42c1; font-weight: bold;">🚚 Expédiée</span>')
        elif status == 'delivered':
            return format_html('<span style="color: green; font-weight: bold;">✓ Livrée</span>')
        elif status == 'cancelled':
            return format_html('<span style="color: red; font-weight: bold;">✕ Annulée</span>')
        else:
            return obj.get_delivery_status_display()
    colored_delivery_status.short_description = 'Livraison'
    colored_delivery_status.admin_order_field = 'delivery_status'


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')


@admin.register(ProductSize)
class ProductSizeAdmin(admin.ModelAdmin):
    list_display = ('product', 'size', 'stock')


@admin.register(ShippingOption)
class ShippingOptionAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'estimated_days')

@admin.register(Profil)
class ProfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'telephone', 'ville', 'pays')
    readonly_fields = ('ancien_panier',)
    search_fields = ('user__username', 'telephone', 'ville')



#Import users infos

class ProfilInline(admin.StackedInline):
    model = Profil
    
class UserAdmin(admin.ModelAdmin):
    model= User
    field = ["username", "first_name", "last_name", "telephone", "adresse","ville", "pays", "codePostale"]
    inlines = [ProfilInline]

admin.site.unregister(User)

admin.site.register(User, UserAdmin)
    
