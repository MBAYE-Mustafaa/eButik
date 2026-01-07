from django.urls import path
from . import views

urlpatterns = [
    path('', views.resume_panier, name='resume_panier'),
    path("ajouter/", views.ajouter_au_panier, name="ajouter_au_panier"),
    path('retirer/', views.retirer_du_panier, name='retirer_du_panier'),
    path('vider/', views.vider_panier, name='vider_panier'),
    path('checkout/', views.checkout, name='checkout'),
   
]