from django.urls import path
from . import views
from panier.views import resume_panier, ajouter_au_panier, retirer_du_panier, vider_panier

urlpatterns = [
    path('paiement_success/', views.paiement_success, name='paiement_success'),
    path('checkout/', views.checkout, name='checkout'),
  path('create-payment-intent/', views.create_payment_intent, name='create_payment_intent'),
  path('mobile-request/', views.mobile_request, name='mobile_request'),
    path('complete-order/', views.complete_order, name='complete_order'),
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
]
