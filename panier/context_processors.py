from .panier import Panier

# Ajoute le panier et la devise au contexte des templates
# la devise est conservée en session et déterminée à partir du pays/paramètre
# elle sert au formatage et, éventuellement, à la conversion ultérieure.
def panier(request):
    panier_obj = Panier(request)

    # détection simple de la devise : on peut enrichir par GeoIP, langue, profil ou pays
    # on peut re-déterminer la devise à tout moment en analysant
    # la variable de session `checkout_country` ou le profil utilisateur
    country = request.session.get('checkout_country')
    user = getattr(request, 'user', None)
    if not country and user and getattr(user, 'is_authenticated', False):
        try:
            country = user.profil.pays
        except Exception:
            country = None

    cur = None
    if country:
        c = country.strip().upper()[:2]
        if c in ('FR','BE','CH','LU','ES','PT','IT','DE'):
            cur = 'EUR'
        else:
            cur = 'XOF'
    else:
        # sinon on retient la devise existante ou met la valeur par défaut
        cur = request.session.get('currency', 'XOF')

    # sauvegarde systématique pour refléter un changement éventuel
    request.session['currency'] = cur

    return {'panier': panier_obj, 'currency': cur}

