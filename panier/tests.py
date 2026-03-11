from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware

from core.models import Product, Category
from django.contrib.auth.models import User
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

	def test_currency_context_and_filter(self):
		# le context processor initialise la devise en session
		request = self._get_request_with_session()
		from panier.context_processors import panier as cp
		ctx = cp(request)
		self.assertIn('currency', ctx)
		self.assertEqual(ctx['currency'], 'XOF')
		self.assertEqual(request.session.get('currency'), 'XOF')

		# si on met un pays europeen dans la session, la devise bascule
		request.session['checkout_country'] = 'France'
		request.session.save()
		ctx2 = cp(request)
		self.assertEqual(ctx2['currency'], 'EUR')

        # et si l'utilisateur a un profil avec pays non-européen
        from core.models import Profil
        user = User.objects.create(username='u1')
        # le signal de création peut exister, on récupère le profil
        profil, _ = Profil.objects.get_or_create(user=user)
        profil.pays = 'Sénégal'
        profil.save()
        request.user = user
        ctx3 = cp(request)
        self.assertEqual(ctx3['currency'], 'XOF')

		# filtre de formatage
		from panier.templatetags.currency_filters import format_price
		self.assertEqual(format_price(1234, 'XOF'), '1 234 FCFA')
		self.assertEqual(format_price(1234.5, 'EUR'), '1 234.50 €')
		# accepte les string venant du panier
		self.assertEqual(format_price('5000', 'XOF'), '5 000 FCFA')

	def test_resume_panier_view_includes_currency(self):
		# client integration to ensure currency string is rendered
		session = self.client.session
		session['session_panier'] = { str(self.product.id): {'price': '1000', 'qte': 1} }
		session.save()
		resp = self.client.get('/panier/')
		self.assertEqual(resp.status_code, 200)
		# page should mention the currency (FCFA by default)
		self.assertIn('FCFA', resp.content.decode())
