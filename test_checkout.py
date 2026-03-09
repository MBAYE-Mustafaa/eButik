import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eButik.settings')
import django
django.setup()

from django.test import Client
c = Client()

# Add to cart
resp = c.post('/panier/ajouter/', {'action': 'post', 'product_id': '1'})
print('Add to cart status:', resp.status_code)
print('Add to cart content:', resp.content.decode()[:500])

# Check cart
from panier.panier import Panier
panier = Panier(c)
print('Cart items:', len(panier.panier))

# Now, post to complete_order
data = {
    'first_name': 'Test',
    'last_name': 'User',
    'email': 'test@example.com',
    'phone': '123456789',
    'address_line': '123 Test St',
    'city': 'Test City',
    'postal_code': '12345',
    'country': 'Test Country',
    'payment_method': 'card',
    'payment_reference': 'test_ref'
}
resp2 = c.post('/paiement/complete-order/', data)
print('Complete order status:', resp2.status_code)
print('Complete order content:', resp2.content.decode()[:500])

from core.models import Order
print('Orders count:', Order.objects.count())
if Order.objects.exists():
    order = Order.objects.first()
    print('Order status:', order.status)
    print('Order payment_method:', order.payment_method)