# instructions for TEST eButik

Purpose: give an AI coding agent immediate, actionable knowledge to be productive in this Django codebase.

1) Big picture
- **Project type:** Django monolith with two main local apps: `core` (products, auth, pages) and `panier` (session-based shopping cart).
- **Entry points:** `manage.py` for CLI; URLs defined in [eButik/urls.py](eButik/urls.py#L1-L40) and app routes in [core/urls.py](core/urls.py#L1-L20) and [panier/urls.py](panier/urls.py#L1-L20).
- **Templates:** stored under `core/templates` (site pages) and `panier/templates` (cart partials). Views render these templates directly (e.g., `core/views.py::index`, `panier/views.py::resume_panier`).

2) State & persistence
- **Database:** SQLite file `db.sqlite3` (default Django settings). Use Django ORM (`core.models`) and run migrations with `python manage.py makemigrations` / `python manage.py migrate`.
- **Media & static:** media files served from `media/` with MEDIA_ROOT; static assets live in `static/` and `STATICFILES_DIRS` is set. Dev server serves media via urlpatterns in [eButik/urls.py](eButik/urls.py#L1-L40).

3) Cart (panier) specific patterns (critical)
- Cart is session-backed using key `session_panier` in `panier/panier.py` — the Panier class expects a Django `request` and stores product entries as dicts of `{product_id: {'price': <str>}}`.
- The cart is exposed to templates via a context processor `panier.context_processors.panier` registered in settings (see `eButik/settings.py` → `TEMPLATES[0]['OPTIONS']['context_processors']`).
- Add-to-cart endpoint: `POST` to `/panier/ajouter/` (view `panier.views.ajouter_au_panier`). The view expects `action=post` and `product_id` in the POST body and returns JSON `{qte: <number>}` (quantity uses `Panier.__len__()`). Use this pattern when implementing AJAX cart updates.

4) Routing and notable quirks to watch for
- The project-level urls include many `include('core.urls')` entries for specific paths (e.g., `product/<int:pk>/` is routed via include). Confirm canonical route definitions live in `core/urls.py` when adding endpoints.
- Some views use `get_list_or_404(Product, id=product_id)` (in `panier/views.py`) which returns a list — prefer `get_object_or_404(Product, id=...)` when you need a single object.

5) Common developer workflows (commands)
- Install dev dependencies (minimal): `pip install django jazzmin` (project uses `jazzmin` in `INSTALLED_APPS`).
- Run dev server: `python manage.py runserver`.
- Migrations: `python manage.py makemigrations` then `python manage.py migrate`.
- Tests: `python manage.py test` (Django test runner; `tests.py` exists in apps).
- Create admin user: `python manage.py createsuperuser` and use `/admin/` (Jazzmin skin enabled).

6) Conventions & small patterns
- Templates referenced by views are plain names under `templates/` (e.g., `index.html`, `product.html`, `resume_panier.html`). Use these names when updating views or writing template includes.
- Product images upload path: `uploads/product/` (see `core.models.Product.image` upload_to).
- Prices are stored as `DecimalField` in `core.models.Product` but cart currently stores `price` as string — be careful when doing arithmetic (convert back to Decimal).

7) Integration & extension points
- Admin: `core/admin.py` and `panier/admin.py` are places to register models.
- Context processor hook: to change cart visibility or structure, update `panier/context_processors.py` and `eButik/settings.py` accordingly.

8) What to avoid changing without tests
- The session key `session_panier` and the structure of stored cart dicts — front-end code and templates expect this shape.
- URL layout: since project-level urls include app urls in multiple places, refactor routing only after verifying path collisions.

9) Quick examples
- AJAX add-to-cart POST (client): `POST /panier/ajouter/` form data: `action=post`, `product_id=<id>` -> expects JSON `{qte: <int>}`.
- Read cart from a view/template: use context variable `panier` (provided by context processor) or instantiate `Panier(request)` in views.

10) AJAX Example (vanilla JS)
Use this pattern to call the add-to-cart endpoint from the frontend; ensure you include the CSRF token.

```javascript
// get CSRF token from cookies
function getCookie(name) {
	const value = `; ${document.cookie}`;
	const parts = value.split(`; ${name}=`);
	if (parts.length === 2) return parts.pop().split(';').shift();
}

const csrftoken = getCookie('csrftoken');

function addToCart(productId) {
	const data = new FormData();
	data.append('action', 'post');
	data.append('product_id', productId);

	fetch('/panier/ajouter/', {
		method: 'POST',
		body: data,
		headers: { 'X-CSRFToken': csrftoken }
	})
	.then(res => res.json())
	.then(json => {
		// json.qte contains the total quantity in the cart
		console.log('Cart quantity:', json.qte);
		// update UI accordingly
	});
}
```

If anything here is unclear or you want examples added (tests, sample AJAX, or a task checklist), tell me which area and I will iterate.
