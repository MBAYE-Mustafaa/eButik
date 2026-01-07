from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware

from core.models import Product, Category
from panier.panier import Panier


class PanierTests(TestCase):
	def setUp(self):
		self.factory = RequestFactory()
		self.category = Category.objects.create(name='TestCat')
		self.product = Product.objects.create(
			name='TestProduct', price=10, stock=5, category=self.category
		)

	def _get_request_with_session(self):
		request = self.factory.get('/')
		middleware = SessionMiddleware(lambda req: None)
		middleware.process_request(request)
		request.session.save()
		return request

	def test_ajouter_increments_len_and_stores_price(self):
		request = self._get_request_with_session()
		panier = Panier(request)
		self.assertEqual(len(panier), 0)
		panier.ajouter(self.product)
		self.assertEqual(len(panier), 1)
		pid = str(self.product.id)
		self.assertIn(pid, panier.panier)
		self.assertEqual(panier.panier[pid]['price'], str(self.product.price))
