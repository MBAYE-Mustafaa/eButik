from decimal import Decimal
from django import template

register = template.Library()

@register.filter
def format_price(amount, currency="XOF"):
    """Formate un montant selon la devise.

    - **XOF (FCFA)** : on garde un entier, pas de décimales.
    - **autres devises** : on affiche deux décimales.

    Le symbole ou l'abréviation est ajoutée automatiquement.
    """
    if amount is None:
        return ""

    # convertit en Decimal si besoin (string depuis le panier)
    amt = Decimal(amount)
    cur = currency.upper()

    # formatage simple des milliers avec un espace pour plus de lisibilité
    sep = " "
    if cur == "XOF":
        # entiers uniquement pour le FCFA
        formatted = f"{int(amt):,}".replace(",", sep)
    else:
        # deux décimales pour les autres devises
        formatted = f"{amt:,.2f}".replace(",", sep)

    symbols = {"XOF": "FCFA", "EUR": "€"}
    symbol = symbols.get(cur, cur)
    return f"{formatted} {symbol}"
