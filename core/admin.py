from django.contrib import admin
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
    list_display = ('first_name', 'last_name', 'email')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'order_date', 'total_amount', 'status')
    inlines = [OrderItemInline]


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
    
