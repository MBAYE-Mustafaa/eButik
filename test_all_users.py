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
p = Product.objects.create(name=prod_name, price=1000, stock=1000, category=c)
print(f'Product created: {p.id}\n')

# Test 1: Anonymous user
print('=' * 60)
print('Test 1: ANONYMOUS USER')
print('=' * 60)
client = Client()
session = client.session
session['session_panier'] = {str(p.id): {'price': '1000', 'qte': 1}}
session.save()

data = {
    'first_name': 'John', 'last_name': 'Doe', 'email': 'john@test.com',
    'address_line': '123 Test', 'city': 'City', 'country': 'Country',
    'payment_method': 'card', 'payment_reference': 'ref1'
}
resp = client.post('/paiement/complete-order/', data)
if resp.status_code == 200:
    resp_data = json.loads(resp.content)
    order_id = resp_data['order_id']
    order = Order.objects.get(id=order_id)
    cmd = Commande.objects.get(core_order_id=order_id)
    print(f'✅ Order {order_id} created: {order.customer.first_name} {order.customer.last_name}')
    print(f'✅ Commande {cmd.id} created: {cmd.email_livraison}')
else:
    print(f'❌ Failed: {resp.status_code}')

# Test 2: User Alice (existing user)
print('\n' + '=' * 60)
print('Test 2: USER - Alice')
print('=' * 60)
try:
    alice = User.objects.get(username='Alice')
    print(f'Found existing user: Alice')
except:
    alice = User.objects.create_user(username='Alice', email='alice@test.com', password='pass123', first_name='Alice', last_name='Smith')
    print(f'Created new user: Alice')

client2 = Client()
client2.login(username='Alice', password='pass123')
session = client2.session
session['session_panier'] = {str(p.id): {'price': '1000', 'qte': 1}}
session.save()

data = {
    'first_name': 'Alice', 'last_name': 'Smith', 'email': 'alice@test.com',
    'address_line': '456 Test', 'city': 'City2', 'country': 'Country',
    'payment_method': 'card', 'payment_reference': 'ref2'
}
resp = client2.post('/paiement/complete-order/', data)
if resp.status_code == 200:
    resp_data = json.loads(resp.content)
    order_id = resp_data['order_id']
    order = Order.objects.get(id=order_id)
    cmd = Commande.objects.get(core_order_id=order_id)
    print(f'✅ Order {order_id} created: {order.customer.first_name} {order.customer.last_name}')
    print(f'✅ Commande {cmd.id} created: {cmd.email_livraison}')
    print(f'✅ User linked: {order.customer.user.username if order.customer.user else "None"}')
else:
    print(f'❌ Failed: {resp.status_code}')

# Test 3: User Bob (new user)
print('\n' + '=' * 60)
print('Test 3: USER - Bob (NEW)')
print('=' * 60)
bob = User.objects.create_user(username='Bob_' + str(int(time.time())), email='bob@test.com', password='pass123', first_name='Bob', last_name='Wilson')
print(f'Created user: {bob.username}')

client3 = Client()
client3.login(username=bob.username, password='pass123')
session = client3.session
session['session_panier'] = {str(p.id): {'price': '1000', 'qte': 1}}
session.save()

data = {
    'first_name': 'Bob', 'last_name': 'Wilson', 'email': 'bob@test.com',
    'address_line': '789 Test', 'city': 'City3', 'country': 'Country',
    'payment_method': 'card', 'payment_reference': 'ref3'
}
resp = client3.post('/paiement/complete-order/', data)
if resp.status_code == 200:
    resp_data = json.loads(resp.content)
    order_id = resp_data['order_id']
    order = Order.objects.get(id=order_id)
    cmd = Commande.objects.get(core_order_id=order_id)
    print(f'✅ Order {order_id} created: {order.customer.first_name} {order.customer.last_name}')
    print(f'✅ Commande {cmd.id} created: {cmd.email_livraison}')
    print(f'✅ User linked: {order.customer.user.username if order.customer.user else "None"}')
else:
    print(f'❌ Failed: {resp.status_code}')

# Summary
print('\n' + '=' * 60)
print('SUMMARY - All Orders and Commandes in DB:')
print('=' * 60)
all_orders = Order.objects.all().order_by('-id')[:10]
for order in all_orders:
    cmd = Commande.objects.filter(core_order_id=order.id).first()
    user_link = f' → User: {order.customer.user.username}' if order.customer.user else ' (anonymous)'
    cmd_exists = f'✅ Commande {cmd.id}' if cmd else '❌ NO COMMANDE'
    print(f'Order {order.id}: {order.customer.first_name} {order.customer.last_name}{user_link} | {cmd_exists}')
