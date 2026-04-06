from django.shortcuts import render, redirect
from .models import Product, Category, Profil
from django.db.models import Count, Q
import json
from panier.panier import Panier
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from .forms import PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .forms import SignUpForm, UpdateUserForm, UserInfoForm
from django import forms

def recherche(request):
    query = request.GET.get('q', '') or ''
    query = query.strip()
    results = Product.objects.none()
    if query:
        #Pour chaque mot dans la requête, chercher dans le nom, la description et la catégorie
        tokens = [t for t in query.split() if t]
        q_objects = Q()
        for token in tokens:
            q_objects |= (Q(name__icontains=token) | Q(description__icontains=token) | Q(category__name__icontains=token))
        results = Product.objects.filter(q_objects).distinct()
    return render(request, 'recherche.html', {'query': query, 'results': results})


def update_info(request):
    if not request.user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour modifier vos infos.")
        return redirect('login')

    user = request.user

    # ensure profil exists
    try:
        profil = user.profil
    except Exception:
        from .models import Profil
        profil, _ = Profil.objects.get_or_create(user=user)

    if request.method == 'POST':
        user_form = UpdateUserForm(request.POST, instance=user)
        profile_form = UserInfoForm(request.POST, instance=profil)
        if user_form.is_valid() and profile_form.is_valid():
            # Get customer before saving to use old email
            old_email = user.email
            user_form.save()
            profile_form.save()
            # Update Customer if exists linked to user or by old email
            try:
                from .models import Customer
                customer = getattr(user, 'customer', None)
                if not customer:
                    customer = Customer.objects.filter(email=old_email).first()
                if customer:
                    customer.first_name = user.first_name
                    customer.last_name = user.last_name
                    customer.telephone = profil.telephone
                    customer.address = f"{profil.adresse}, {profil.ville}, {profil.codePostale}, {profil.pays}"
                    customer.email = user.email
                    customer.save()
            except Exception:
                pass  # Ignore if Customer model not available or error
            messages.success(request, "Infos modifiées avec succès !")
            return redirect('update_info')
    else:
        user_form = UpdateUserForm(instance=user)
        profile_form = UserInfoForm(instance=profil)

    return render(request, "update_info.html", {"user_form": user_form, "profile_form": profile_form})

def update_user(request):
    if not request.user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour modifier votre profil.")
        return redirect('login')

    user = request.user
    if request.method == 'POST':
        user_form = UpdateUserForm(request.POST, instance=user)
        if user_form.is_valid():
            user_form.save()
            messages.success(request, "Profil modifié avec succès !")
            return redirect('index')
    else:
        user_form = UpdateUserForm(instance=user)

    return render(request, "update_user.html", {"user_form": user_form})


def update_password(request):
    if not request.user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour changer le mot de passe.")
        return redirect('login')

    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Important to keep the user logged in after password change
            update_session_auth_hash(request, user)
            messages.success(request, 'Mot de passe mis à jour avec succès.')
            return redirect('update_user')
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'update_password.html', {'form': form})


def category_resume(request):
    # Récupère les catégories avec le nombre de produits
    categories_qs = Category.objects.annotate(product_count=Count('products'))

    categories = []
    for c in categories_qs:
        # Prefer category image if present, otherwise pick first product image
        image = None
        if getattr(c, 'image', None):
            try:
                image = c.image.url
            except Exception:
                image = None
        if not image:
            first_prod = c.products.first()
            if first_prod and getattr(first_prod, 'image', None):
                try:
                    image = first_prod.image.url
                except Exception:
                    image = None

        categories.append({
            'name': c.name,
            'description': c.description,
            'product_count': c.product_count,
            'image': image,
        })

    return render(request, 'category_resume.html', {'categories': categories})



def category(request, foo):
   
    foo = foo.replace('-', ' ')
    products = Product.objects.filter(category__name__iexact=foo)
    category = products.first().category if products.exists() else None
    return render(request, 'category.html', {'products': products, 'category': category})


def product(request, pk):
    product = Product.objects.get(id=pk)
    # préparer les tailles disponibles si le produit est une chaussure
    product_sizes = []
    try:
        if getattr(product, 'is_shoe', False):
            from .models import ProductSize
            sizes_qs = ProductSize.objects.filter(product=product).select_related('size')
            product_sizes = [{'id': ps.size.id, 'name': ps.size.name, 'stock': ps.stock} for ps in sizes_qs]
    except Exception:
        product_sizes = []

    return render(request, 'product.html', {'product': product, 'product_sizes': product_sizes})

# Create your views here.
def index(request):
    products = Product.objects.all()
    return render(request, 'index.html', {'products': products})

def about(request):
    return render(request, 'about.html')

def login_user(request):
    # Logic for user login
    if request.method == 'POST':
        username = request.POST['username'] 
        password = request.POST['password']
        
      
        user = authenticate(request, username=username, password=password)
    
        if user is not None:
            login(request, user)
            # Recupérer le panier sauvegardé dans le profil et le fusionner avec le panier de session
            try:
                profil, _ = Profil.objects.get_or_create(user=user)
                saved = {}
                if profil.ancien_panier:
                    try:
                        saved = json.loads(profil.ancien_panier)
                    except Exception:
                        saved = {}

                # recuperer le panier de session et y ajouter les items sauvegardés
                panier = Panier(request)
                for pid, data in (saved or {}).items():
                    try:
                        qte = int(data.get('qte', 1))
                    except Exception:
                        qte = 1
                    # add product if exists
                    try:
                        # pid may be '12' or '12:38' (with size)
                        raw_pid = str(pid).split(':')[0]
                        prod = Product.objects.get(id=int(raw_pid))
                        # extract size if present
                        size = None
                        if ':' in str(pid):
                            size = str(pid).split(':', 1)[1]
                        panier.ajouter(prod, qte=qte, size=size)
                    except Product.DoesNotExist:
                        continue

                # Supprimer le panier sauvegardé dans le profil après fusion
                profil.ancien_panier = ''
                profil.save()

            except Exception:
                # pour toute erreur, on ignore la restauration du panier
                pass

            messages.success(request, "Connexion réussie.")
            return redirect('index')
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    return render(request, 'login.html')

def logout_user(request):
    # Logic for user logout
    # avant de déconnecter, sauvegarder le panier de session dans le profil
    try:
        if request.user.is_authenticated:
            profil, _ = Profil.objects.get_or_create(user=request.user)
            session_panier = request.session.get('session_panier', {})
            try:
                profil.ancien_panier = json.dumps(session_panier)
                profil.save()
            except Exception:
                # ignore serialization errors
                pass
    except Exception:
        pass

    logout(request)
    messages.info(request, "Vous avez été déconnecté avec succès.")
    return redirect('index')

def register_user(request):
    form = SignUpForm()
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']
            
            password = form.cleaned_data['password1']
            user = authenticate(username=username, password=password)
          
            if user is not None:
                login(request, user)
            messages.success(request, "Inscription réussie ! Veuillez compléter vos informations personnelles, s'il vous plaît.")
            return redirect('update_info')
        
        else:
            messages.error(request, "Oops, erreur lors de l'inscription. Veuillez vérifier les informations fournies.")
            return render(request, 'register.html', {'form': form})
    else:
            return render(request, 'register.html', {'form': form})


def order_history(request):
    """Affiche l'historique des commandes de l'utilisateur connecté."""
    if not request.user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour voir votre historique de commandes.")
        return redirect('login')
    
    from .models import Order
    # Récupérer toutes les commandes de l'utilisateur
    orders = Order.objects.filter(user=request.user).prefetch_related('orderitem_set__product')
    
    context = {
        'orders': orders,
        'payment_status_display': dict(Order.PAYMENT_STATUS),
        'delivery_status_display': dict(Order.DELIVERY_STATUS),
    }
    
    return render(request, 'order_history.html', context)


def order_detail(request, order_id):
    """Affiche les détails d'une commande spécifique."""
    if not request.user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour voir vos commandes.")
        return redirect('login')
    
    from .models import Order
    from django.shortcuts import get_object_or_404
    
    # Récupérer la commande et vérifier qu'elle appartient à l'utilisateur
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
        'payment_status_display': dict(Order.PAYMENT_STATUS),
        'delivery_status_display': dict(Order.DELIVERY_STATUS),
        'order_items': order.orderitem_set.all().select_related('product'),
    }
    
    return render(request, 'order_detail.html', context)
