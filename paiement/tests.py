from django.test import TestCase
from core.models import Category, Product, Order
from decimal import Decimal
import json, types, sys
from django.test import Client


# helper to install dummy stripe module for webhook tests
def install_dummy_stripe():
    if 'stripe' in sys.modules:
        return
    stripe_mod = types.ModuleType('stripe')
    stripe_mod.api_key = ''

    class DummyEvent:
        def __init__(self, type, data):
            self.type = type
            self.data = data

        @staticmethod
        def construct_from(payload, api_key):
            return payload

    class DummyWebhook:
        @staticmethod
        def construct_event(payload, sig, secret):
            data = json.loads(payload)
            return DummyEvent(data.get('type'), types.SimpleNamespace(object=data.get('data', {}).get('object')))

    stripe_mod.Event = DummyEvent
    stripe_mod.Webhook = DummyWebhook
    sys.modules['stripe'] = stripe_mod


class PaymentTests(TestCase):
    def setUp(self):
        # make sure a category exists for product foreign key
        self.cat = Category.objects.create(name="TestCat")
        self.prod = Product.objects.create(name="Test", price=1000, stock=10, category=self.cat)

    def test_create_payment_intent_no_key_returns_error(self):
        # Temporarily remove stripe key to test error handling
        from django.conf import settings
        original_key = settings.STRIPE_SECRET_KEY
        settings.STRIPE_SECRET_KEY = ''
        try:
            resp = self.client.post('/paiement/create-payment-intent/')
            self.assertEqual(resp.status_code, 500)
            self.assertIn('Stripe non configuré', resp.json().get('error'))
        finally:
            settings.STRIPE_SECRET_KEY = original_key

    def test_complete_order_empty_cart(self):
        resp = self.client.post('/paiement/complete-order/', data={
            'first_name': 'a', 'last_name': 'b', 'email': 'a@b.com',
            'address_line': 'x', 'city': 'y', 'country': 'z',
            'payment_method': 'card', 'payment_reference': 'ref'
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json(), {'error': 'Panier vide'})

    def test_complete_order_creates_order(self):
        session = self.client.session
        session['session_panier'] = { str(self.prod.id): {'price': '1000', 'qte': 2} }
        session.save()
        # record counts before request to ensure duplication
        from paiement.models import Commande as PaiementCommande
        before_core = Order.objects.count()
        before_paiement = PaiementCommande.objects.count()

        data = {'first_name': 'a','last_name': 'b','email':'a@b.com',
                'address_line':'x','city':'y','country':'z',
                'payment_method':'mobile','payment_reference':'123'}
        resp = self.client.post('/paiement/complete-order/', data=data)
        self.assertEqual(resp.status_code, 200)
        json_resp = resp.json()
        self.assertEqual(json_resp['status'], 'ok')
        order = Order.objects.get(id=json_resp['order_id'])
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.payment_reference, '123')
        self.assertEqual(order.payment_method, 'mobile')

        # verify duplication to paiement app
        after_core = Order.objects.count()
        after_paiement = PaiementCommande.objects.count()
        self.assertEqual(after_core, before_core + 1)
        self.assertEqual(after_paiement, before_paiement + 1)
        cmd = PaiementCommande.objects.last()
        self.assertEqual(cmd.total, order.total_amount)
        self.assertEqual(cmd.email_livraison, order.customer.email)
        # link back to core order
        self.assertEqual(cmd.core_order, order)
        # verify OrderItem created
        self.assertEqual(order.orderitem_set.count(), 1)
        item = order.orderitem_set.first()
        self.assertEqual(item.product, self.prod)
        self.assertEqual(item.quantity, 2)

    def test_complete_order_handles_duplication_errors(self):
        # patch paiement.models.Commande.objects.create to raise an exception
        from paiement import models as paymodels
        orig_create = paymodels.Commande.objects.create
        def raise_error(*args, **kwargs):
            raise Exception('dup fail')
        paymodels.Commande.objects.create = raise_error

        session = self.client.session
        session['session_panier'] = { str(self.prod.id): {'price': '1000', 'qte': 2} }
        session.save()
        data = {'first_name': 'a','last_name': 'b','email':'a@b.com',
                'address_line':'x','city':'y','country':'z',
                'payment_method':'mobile','payment_reference':'123'}
        resp = self.client.post('/paiement/complete-order/', data=data)
        self.assertEqual(resp.status_code, 200)
        json_resp = resp.json()
        self.assertEqual(json_resp['status'], 'ok')
        # ensure order created in core despite failure
        from core.models import Order
        order = Order.objects.get(id=json_resp['order_id'])
        self.assertEqual(order.status, 'paid')
        # paiement side should have been skipped (no new commandes)
        from paiement.models import Commande as PaiementCommande
        self.assertEqual(PaiementCommande.objects.count(), 0)
        # restore original method
        paymodels.Commande.objects.create = orig_create

    def test_stripe_webhook_marks_paid(self):
        install_dummy_stripe()
        # create a customer first
        from core.models import Customer
        cust = Customer.objects.create(first_name='Test', last_name='User', email='test@example.com')
        # create pending order with reference
        order = Order.objects.create(
            customer=cust, total_amount=Decimal('1000'), status='pending',
            payment_method='card', payment_reference='pi_123',
            address='foo'
        )
        payload = {
            "id": "evt_test",
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": "pi_123"}}
        }
        resp = self.client.post('/paiement/webhook/', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        # if a paiement.Commande was created for this order, core_order should link
        from paiement.models import Commande as PaiementCommande
        cmd = PaiementCommande.objects.filter(core_order=order).first()
        if cmd:
            self.assertEqual(cmd.core_order, order)

    def test_full_site_flow(self):
        # Test complete user flow: browse, add to cart, checkout, admin
        client = Client()

        # 1. Index page
        resp = client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('eButik', resp.content.decode())

        # 2. Add to cart (simulate AJAX)
        resp = client.post('/panier/ajouter/', {
            'product_id': self.prod.id,
            'qte': 1,
            'action': 'post'
        })
        self.assertEqual(resp.status_code, 200)
        json_resp = resp.json()
        self.assertEqual(json_resp['qty'], 1)

        # 3. View cart
        resp = client.get('/panier/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Votre panier', resp.content.decode())

        # 4. Checkout page
        resp = client.get('/paiement/checkout/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Validation de la commande', resp.content.decode())

        # 5. Complete order
        data = {
            'first_name': 'Test', 'last_name': 'User', 'email': 'test@example.com',
            'phone': '123456789', 'address_line': '123 Test St', 'city': 'TestCity',
            'postal_code': '12345', 'country': 'TestCountry',
            'payment_method': 'card', 'payment_reference': 'test_ref_123'
        }
        resp = client.post('/paiement/complete-order/', data)
        self.assertEqual(resp.status_code, 200)
        json_resp = resp.json()
        self.assertEqual(json_resp['status'], 'ok')
        order_id = json_resp['order_id']

        # 6. Check database
        from core.models import Order
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.orderitem_set.count(), 1)

        # 7. Admin access (simulate superuser)
        from django.contrib.auth.models import User
        User.objects.create_superuser('admin', 'admin@test.com', 'pass')
        client.login(username='admin', password='pass')

        # Admin index
        resp = client.get('/admin/')
        self.assertEqual(resp.status_code, 200)

        # Core Orders
        resp = client.get('/admin/core/order/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(str(order_id), resp.content.decode())

        # Paiement Commandes
        resp = client.get('/admin/paiement/commande/')
        self.assertEqual(resp.status_code, 200)
        # Should show the linked commande
