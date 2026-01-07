from .panier import Panier

# Ajoute le panier au contexte des templates
def panier(request):
    # Retourne un dictionnaire avec le panier
    return {'panier': Panier(request)}

