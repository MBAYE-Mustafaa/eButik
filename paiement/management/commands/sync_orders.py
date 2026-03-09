from django.core.management.base import BaseCommand
from core.models import Order
from paiement.models import Commande, ItemCommande
from decimal import Decimal

class Command(BaseCommand):
    help = 'Synchronize core.Order objects into paiement.Commande for admin visibility'

    def handle(self, *args, **options):
        created = 0
        for order in Order.objects.all():
            # if a paiement record already exists for this core order, skip
            if Commande.objects.filter(core_order=order).exists():
                continue
            # otherwise, create a matching Commande
            cmd = Commande.objects.create(
                core_order=order,
                user=order.customer.user if hasattr(order.customer, 'user') else None,
                adresse_livraison=order.address.replace("\n", ", "),
                email_livraison=order.customer.email,
                telephone_livraison=order.customer.telephone or '',
                total=order.total_amount
            )
            # replicate items (OrderItem)
            for item in order.orderitem_set.all():
                try:
                    ItemCommande.objects.create(
                        user=order.customer.user if hasattr(order.customer, 'user') else None,
                        commande=cmd,
                        produit=item.product,
                        quantite=item.quantity,
                        prix_unitaire=item.price,
                        prix_total=item.price * Decimal(item.quantity)
                    )
                except Exception:
                    self.stdout.write(self.style.WARNING(f"failed to copy item {item.id}"))
            created += 1
        self.stdout.write(self.style.SUCCESS(f"synchronized {created} orders"))
