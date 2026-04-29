from urllib import request
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from decimal import Decimal
from core.models import Product
from django.core.mail import send_mail
from django.db import transaction
from panier.panier import Panier
import json
import stripe 
import logging
import requests
import uuid
from datetime import datetime, timedelta

stripe.api_key = settings.STRIPE_SECRET_KEY

# Configuration de la devise
SITE_CURRENCY = 'XOF'  # Devise du site

# Configuration Mobile Money
MOBILE_MONEY_CONFIG = {
    'wave': {
        'api_url': 'https://api.wave.com/v1/checkout/sessions',
        'api_key': getattr(settings, 'WAVE_API_KEY', ''),
        'secret': getattr(settings, 'WAVE_SECRET_KEY', ''),
        'webhook_secret': getattr(settings, 'WAVE_WEBHOOK_SECRET', ''),
        'merchant_id': getattr(settings, 'WAVE_MERCHANT_ID', ''),
    },
    'orange': {
        'api_url': 'https://api.orange.com/orange-money-webpay/dev/v1/webpayment',
        'client_id': getattr(settings, 'ORANGE_CLIENT_ID', ''),
        'client_secret': getattr(settings, 'ORANGE_CLIENT_SECRET', ''),
        'merchant_key': getattr(settings, 'ORANGE_MERCHANT_KEY', ''),
        'webhook_secret': getattr(settings, 'ORANGE_WEBHOOK_SECRET', ''),
    },
    'lemfi': {
        'api_url': 'https://api.lemfi.com/v1/payments',
        'api_key': getattr(settings, 'LEMFY_API_KEY', ''),
        'secret': getattr(settings, 'LEMFY_SECRET_KEY', ''),
        'webhook_secret': getattr(settings, 'LEMFY_WEBHOOK_SECRET', ''),
        'merchant_id': getattr(settings, 'LEMFY_MERCHANT_ID', ''),
    }
}

# Page affichée après un paiement (simulé)
def paiement_success(request):
    return render(request, 'paiement/paiement_success.html', {})

# Page affichée après une annulation de paiement (simulé)
def cancel_view(request):
    request.session['panier'] = {}  # vider le panier en cas d'annulation
    return render(request, 'paiement/paiement_cancel.html', {})

def checkout(request):
    # Calculer le total du panier
    panier = Panier(request)

    # rediriger si panier vide
    if not panier.get_prods():
        from django.contrib import messages
        messages.error(request, 'Votre panier est vide, ajoutez des produits avant de payer.')
        return redirect('resume_panier')

    total = Decimal('0')

    for v in panier.panier.values():
        price = Decimal(v.get('price', '0'))
        qte = int(v.get('qte', 1))
        total += price * qte

    # Stocker le total dans la session pour create_payment_intent
    request.session['checkout_total'] = float(total)

    # Pré-remplissage utilisateur
    prefill = {
        'first_name': '',
        'last_name': '',
        'email': '',
        'phone': '',
        'address_line': '',
        'city': '',
        'postal_code': '',
        'country': ''
    }

    if request.user.is_authenticated:
        try:
            profil = request.user.profil
        except:
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

    products = panier.get_prods()

    context = {
        'products': products,
        'total': total,
        'stripe_pub_key': settings.STRIPE_PUBLISHABLE_KEY,
        'prefill': prefill,
        'currency': SITE_CURRENCY
    }

    return render(request, 'paiement/checkout.html', context)


@csrf_exempt
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
    if sig_header is None:
        return HttpResponse(status=400)
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
            order = Order.objects.filter(
              payment_reference=payment_intent_id,
              status='pending'
            ).first()

            if order:
              order.status = 'paid'
              order.save()
        except Order.DoesNotExist:
            pass  # Dans le cas où on ne trouve pas, on ignore (peut arriver si la commande a déjà été traitée ou si le webhook arrive avant la création de la commande)

    return HttpResponse(status=200)

def handle_successful_payment(session_id):
    """
    Fonction pour gérer les actions après un paiement réussi (ex: envoyer email de confirmation).
    Appelée depuis la vue de succès après redirection de Stripe.
    """
    from core.models import Order
    try:
        order = Order.objects.get(payment_reference=session_id)
        # Envoyer un email de confirmation (exemple simple)
        send_mail(
            'Votre commande a été bien reçue',
            f'Bonjour {order.customer.first_name},\n\nMerci pour votre commande #{order.id} ! Nous la traitons actuellement.',
            settings.DEFAULT_FROM_EMAIL,
            [order.customer.email],
            fail_silently=True,
        )
    except Order.DoesNotExist:
        pass  # Si on ne trouve pas la commande, on ignore

@csrf_exempt
@require_POST
def create_payment_intent(request):
    """
    Point d'entrée pour créer un PaymentIntent Stripe avec la devise XOF.
    Important: Le XOF n'a pas de centimes, donc 1 XOF = 1 unité Stripe.
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Récupérer le total depuis la session
        total = request.session.get('checkout_total')
        
        # Si pas dans la session, calculer depuis le panier
        if not total:
            panier = Panier(request)
            total = Decimal('0')
            for v in panier.panier.values():
                price = Decimal(v.get('price', '0'))
                qte = int(v.get('qte', 1))
                total += price * qte
            total = float(total)
        
        # Pour le XOF : pas de multiplication par 100 (pas de centimes)
        # Exemple: 15000 XOF = 15000 (pas 1500000)
        amount = int(total)
        
        # S'assurer que le montant est valide (minimum 50 XOF)
        if amount < 50:
            amount = 1000  # Montant minimum par défaut
        
        logger.info(f"Création PaymentIntent de {amount} XOF")
        
        # Créer le PaymentIntent avec la devise XOF
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='xof',  # Important: 'xof' en minuscules pour Stripe
            payment_method_types=['card'],
            metadata={
                'integration_check': 'accept_a_payment',
                'user_id': request.user.id if request.user.is_authenticated else 'guest',
                'original_amount': str(total),
                'currency': 'XOF'
            }
        )
        
        return JsonResponse({
            'clientSecret': intent.client_secret
        })
        
    except stripe.error.StripeError as e:
        logger.error(f"Erreur Stripe: {str(e)}")
        return JsonResponse({'error': f'Erreur Stripe: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f"Erreur générale: {str(e)}")
        return JsonResponse({'error': f'Erreur: {str(e)}'}, status=500)


@require_POST
def mobile_request(request):
    """
    Point d'entrée pour initier un paiement Mobile Money.
    Supporte Wave, Orange Money, et Lemfi.
    """
    provider = request.POST.get('mobile_provider')
    phone = request.POST.get('mobile_phone')
    amount = request.POST.get('amount')

    if not all([provider, phone, amount]):
        return JsonResponse({'error': 'Paramètres manquants'}, status=400)

    if provider not in ['wave', 'orange', 'lemfi']:
        return JsonResponse({'error': 'Fournisseur non supporté'}, status=400)

    try:
        amount = float(amount)
        if amount < 100:  # Minimum 100 XOF
            return JsonResponse({'error': 'Montant minimum: 100 XOF'}, status=400)
    except ValueError:
        return JsonResponse({'error': 'Montant invalide'}, status=400)

    # Générer une référence unique
    reference = f"MM-{uuid.uuid4().hex[:12].upper()}"

    # Stocker les infos dans la session
    request.session['mobile_payment'] = {
        'provider': provider,
        'phone': phone,
        'amount': amount,
        'reference': reference,
        'timestamp': datetime.now().isoformat()
    }

    # Appeler l'API du fournisseur
    try:
        if provider == 'wave':
            return initiate_wave_payment(request, phone, amount, reference)
        elif provider == 'orange':
            return initiate_orange_payment(request, phone, amount, reference)
        elif provider == 'lemfi':
            return initiate_lemfi_payment(request, phone, amount, reference)
    except Exception as e:
        logging.error(f"Erreur paiement {provider}: {str(e)}")
        return JsonResponse({'error': f'Erreur technique: {str(e)}'}, status=500)


def initiate_wave_payment(request, phone, amount, reference):
    """
    Initier un paiement Wave Money.
    """
    config = MOBILE_MONEY_CONFIG['wave']
    
    if not config['api_key']:
        return JsonResponse({'error': 'Configuration Wave manquante'}, status=500)

    headers = {
        'Authorization': f'Bearer {config["api_key"]}',
        'Content-Type': 'application/json'
    }

    payload = {
        'amount': str(int(amount)),  # Wave attend un string
        'currency': 'XOF',
        'client_reference': reference,
        'phone_number': phone,
        'webhook_url': f"{settings.SITE_URL}/paiement/wave-webhook/",
        'success_url': f"{settings.SITE_URL}/paiement_success/",
        'failure_url': f"{settings.SITE_URL}/paiement_cancel/",
        'merchant_id': config['merchant_id']
    }

    try:
        response = requests.post(config['api_url'], json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        return JsonResponse({
            'status': 'pending',
            'reference': reference,
            'wave_checkout_url': data.get('checkout_url'),
            'message': "Paiement Wave initié. Confirmez sur votre téléphone."
        })
    except requests.RequestException as e:
        logging.error(f"Erreur API Wave: {str(e)}")
        return JsonResponse({'error': 'Erreur de connexion Wave'}, status=500)


def initiate_orange_payment(request, phone, amount, reference):
    """
    Initier un paiement Orange Money.
    """
    config = MOBILE_MONEY_CONFIG['orange']
    
    if not config['client_id']:
        return JsonResponse({'error': 'Configuration Orange manquante'}, status=500)

    # D'abord obtenir le token d'accès
    token_payload = {
        'grant_type': 'client_credentials',
        'client_id': config['client_id'],
        'client_secret': config['client_secret']
    }
    
    try:
        token_response = requests.post(
            'https://api.orange.com/oauth/v3/token',
            data=token_payload,
            timeout=30
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data['access_token']
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'merchant_key': config['merchant_key'],
            'currency': 'XOF',
            'order_id': reference,
            'amount': str(int(amount)),
            'return_url': f"{settings.SITE_URL}/paiement_success/",
            'cancel_url': f"{settings.SITE_URL}/paiement_cancel/",
            'notif_url': f"{settings.SITE_URL}/paiement/orange-webhook/",
            'lang': 'fr',
            'reference': reference
        }
        
        payment_response = requests.post(config['api_url'], json=payload, headers=headers, timeout=30)
        payment_response.raise_for_status()
        
        data = payment_response.json()
        return JsonResponse({
            'status': 'pending',
            'reference': reference,
            'orange_payment_url': data.get('payment_url'),
            'message': "Paiement Orange Money initié. Confirmez sur votre téléphone."
        })
    except requests.RequestException as e:
        logging.error(f"Erreur API Orange: {str(e)}")
        return JsonResponse({'error': 'Erreur de connexion Orange Money'}, status=500)


def initiate_lemfi_payment(request, phone, amount, reference):
    """
    Initier un paiement Lemfi.
    """
    config = MOBILE_MONEY_CONFIG['lemfi']
    
    if not config['api_key']:
        return JsonResponse({'error': 'Configuration Lemfi manquante'}, status=500)

    headers = {
        'Authorization': f'Bearer {config["api_key"]}',
        'Content-Type': 'application/json'
    }

    payload = {
        'amount': int(amount),
        'currency': 'XOF',
        'phone_number': phone,
        'reference': reference,
        'description': f'Paiement commande eButik #{reference}',
        'webhook_url': f"{settings.SITE_URL}/paiement/lemfi-webhook/",
        'success_url': f"{settings.SITE_URL}/paiement_success/",
        'cancel_url': f"{settings.SITE_URL}/paiement_cancel/",
        'merchant_id': config['merchant_id']
    }

    try:
        response = requests.post(config['api_url'], json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        return JsonResponse({
            'status': 'pending',
            'reference': reference,
            'lemfi_checkout_url': data.get('checkout_url'),
            'message': "Paiement Lemfi initié. Confirmez sur votre téléphone."
        })
    except requests.RequestException as e:
        logging.error(f"Erreur API Lemfi: {str(e)}")
        return JsonResponse({'error': 'Erreur de connexion Lemfi'}, status=500)


@csrf_exempt
@require_POST
def wave_webhook(request):
    """
    Webhook pour confirmer les paiements Wave.
    """
    config = MOBILE_MONEY_CONFIG['wave']
    
    # Vérifier la signature du webhook
    signature = request.META.get('HTTP_X_WAVE_SIGNATURE')
    if not signature:
        return HttpResponse(status=400)
    
    # Calculer la signature attendue (simplifié - à adapter selon la doc Wave)
    expected_signature = config['webhook_secret']
    if signature != expected_signature:
        return HttpResponse(status=401)
    
    try:
        data = json.loads(request.body)
        
        if data.get('status') == 'successful':
            reference = data.get('client_reference')
            amount = data.get('amount')
            
            # Traiter le paiement réussi
            success = process_mobile_payment_success(reference, 'wave', amount)
            if success:
                return HttpResponse(status=200)
        
        return HttpResponse(status=400)
    except Exception as e:
        logging.error(f"Erreur webhook Wave: {str(e)}")
        return HttpResponse(status=500)


@csrf_exempt
@require_POST
def orange_webhook(request):
    """
    Webhook pour confirmer les paiements Orange Money.
    """
    config = MOBILE_MONEY_CONFIG['orange']
    
    # Vérifier la signature du webhook
    signature = request.META.get('HTTP_X_ORANGE_SIGNATURE')
    if not signature:
        return HttpResponse(status=400)
    
    try:
        data = json.loads(request.body)
        
        if data.get('status') == 'SUCCESS':
            reference = data.get('order_id')
            amount = data.get('amount')
            
            # Traiter le paiement réussi
            success = process_mobile_payment_success(reference, 'orange', amount)
            if success:
                return HttpResponse(status=200)
        
        return HttpResponse(status=400)
    except Exception as e:
        logging.error(f"Erreur webhook Orange: {str(e)}")
        return HttpResponse(status=500)


@csrf_exempt
@require_POST
def lemfi_webhook(request):
    """
    Webhook pour confirmer les paiements Lemfi.
    """
    config = MOBILE_MONEY_CONFIG['lemfi']
    
    # Vérifier la signature du webhook
    signature = request.META.get('HTTP_X_LEMFI_SIGNATURE')
    if not signature:
        return HttpResponse(status=400)
    
    try:
        data = json.loads(request.body)
        
        if data.get('status') == 'completed':
            reference = data.get('reference')
            amount = data.get('amount')
            
            # Traiter le paiement réussi
            success = process_mobile_payment_success(reference, 'lemfi', amount)
            if success:
                return HttpResponse(status=200)
        
        return HttpResponse(status=400)
    except Exception as e:
        logging.error(f"Erreur webhook Lemfi: {str(e)}")
        return HttpResponse(status=500)


def process_mobile_payment_success(reference, provider, amount):
    """
    Traiter un paiement mobile money réussi.
    """
    try:
        from core.models import Order
        
        # Trouver la commande par référence
        order = Order.objects.filter(
            payment_reference=reference,
            status='pending'
        ).first()
        
        if order:
            order.status = 'paid'
            order.payment_method = f'mobile_{provider}'
            order.save()
            
            # Envoyer email de confirmation
            send_mail(
                'Votre commande a été bien reçue',
                f'Bonjour {order.customer.first_name},\n\nMerci pour votre commande #{order.id} ! Paiement {provider.upper()} confirmé.\nNous la traitons actuellement.',
                settings.DEFAULT_FROM_EMAIL,
                [order.customer.email],
                fail_silently=True,
            )
            
            return True
        
        return False
    except Exception as e:
        logging.error(f"Erreur traitement paiement {provider}: {str(e)}")
        return False


@require_POST
def complete_order(request):
    """Crée l'Order à partir du panier et des informations client envoyées depuis le checkout."""
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

        # Si l'utilisateur est authentifié, récupérer ou créer le Customer par user
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
            # Pour les utilisateurs anonymes, récupérer ou créer par email
            customer, created = Customer.objects.get_or_create(email=email, defaults={
                'first_name': first_name,
                'last_name': last_name,
                'telephone': phone,
                'password': '',
                'address': f"{address_line}, {city}, {postal_code}, {country}"
            })

        # Mettre à jour les données du client
        customer.first_name = first_name
        customer.last_name = last_name
        customer.email = email
        customer.telephone = phone
        customer.address = f"{address_line}, {city}, {postal_code}, {country}"
        customer.save()

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

        # Crée la commande principale
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                customer=customer,
                total_amount=total,
                address=f"{address_line}\n{city}\n{postal_code}\n{country}",
                status='paid',
                payment_method=payment_method,
                payment_reference=payment_reference
            )
            # Créer les items de commande
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
                # Décrémenter le stock
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
            # conserver l'id dans la session
            request.session['last_order_id'] = order.id

        # vider le panier
        panier.clear()
        
        # Nettoyer la session
        if 'checkout_total' in request.session:
            del request.session['checkout_total']

        # Dupliquer dans l'app paiement
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
                    pass
        except Exception:
            import logging
            logging.exception("paiement duplication failed")

        return JsonResponse({'status': 'ok', 'order_id': order.id})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)