from django.db import models
import datetime
from django.contrib.auth.models import User
from django.db.models.signals import post_save





# Création profil client

class Profil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_modified = models.DateTimeField(auto_now=True)
    telephone = models.CharField(max_length=20, blank=True)
    adresse = models.CharField(max_length=250, blank=True, null=True)
    ville = models.CharField(max_length=250, blank=True, null=True)
    pays = models.CharField(max_length=250, blank=True)
    codePostale = models.CharField(max_length=250, blank=True)
    ancien_panier = models.TextField(blank=True)

    def __str__(self):
        return self.user.username

#Créer un profil user par défaut
def creer_profil(sender, instance, created, **kwargs):
    if created : 
        user_profil = Profil(user=instance)
        user_profil.save()


post_save.connect(creer_profil, sender=User)


# Category model to classify products
class Category(models.Model):
    name = models.CharField(max_length=50)
    image = models.ImageField(upload_to='uploads/categories/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)


    def __str__(self):
        return self.name


class Meta :
    verbose_name_plural = "Categories"




# Customer model to represent users of the eButik platform
class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100)
    telephone = models.CharField(max_length=10, blank=True, null=True)
    password = models.CharField(max_length=100)
    address = models.TextField(blank=True, null=True)
    def __str__(self):
        return f"{self.first_name} {self.last_name}" 



# Product model to represent items available in the eButik
class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=0)
    stock = models.PositiveIntegerField()
    is_shoe = models.BooleanField(default=False)
    # sizes are linked through ProductSize when `is_shoe` is True
    sizes = models.ManyToManyField('Size', through='ProductSize', blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    image = models.ImageField(upload_to='uploads/product/', blank=True, null=True)
#for adding sale stuff
    is_on_sale = models.BooleanField(default=False)
    original_price = models.DecimalField(max_digits=10, decimal_places=0, blank=True, null=True)
    sale_price = models.DecimalField(max_digits=10, decimal_places=0, blank=True, null=True)    
    
    def __str__(self):
        return self.name


# Sizes and per-product size stock
class Size(models.Model):
    CATEGORY_CHOICES = (
        ('men', 'Homme'),
        ('women', 'Femme'),
        ('child', 'Enfant'),
        ('accessory', 'Accessoire'),
    )
    name = models.CharField(max_length=50)  # e.g. 38, 39, M, L
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='men')

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class ProductSize(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.ForeignKey(Size, on_delete=models.CASCADE)
    stock = models.PositiveIntegerField(default=0)
    extra_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)

    class Meta:
        unique_together = ('product', 'size')

    def __str__(self):
        return f"{self.product.name} - {self.size.name}"

# Order and OrderItem models to handle customer orders
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, through='OrderItem')
    order_date = models.DateTimeField(default=datetime.datetime.now)
    total_amount = models.DecimalField(max_digits=10, decimal_places=0)
    address = models.TextField(blank=True, null=True)

    # payment tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, blank=True, null=True)
    payment_reference = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"Order {self.id} - {self.customer}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    # chosen size for shoes (optional)
    size = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


# Shipping options
class ShippingOption(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    estimated_days = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} - {self.price}"