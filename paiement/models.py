from django.db import models
from django.contrib.auth.models import User
from core.models import Product
from django.db.models.signals import post_save


# Create your models here.

try:
    from core.models import Profil

    class ProfilLivraison(Profil):
        class Meta:
            proxy = True
            verbose_name = 'Adresse de livraison'
            verbose_name_plural = 'Adresse de livraison'
except Exception:
    # If core isn't importable at import time (e.g. migrations in progress),
    # fail gracefully—admin registration can guard against this as well.
    pass

#Creation du modele Commande
class Commande(models.Model):
    # ForeignKey vers l'utilisateur qui a passe la commande
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    date_commande = models.DateTimeField(auto_now_add=True)
    adresse_livraison = models.TextField(max_length=250)
    email_livraison = models.EmailField(max_length=200)
    telephone_livraison = models.CharField(max_length=20)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Commande {self.id} de {self.user.username} - Total: {self.total}"


#Creation du modele itemCommande
class ItemCommande(models.Model):
    # ForeignKey vers la commande
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    commande = models.ForeignKey(Commande, related_name='items', on_delete=models.CASCADE, null=True, blank=True)
    produit = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    quantite = models.PositiveIntegerField(default=1)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    prix_total = models.DecimalField(max_digits=10, decimal_places=2)
    date_ajout = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantite} x {self.produit.name} pour la commande {self.commande.id}"
    

#Adresse de livraison par defaut pour les utilisateurs enregistres
def AdresseLivraisonParDefaut(sender, instance, created, **kwargs):
    if created and instance.user:
        user_adresse = ProfilLivraison(user=instance)
        user_adresse.save()

post_save.connect(AdresseLivraisonParDefaut, sender=Commande) 
