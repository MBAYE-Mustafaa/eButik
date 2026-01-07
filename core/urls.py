from django.urls import path
from . import views
from panier.views import resume_panier, ajouter_au_panier, retirer_du_panier, vider_panier

urlpatterns = [
    path('', views.index, name='index'),  
    path('about/', views.about, name='about'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('register/', views.register_user, name='register'),
    path('update_user/', views.update_user, name='update_user'),
    path('update_info/', views.update_info, name='update_info'),
    path('product/<int:pk>/', views.product, name='product'),
    path('category/<str:foo>/', views.category, name='category'),
    path('category_resume/', views.category_resume, name='category_resume'),
    path('update_user/', views.update_user, name='update_user'),
    path('update_password/', views.update_password, name='update_password'),
    path('recherche/', views.recherche, name='recherche'),
]