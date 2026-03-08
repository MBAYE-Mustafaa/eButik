from django.test import TestCase
from core.models import Category, Product, Order
from decimal import Decimal
import json, types, sys


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
