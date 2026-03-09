#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eButik.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from core.models import Category, Product, Order, Customer
from paiement.models import Commande
import time
import json

# Create product
cat_name = 'Cat_' + str(int(time.time()))
c = Category.objects.create(name=cat_name)
prod_name = 'Prod_' + str(int(time.time()))
p = Product.objects.create(name=prod_name, price=1000, stock=100, category=c)
print(f'Product created: {p.id}')

# Try to login and order as Momo
client = Client()
login_result = client.login(username='Momo', password='ebutik2026')
print(f'Login: {login_result}')

if login_result:
    # Create session cart
    session = client.session
    session['session_panier'] = {str(p.id): {'price': '1000', 'qte': 1}}
    session.save()
    
    data = {
        'first_name': 'Momo', 'last_name': 'Test', 'email': 'momo@test.com',
        'address_line': '123 Test', 'city': 'City', 'country': 'Country',
        'payment_method': 'card', 'payment_reference': 'momo_ref'
    }
    
    print(f'Posting to /paiement/complete-order/...')
    resp = client.post('/paiement/complete-order/', data)
    print(f'Response status: {resp.status_code}')
    print(f'Response body: {resp.content.decode()}')
    
    if resp.status_code == 200:
        resp_data = json.loads(resp.content)
        order_id = resp_data.get('order_id')
        print(f'\nOrder ID from response: {order_id}')
        
        # Check if order exists in DB
        order = Order.objects.filter(id=order_id).first()
        print(f'Order in DB: {order is not None}')
        if order:
            print(f'  ID: {order.id}')
            print(f'  Customer: {order.customer}')
            print(f'  Customer User: {order.customer.user if hasattr(order.customer, "user") else "N/A"}')
            print(f'  Total: {order.total_amount}')
        
        # Check if Commande exists
        cmd = Commande.objects.filter(core_order_id=order_id).first()
        print(f'\nCommande in DB: {cmd is not None}')
        if cmd:
            print(f'  Commande ID: {cmd.id}')
            print(f'  Email: {cmd.email_livraison}')
        else:
            print('  NO COMMANDE FOR THIS ORDER!')
            
        # List ALL Commandes for debugging
        print(f'\nAll Commandes (last 5):')
        for cmd in Commande.objects.all().order_by('-id')[:5]:
            print(f'  Commande {cmd.id}: core_order={cmd.core_order_id}, email={cmd.email_livraison}')
