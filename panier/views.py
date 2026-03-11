from django.shortcuts import render, get_object_or_404, redirect
from .panier import Panier
from core.models import Product
from core.models import ProductSize, Size
from core.forms import CheckoutForm
from django.http import JsonResponse
from django.urls import reverse 

# Create your views here.

def resume_panier(request):
    # Logique pour afficher le résumé du panier

    panier = Panier(request)
    products_panier = panier.get_prods()

    return render(request, "resume_panier.html", {"products_panier" : products_panier})

def ajouter_au_panier(request):
    # Logique pour ajouter un produit au panier
    panier = Panier(request)
    if request.method == 'POST' and request.POST.get('action') == 'post':
        product_id = int(request.POST.get('product_id'))
        qte = int(request.POST.get('qte', 1))
        size = request.POST.get('size') or None
        product = get_object_or_404(Product, id=product_id)
        # If product is a shoe, validate size and stock
        if getattr(product, 'is_shoe', False):
            if not size:
                return JsonResponse({'error': 'Veuillez sélectionner une taille.'}, status=400)
            try:
                size_id = int(size)
                ps = ProductSize.objects.get(product=product, size_id=size_id)
            except (ProductSize.DoesNotExist, ValueError):
                return JsonResponse({'error': 'Taille invalide.'}, status=400)

            if ps.stock < qte:
                return JsonResponse({'error': 'Stock insuffisant pour la taille sélectionnée.'}, status=400)

        panier.ajouter(product=product, qte=qte, size=size)

        # Retourner la quantité totale d'articles dans le panier
        cart_qte = panier.total_items
        return JsonResponse({'qty': cart_qte})

    

    
def retirer_du_panier(request):
    panier = Panier(request)
    #Logique pour retirer items du panier 
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        action = request.POST.get('action')

        if action == 'remove' and product_id:
            panier.remove(product_id)
            return JsonResponse({'qty': panier.total_items})

        if action == 'update' and product_id:
            qte = int(request.POST.get('qte', 1))
            # product_id may be a key like '12:38' when size is selected
            if ':' in str(product_id):
                panier.set_quantity(product_id, qte)
            else:
                product = get_object_or_404(Product, id=int(product_id))
                panier.set_quantity(product, qte)
            return JsonResponse({'qty': panier.total_items})

    return JsonResponse({'error': 'Invalid request'}, status=400)

def vider_panier(request):
    panier = Panier(request)
    if request.method == 'POST':
        panier.clear()
        return JsonResponse({'qty': 0})
    return JsonResponse({'error': 'Invalid request'}, status=400)


def checkout(request):
    panier = Panier(request)
    form = CheckoutForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            # Récupérer les données et les utiliser pour créer Order, etc.
            adresse = form.cleaned_data.get('adresse')
            ville = form.cleaned_data.get('ville')
            # TODO: créer l'Order et sauvegarder l'adresse si nécessaire
            return redirect(reverse('paiement_success'))

    # calculer total simple
    products = panier.get_prods()
    total = 0
    for p in products:
        try:
            total += float(getattr(p, 'price', 0)) * int(getattr(p, 'qte', 1))
        except Exception:
            pass

    # on fournit le total brut au template, le formatage se fait avec le filtre
    context = {
        'form': form,
        'products_panier': products,
        'panier': panier,
        'total': total,
        'prefill': {},
        'stripe_pub_key': ''
    }

    return render(request, 'paiement/checkout.html', context)
