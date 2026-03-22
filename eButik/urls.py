from django.contrib import admin
from django.urls import path, include
from . import settings
from django.conf.urls.static import static
from core.views import index, login_user, logout_user




urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('core/', include('core.urls')),
    path('logout/', logout_user, name='logout'),
    path('login/', login_user, name='login'),
    path('register/', include('core.urls')),
    path('about/', include('core.urls')),
    path('product/<int:pk>/', include('core.urls')),
    path('category/<str:foo>/', include('core.urls')),
    path('panier/', include('panier.urls')),
    path('paiement/', include('paiement.urls')),
    path('search/', include('core.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
