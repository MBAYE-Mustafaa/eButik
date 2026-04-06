"""
Management command pour mettre à jour les statuts de livraison des commandes.
Utile pour les tests et la gestion batch.

Usage:
  python manage.py update_order_status <order_id> shipped --tracking ABC123
  python manage.py update_order_status <order_id> delivered
  python manage.py update_order_status <order_id> processing
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from core.models import Order
from datetime import datetime


class Command(BaseCommand):
    help = 'Met à jour le statut de livraison d\'une commande'

    def add_arguments(self, parser):
        parser.add_argument('order_id', type=int, help='ID de la commande à mettre à jour')
        parser.add_argument('status', type=str, 
                          choices=['pending', 'processing', 'shipped', 'delivered', 'cancelled'],
                          help='Nouveau statut de livraison')
        parser.add_argument('--tracking', type=str, help='Numéro de suivi (pour shipped)')

    def handle(self, *args, **options):
        order_id = options['order_id']
        new_status = options['status']
        tracking = options.get('tracking')

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            raise CommandError(f'Commande #{order_id} introuvable')

        old_status = order.delivery_status
        order.delivery_status = new_status

        # Mettre à jour les dates selon le statut
        if new_status == 'shipped':
            order.shipped_date = timezone.now()
            if tracking:
                order.tracking_number = tracking
        elif new_status == 'delivered':
            order.delivered_date = timezone.now()
            if not order.shipped_date:
                order.shipped_date = timezone.now()

        order.save()

        status_display = {
            'pending': '📦 En attente',
            'processing': '⚙️ En traitement',
            'shipped': '🚚 Expédiée',
            'delivered': '✓ Livrée',
            'cancelled': '✕ Annulée'
        }

        self.stdout.write(self.style.SUCCESS(
            f'✓ Commande #{order_id} mise à jour: '
            f'{status_display.get(old_status, old_status)} → {status_display.get(new_status, new_status)}'
        ))

        if new_status == 'shipped' and tracking:
            self.stdout.write(self.style.SUCCESS(f'  N° de suivi: {tracking}'))

        if new_status == 'shipped':
            self.stdout.write(f'  Date d\'expédition: {order.shipped_date.strftime("%d/%m/%Y %H:%M")}')
        elif new_status == 'delivered':
            self.stdout.write(f'  Date de livraison: {order.delivered_date.strftime("%d/%m/%Y %H:%M")}')
