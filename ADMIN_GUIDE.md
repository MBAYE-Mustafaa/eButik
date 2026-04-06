# 📖 Guide Administrateur - Suivi de Commandes

## 🎯 Objectif
Ce guide explique comment utiliser le nouveau système de suivi de commandes pour gérer les statuts de livraison et offrir une meilleure expérience client.

---

## 🔐 Accès à l'Interface d'Administration

1. Rendez-vous sur `/admin/`
2. Connectez-vous avec votre compte administrateur
3. Dans la section "Core", cliquez sur "Orders"

---

## 📊 Tableau des Commandes

L'interface affiche un tableau avec:
- **N° Commande** - Identifiant unique
- **Email Client** - Email de contact du client
- **Date** - Date de la commande
- **Montant** - Total en XOF
- **Paiement** - Statut du paiement (vert=payé, orange=en attente)
- **Livraison** - Statut de livraison (avec emojis)
- **Méthode Paiement** - Type de paiement utilisé

### 🔍 Filtres Disponibles
- Filtrer par statut de paiement (Payé, En attente, Annulé)
- Filtrer par statut de livraison (En attente, En traitement, Expédiée, Livrée, Annulée)
- Filtrer par méthode de paiement
- Filtrer par date (calendrier interactif)

### 🔎 Recherche
Recherchez rapidement par:
- Prénom du client
- Nom du client
- Email du client
- Numéro de suivi
- Référence de paiement
- N° de commande

---

## ✏️ Mettre à Jour une Commande

### 1. Cliquer sur la Commande
Cliquez sur le N° de commande pour ouvrir les détails.

### 2. Sections Éditable
Vous verrez plusieurs sections:

#### 📋 Informations de Base
- **Utilisateur** (lecture seule) - Compte Django du client
- **Client** (lecture seule) - Infos détaillées du client
- **Date** (lecture seule) - Date de création
- **Statut Paiement** - Payé / En attente / Annulé
- **Statut Livraison** - À mettre à jour
- **Méthode Paiement** (lecture seule)
- **Référence Paiement** (lecture seule)

#### 🚚 Suivi de Livraison (À REMPLIR)
- **N° de Suivi** - Entrez le tracking number (ex: DHL123456XYZ)
- **Date d'Expédition** - Sélectionnez la date
- **Date de Livraison** - Remplissez une fois livrée

#### 📍 Adresse de Livraison (lecture seule)
L'adresse complète de livraison du client.

#### 💰 Montants (lecture seule)
Le total de la commande.

### 3. Flux Recommandé

**Étape 1: Réception du Paiement**
```
Statut Paiement: [En attente] → [Payé]
```

**Étape 2: En Préparation**
```
Statut Livraison: [En attente] → [En traitement]
```

**Étape 3: Colis Prêt à Expédier**
```
Statut Livraison: [En traitement] → [Expédiée]
N° de Suivi: [Entrez le numéro]
Date d'Expédition: [Entrez la date]
```

**Étape 4: Commande Livrée**
```
Statut Livraison: [Expédiée] → [Livrée]
Date de Livraison: [Entrez la date]
```

### 4. Sauvegarder
Cliquez sur le bouton **"Enregistrer"** en bas de la page.

---

## 💻 Utilisation depuis la Ligne de Commande (Optionnel)

Pour les mises à jour en batch, vous pouvez utiliser le management command:

### Mettre à Jour en Expédition
```bash
python manage.py update_order_status 42 shipped --tracking DHL123456XYZ
```

### Mettre à Jour en Livraison
```bash
python manage.py update_order_status 42 delivered
```

### Mettre à Jour En Traitement
```bash
python manage.py update_order_status 42 processing
```

---

## 📧 Notifications Clients

### Comportement Actuel
Les clients reçoivent:
1. **Email de confirmation** - Après paiement
2. **Accès à l'historique** - Ils peuvent voir leurs commandes dans "Mes Commandes"
3. **Détails + Timeline** - Voir le statut mis à jour

### Améliorations Futures
- Email automatique quand "Expédiée"
- Email automatique quand "Livrée"
- SMS notifications (optionnel)
- Tracking link dans les emails

---

## 🎯 Statuts Expliqués

### Paiement
| Statut | Emoji | Couleur | Signification |
|--------|-------|--------|---------------|
| Payée | ✓ | Vert | Paiement reçu et validé |
| En attente | ⏳ | Orange | En cours de traitement |
| Annulée | ✕ | Rouge | Paiement refusé/annulé |

### Livraison
| Statut | Emoji | Couleur | Signification |
|--------|-------|--------|---------------|
| En attente | 📦 | Gris | Commande confirmée, en préparation |
| En traitement | ⚙️ | Bleu | Préparation active |
| Expédiée | 🚚 | Violet | Envoyée au client |
| Livrée | ✓ | Vert | Reçue par le client |
| Annulée | ✕ | Rouge | Commande annulée |

---

## 🔒 Permissions

Seuls les administrateurs peuvent:
- Voir toutes les commandes
- Modifier les statuts de livraison
- Entrer les numéros de suivi
- Voir les emails des clients

---

## ❓ FAQ

### Comment un client perd-il accès à sa commande?
Les clients ne perdront jamais accès. Ils peuvent toujours voir leurs commandes s'ils sont connectés.

### Que se passe-t-il si je change d'avis sur un statut?
Cliquez simplement sur la commande et changez le statut. Il n'y a pas de limite de modifications.

### Les clients reçoivent-ils des emails?
Oui, après paiement. Les futurs emails de statut seront envoyés (à implémenter).

### Puis-je filtrer par plage de dates?
Oui, utilisez le filtre "Date" avec le calendrier fourni.

### Comment exporter les commandes?
Django admin offre des options d'export. Utilisez les formats CSV/Excel depuis les filtres.

---

## 🚀 Bonnes Pratiques

✅ **À Faire**:
- Mettre à jour rapidement le statut quand vous expédiez
- Entrer toujours un numéro de suivi
- Vérifier régulièrement les commandes "En attente"
- Utiliser les filtres pour trouver rapidement

❌ **À Éviter**:
- Délaisser une commande sans statut
- Oublier d'entrer le numéro de suivi
- Modifier pascialement (la date sans le statut)
- Utiliser des numéros de suivi incorrects

---

## 📞 Support

Pour toute question technique ou pour améliorer ce système, contactez le responsable technique.
