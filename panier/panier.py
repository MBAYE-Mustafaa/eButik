from core.models import Product, Size
import copy


class Panier():
    def __init__(self, request):
        self.session = request.session
        panier = self.session.get("session_panier")
        if "session_panier" not in request.session:
            panier = self.session["session_panier"] = {}

        self.panier = panier 

        #pour créer une clé unique pour le produit dans le panier, en tenant compte de la taille si applicable


    def _make_key(self, product_id, size=None):
        if size:
            return f"{product_id}:{size}"
        return str(product_id)

    def ajouter(self, product, qte=1, size=None):
        product_id = str(product.id)
        key = self._make_key(product_id, size)
        qte = int(qte or 1)

        if key in self.panier:
            existing = int(self.panier[key].get('qte', 1))
            self.panier[key]['qte'] = existing + qte
        else:
            entry = {'price': str(product.price), 'qte': qte}
            if size:
                entry['size'] = str(size)
            self.panier[key] = entry

        self.session.modified = True

    def set_quantity(self, product, qte):
        # expects product is an instance or id; if product has attribute 'id' use it
        product_id = str(getattr(product, 'id', product))
        qte = int(qte or 1)
        # If there's a size specified, caller should pass a key to target specific item
        if product_id in self.panier:
            if qte <= 0:
                self.panier.pop(product_id, None)
            else:
                self.panier[product_id]['qte'] = qte
        else:
            # If product not present, add it with qte
            self.panier[product_id] = {'price': str(product.price), 'qte': qte}

        self.session.modified = True

    def remove(self, product_id):
        pid = str(product_id)
        if pid in self.panier:
            self.panier.pop(pid, None)
            self.session.modified = True

    def clear(self):
        self.session['session_panier'] = {}
        self.panier = self.session['session_panier']
        self.session.modified = True
    def __len__(self):
        # retourne le nombre d'articles distincts dans le panier
        return len(self.panier)

    @property
    def total_items(self):
        # retourne la somme des quantités (nbr d'items)
        return sum(int(v.get('qte', 1)) for v in self.panier.values())

    def get_prods(self):
        # Pour obtenir les objets Product et y attacher la quantité
        # keys may be like '12' or '12:38' when size is provided
        keys = list(self.panier.keys())
        ids = set(k.split(':')[0] for k in keys)
        products = Product.objects.filter(id__in=ids)

        prods_out = []
        for prod in products:
            # find all matching keys for this product
            matching = [k for k in keys if k.split(':')[0] == str(prod.id)]
            for k in matching:
                entry = self.panier.get(k, {})
                # clone the product instance so multiple lines for same product remain distinct
                item = copy.copy(prod)
                item.qte = int(entry.get('qte', 1))
                item.cart_key = k
                # selected_size stores size id (string) when present; resolve name if possible
                sel = entry.get('size')
                item.selected_size = sel
                item.selected_size_name = None
                if sel:
                    try:
                        # attempt to interpret as id
                        size_obj = Size.objects.get(id=int(sel))
                        item.selected_size_name = size_obj.name
                    except Exception:
                        # fallback to raw value
                        item.selected_size_name = sel
                prods_out.append(item)

        return prods_out



