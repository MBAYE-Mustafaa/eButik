from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from decimal import Decimal
from django.db import transaction

from panier.panier import Panier

import json

#Librairies de paiement simulées pour les tests


# Page affichée après un paiement (simulé)
def paiement_success(request):
    return render(request, 'paiement/paiement_success.html', {})


def checkout(request):
    # Cette vue affiche le formulaire de paiement. Pour simplifier les tests,
    # nous n'utilisons jamais la clé Stripe et activons toujours le mode fallback.
    stripe_pub = ''

    # Calculer le total du panier pour l'affichage
    panier = Panier(request)
    # rediriger si panier vide
    if not panier.total_items:
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, 'Votre panier est vide, ajoutez des produits avant de payer.')
        return redirect('resume_panier')
    total = Decimal('0')
    for v in panier.panier.values():
        price = Decimal(v.get('price', '0'))
        qte = int(v.get('qte', 1))
        total += price * qte

    # le total brut reste un Decimal, le formatage se fait en template
    total_display = None  # conservé pour compatibilité éventuelle

    # Pré-remplissage si utilisateur connecté
    prefill = {
        'first_name': '', 'last_name': '', 'email': '', 'phone': '',
        'address_line': '', 'city': '', 'postal_code': '', 'country': ''
    }

    # si le formulaire a été soumis, retenir le pays indiqué pour déterminer la devise
    if request.method == 'POST':
        cty = request.POST.get('country') or request.POST.get('pays')
        if cty:
            request.session['checkout_country'] = cty
    #si le client a un profil, on préremplit les champs
    if request.user.is_authenticated:
        try:
            profil = request.user.profil
        except Exception:
            profil = None

        prefill['first_name'] = request.user.first_name or ''
        prefill['last_name'] = request.user.last_name or ''
        prefill['email'] = request.user.email or ''
        if profil:
            prefill['phone'] = profil.telephone or ''
            prefill['address_line'] = profil.adresse or ''
            prefill['city'] = profil.ville or ''
            prefill['postal_code'] = profil.codePostale or ''
            prefill['country'] = profil.pays or ''

    # note: stripe_pub_key intentionally blank for fallback
    # on transmet total et laisse le template appliquer le filtre de devise
    return render(request, 'paiement/checkout.html', {
        'stripe_pub_key': stripe_pub,
        'total': total,
        'prefill': prefill,
    })


@require_POST
def create_payment_intent(request):
    """
    Pour Créer un PaymentIntent Stripe pour le montant du panier.
    Nécessite `STRIPE_SECRET_KEY` défini dans `settings.py` ou en variable d'env.
    Renvoie JSON: {clientSecret: ...}
    """
    stripe_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
    if not stripe_key:
        return JsonResponse({'error': 'Stripe non configuré'}, status=500)

    try:
        import stripe
    except Exception:
        return JsonResponse({'error': 'Le module stripe est manquant'}, status=500)

    panier = Panier(request)
    # calcul simple du total
    total = Decimal('0')
    for v in panier.panier.values():
        price = Decimal(v.get('price', '0'))
        qte = int(v.get('qte', 1))
        total += price * qte

    amount = int(total * 100)

    stripe.api_key = stripe_key
    try:
        intent = stripe.PaymentIntent.create(amount=amount, currency='eur')
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'clientSecret': intent.client_secret})


@require_POST
def mobile_request(request):
    """
    Point d'entrée minimal pour déclencher une demande Mobile Money.
    Ceci ne contacte pas de vrai fournisseur — à remplacer par un appel API réel (Orange Money, Wave, etc ou meme DunyaPay).
    Renvoie JSON {status: 'pending', reference: '...'}
    """
    provider = request.POST.get('mobile_provider')
    phone = request.POST.get('mobile_phone')
    if not phone:
        return JsonResponse({'error': 'Téléphone requis'}, status=400)

    import uuid
    ref = str(uuid.uuid4())

    # TODO: ici appeler l'API du fournisseur mobile money (Orange Money, Wave...)
    return JsonResponse({'status': 'pending', 'reference': ref, 'message': "Demande envoyée. Confirmez le paiement sur votre téléphone."})


@require_POST
def complete_order(request):
    """Crée l'Order à partir du panier et des informations client envoyées depuis le checkout.
    Attend : first_name, last_name, email, phone, address_line, city, postal_code, country, payment_method, payment_reference
    """
    try:
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        address_line = request.POST.get('address_line', '').strip()
        city = request.POST.get('city', '').strip()
        postal_code = request.POST.get('postal_code', '').strip()
        country = request.POST.get('country', '').strip()
        payment_method = request.POST.get('payment_method', '').strip()
        payment_reference = request.POST.get('payment_reference', '').strip()
    except Exception as exc:
        return JsonResponse({'error': f'paramètres invalides ({exc})'}, status=400)

    # validation minimale
    if not (first_name and last_name and email and address_line and city and country):
        return JsonResponse({'error': "Nom, email et adresse requis"}, status=400)

    try:
        from core.models import Customer, Order, OrderItem

        # If user is authenticated, get or create Customer by user, not by email
        if request.user.is_authenticated:
            customer, created = Customer.objects.get_or_create(user=request.user, defaults={
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'telephone': phone,
                'password': '',
                'address': f"{address_line}, {city}, {postal_code}, {country}"
            })
        else:
            # For anonymous users, get or create by email
            customer, created = Customer.objects.get_or_create(email=email, defaults={
                'first_name': first_name,
                'last_name': last_name,
                'telephone': phone,
                'password': '',
                'address': f"{address_line}, {city}, {postal_code}, {country}"
            })

        # Always update customer data (changes from user profile)
        customer.first_name = first_name
        customer.last_name = last_name
        customer.email = email
        customer.telephone = phone
        customer.address = f"{address_line}, {city}, {postal_code}, {country}"
        customer.save()

        # Ne pas proposer/forcer la création de compte ici — commande enregistrée même sans compte

        panier = Panier(request)
        products = panier.get_prods()
        if not products:
            return JsonResponse({'error': 'Panier vide'}, status=400)

        total = Decimal('0')
        from core.models import ProductSize
        for p in products:
            qte = int(p.qte)
            price = Decimal(p.price)
            extra = Decimal('0')
            if getattr(p, 'selected_size', None):
                try:
                    ps = ProductSize.objects.get(product=p, size_id=int(p.selected_size))
                    if ps.extra_price:
                        extra = Decimal(ps.extra_price)
                except Exception:
                    ps = None
            total += (price + extra) * qte

        # Crée la commande principale et sauvegarde dans l'app core,
        # ensuite duplique dans l'app paiement pour affichage séparé.
        with transaction.atomic():
            order = Order.objects.create(
                customer=customer,
                total_amount=total,
                address=f"{address_line}\n{city}\n{postal_code}\n{country}",
                status='paid',
                payment_method=payment_method,
                payment_reference=payment_reference
            )
            # Create order items
            for p in products:
                qte = int(p.qte)
                size_name = ''
                extra = Decimal('0')
                ps = None
                if getattr(p, 'selected_size', None):
                    try:
                        ps = ProductSize.objects.get(product=p, size_id=int(p.selected_size))
                        size_name = ps.size.name
                        if ps.extra_price:
                            extra = Decimal(ps.extra_price)
                    except Exception:
                        ps = None
                OrderItem.objects.create(order=order, product=p, quantity=qte, size=size_name)
                # decrement stock
                try:
                    if ps:
                        if ps.stock >= qte:
                            ps.stock = ps.stock - qte
                            ps.save()
                    else:
                        if p.stock >= qte:
                            p.stock = p.stock - qte
                            p.save()
                except Exception:
                    pass
            # conserver l'id dans la session pour affichage après redirection
            request.session['last_order_id'] = order.id

        # vider le panier
        panier.clear()

        # duplicate into paiement app OUTSIDE transaction, to never rollback main order
        try:
            from paiement.models import Commande as PaiementCommande, ItemCommande
            cmd = PaiementCommande.objects.create(
                core_order=order,
                user=request.user if request.user.is_authenticated else None,
                adresse_livraison=f"{address_line}, {city}, {postal_code}, {country}",
                email_livraison=email,
                telephone_livraison=phone,
                total=total
            )
            for p in products:
                try:
                    qte = int(p.qte)
                    price_unit = Decimal(p.price)
                    extra = Decimal('0')
                    if getattr(p, 'selected_size', None):
                        try:
                            ps = ProductSize.objects.get(product=p, size_id=int(p.selected_size))
                            if ps.extra_price:
                                extra = Decimal(ps.extra_price)
                        except Exception:
                            pass
                    ItemCommande.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        commande=cmd,
                        produit=p,
                        quantite=qte,
                        prix_unitaire=(price_unit + extra),
                        prix_total=(price_unit + extra) * qte
                    )
                except Exception:
                    # ignore individual item errors
                    pass
        except Exception:
            # if paiement models fail, log and continue
            import logging
            logging.exception("paiement duplication failed")

        return JsonResponse({'status': 'ok', 'order_id': order.id})
    except Exception as e:
        import traceback; traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
def stripe_webhook(request):
    """
    Gère les webhooks Stripe pour confirmer les paiements.
    Vérifie la signature et marque la commande comme payée si payment_intent.succeeded.
    """
    stripe_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
    if not stripe_key or not webhook_secret:
        return HttpResponse(status=500)

    try:
        import stripe
    except Exception:
        return HttpResponse(status=500)

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return HttpResponse(status=400)

    # Prendre action selon le type d'événement
    if event.type == 'payment_intent.succeeded':
        payment_intent = event.data.object
        payment_intent_id = payment_intent['id']

        #Trouver la commande correspondante et la marquer comme payée
        from core.models import Order
        try:
            order = Order.objects.get(payment_reference=payment_intent_id, status='pending')
            order.status = 'paid'
            order.save()
        except Order.DoesNotExist:
            pass  # Dans le cas où on ne trouve pas, on ignore (peut arriver si la commande a déjà été traitée ou si le webhook arrive avant la création de la commande)

    return HttpResponse(status=200)