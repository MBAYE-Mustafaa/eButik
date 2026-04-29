# Guide d'implémentation des APIs Mobile Money pour eButik

## Vue d'ensemble

Ce guide explique comment implémenter et configurer les paiements mobile money (Wave, Orange Money, Lemfi) pour votre site e-commerce Django eButik, ciblant principalement les clients sénégalais.

## APIs Implémentées

### 1. Wave
- **Type**: API REST avec OAuth2
- **Documentation**: https://developer.wave.com/
- **Devise**: XOF (Franc CFA)
- **Pays**: Sénégal, Côte d'Ivoire, Mali

### 2. Orange Money
- **Type**: API REST avec OAuth2
- **Documentation**: https://developer.orange.com/
- **Devise**: XOF (Franc CFA)
- **Pays**: Sénégal, Mali, Côte d'Ivoire, Burkina Faso

### 3. Lemfi
- **Type**: API REST avec clé API
- **Documentation**: https://docs.lemfi.com/
- **Devise**: XOF (Franc CFA)
- **Pays**: Sénégal

## Configuration requise

### 1. Variables d'environnement

Créez un fichier `.env` à la racine de votre projet avec les variables suivantes :

```bash
# Wave
WAVE_CLIENT_ID=votre_client_id_wave
WAVE_CLIENT_SECRET=votre_client_secret_wave
WAVE_WEBHOOK_SECRET=votre_webhook_secret_wave

# Orange Money
ORANGE_MONEY_CLIENT_ID=votre_client_id_orange
ORANGE_MONEY_CLIENT_SECRET=votre_client_secret_orange
ORANGE_MONEY_MERCHANT_KEY=votre_merchant_key_orange
ORANGE_MONEY_WEBHOOK_SECRET=votre_webhook_secret_orange

# Lemfi
LEMFY_API_KEY=votre_api_key_lemfi
LEMFY_SECRET_KEY=votre_secret_key_lemfi
LEMFY_WEBHOOK_SECRET=votre_webhook_secret_lemfi
```

### 2. Installation des dépendances

Ajoutez `python-dotenv` à votre `requirements.txt` si ce n'est pas déjà fait :

```
python-dotenv==1.0.0
```

### 3. Chargement des variables d'environnement

Dans `eButik/settings.py`, ajoutez au début :

```python
import os
from dotenv import load_dotenv

load_dotenv()
```

## Architecture de l'implémentation

### Flux de paiement

1. **Sélection du moyen de paiement** : L'utilisateur choisit Wave, Orange Money ou Lemfi
2. **Initiation du paiement** : Envoi d'une requête à l'API du fournisseur
3. **Redirection** : L'utilisateur est redirigé vers l'app mobile ou l'interface web du fournisseur
4. **Confirmation** : Le fournisseur envoie un webhook pour confirmer le paiement
5. **Finalisation** : Mise à jour du statut de la commande

### Points d'entrée

- **Initiation** : `POST /paiement/mobile-request/`
- **Webhooks** :
  - Wave : `POST /paiement/wave-webhook/`
  - Orange : `POST /paiement/orange-webhook/`
  - Lemfi : `POST /paiement/lemfi-webhook/`

## Détails d'implémentation par fournisseur

### Wave

#### Configuration
```python
WAVE_CONFIG = {
    'api_base_url': 'https://api.wave.com/v1',
    'client_id': os.getenv('WAVE_CLIENT_ID'),
    'client_secret': os.getenv('WAVE_CLIENT_SECRET'),
    'webhook_secret': os.getenv('WAVE_WEBHOOK_SECRET'),
}
```

#### Initiation de paiement
```python
def initiate_wave_payment(amount, phone_number, order_id):
    # 1. Obtenir le token d'accès OAuth2
    token = get_wave_access_token()

    # 2. Créer la transaction
    payload = {
        'amount': amount,
        'currency': 'XOF',
        'recipient': phone_number,
        'reference': f'ORDER_{order_id}',
        'callback_url': 'https://votredomaine.com/paiement/wave-webhook/'
    }

    response = requests.post(
        f"{WAVE_CONFIG['api_base_url']}/payments",
        json=payload,
        headers={'Authorization': f'Bearer {token}'}
    )

    return response.json()
```

#### Webhook
```python
@csrf_exempt
def wave_webhook(request):
    # Vérifier la signature du webhook
    signature = request.headers.get('X-Wave-Signature')
    if not verify_wave_signature(request.body, signature):
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    data = json.loads(request.body)
    if data['status'] == 'completed':
        # Traiter le paiement réussi
        process_payment_success(data['reference'], data['amount'])

    return JsonResponse({'status': 'ok'})
```

### Orange Money

#### Configuration
```python
ORANGE_CONFIG = {
    'api_base_url': 'https://api.orange.com',
    'client_id': os.getenv('ORANGE_MONEY_CLIENT_ID'),
    'client_secret': os.getenv('ORANGE_MONEY_CLIENT_SECRET'),
    'merchant_key': os.getenv('ORANGE_MONEY_MERCHANT_KEY'),
}
```

#### Initiation de paiement
```python
def initiate_orange_payment(amount, phone_number, order_id):
    # 1. Obtenir le token OAuth2
    token = get_orange_access_token()

    # 2. Créer la transaction
    payload = {
        'amount': amount,
        'currency': 'XOF',
        'customer_msisdn': phone_number,
        'merchant_key': ORANGE_CONFIG['merchant_key'],
        'reference': f'ORDER_{order_id}',
        'callback_url': 'https://votredomaine.com/paiement/orange-webhook/'
    }

    response = requests.post(
        f"{ORANGE_CONFIG['api_base_url']}/om-money/v1/payments",
        json=payload,
        headers={'Authorization': f'Bearer {token}'}
    )

    return response.json()
```

### Lemfi

#### Configuration
```python
LEMFY_CONFIG = {
    'api_base_url': 'https://api.lemfi.com/v1',
    'api_key': os.getenv('LEMFY_API_KEY'),
    'secret_key': os.getenv('LEMFY_SECRET_KEY'),
}
```

#### Initiation de paiement
```python
def initiate_lemfi_payment(amount, phone_number, order_id):
    # Créer la signature HMAC
    timestamp = str(int(time.time()))
    payload = {
        'amount': amount,
        'currency': 'XOF',
        'phone': phone_number,
        'reference': f'ORDER_{order_id}',
        'callback_url': 'https://votredomaine.com/paiement/lemfi-webhook/',
        'timestamp': timestamp
    }

    signature = create_lemfi_signature(payload, LEMFY_CONFIG['secret_key'])

    headers = {
        'X-API-Key': LEMFY_CONFIG['api_key'],
        'X-Signature': signature,
        'X-Timestamp': timestamp
    }

    response = requests.post(
        f"{LEMFY_CONFIG['api_base_url']}/payments/initiate",
        json=payload,
        headers=headers
    )

    return response.json()
```

## Sécurité

### Vérification des webhooks

Chaque fournisseur utilise une méthode différente pour sécuriser les webhooks :

- **Wave** : Signature HMAC-SHA256 dans l'en-tête `X-Wave-Signature`
- **Orange Money** : Signature HMAC-SHA256 dans l'en-tête `X-Orange-Signature`
- **Lemfi** : Signature HMAC-SHA256 dans l'en-tête `X-Signature`

### Validation des données

- Vérifiez toujours le montant et la référence de la commande
- Validez le numéro de téléphone (format sénégalais)
- Stockez l'état des transactions pour éviter les doublons

## Gestion des erreurs

### Codes d'erreur courants

- **400 Bad Request** : Données invalides
- **401 Unauthorized** : Clés API invalides
- **402 Payment Required** : Solde insuffisant
- **409 Conflict** : Transaction déjà traitée

### Gestion des timeouts

- Implémentez des timeouts appropriés (30 secondes recommandées)
- Gérez les cas où l'utilisateur annule le paiement
- Prévoyez une logique de retry pour les erreurs temporaires

## Tests

### Environnements de test

- **Wave** : Utilisez l'environnement sandbox
- **Orange Money** : Utilisez les numéros de test fournis
- **Lemfi** : Utilisez l'API de test

### Tests unitaires

```python
def test_wave_payment_initiation():
    # Test de l'initiation d'un paiement Wave
    pass

def test_webhook_signature_verification():
    # Test de la vérification des signatures webhook
    pass
```

## Déploiement

### Configuration en production

1. **Domaines autorisés** : Ajoutez votre domaine aux applications API
2. **Certificats SSL** : Assurez-vous que les webhooks utilisent HTTPS
3. **Variables d'environnement** : Configurez les vraies clés API
4. **Logs** : Activez la journalisation des transactions

### Monitoring

- Surveillez les taux de succès des paiements
- Alertes sur les échecs répétés
- Vérification périodique des soldes API

## Support et dépannage

### Ressources utiles

- **Wave Developer Portal** : https://developer.wave.com/
- **Orange Developer Portal** : https://developer.orange.com/
- **Lemfi Documentation** : https://docs.lemfi.com/

### Problèmes courants

1. **Signature webhook invalide** : Vérifiez la clé secrète
2. **Timeout** : Augmentez le timeout ou vérifiez la connectivité
3. **Numéro invalide** : Validez le format des numéros sénégalais
4. **Solde insuffisant** : Gérez gracieusement cette erreur

## Évolutions futures

- Support d'autres pays d'Afrique de l'Ouest
- Intégration de nouveaux fournisseurs (MTN Mobile Money, etc.)
- Optimisation des performances avec cache Redis
- Analytics avancés sur les paiements