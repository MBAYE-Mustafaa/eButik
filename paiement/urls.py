# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('create-payment-intent/', views.create_payment_intent, name='create_payment_intent'),
    path('complete-order/', views.complete_order, name='complete_order'),
    path('mobile-request/', views.mobile_request, name='mobile_request'),
    path('paiement_success/', views.paiement_success, name='paiement_success'),
    path('paiement_cancel/', views.cancel_view, name='paiement_cancel'),
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
]