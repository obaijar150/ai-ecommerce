# AGENTS.md — AI E-Commerce Platform

## Project Rules

1. **No paid APIs or services.** All AI features must use free, open-source tools (scikit-learn, NLTK, Surprise, Hugging Face transformers with open models).
2. **No frontend frameworks.** HTML, CSS, and vanilla JavaScript only. No React, Vue, Next.js, or Angular.
3. **Django templates** for server-side rendering. DRF for API endpoints consumed by vanilla JS fetch().
4. **PostgreSQL is the only database.** Use its features (JSONB, FTS, arrays) rather than adding MongoDB/Elasticsearch.
5. **Every feature must have tests.** No exceptions. Run `pytest` before committing.
6. **No feature is "done" until tested.** A feature is complete only when it works AND has passing tests.
7. **Phase-gated development.** Complete and verify each phase before starting the next.
8. **Commit after each verified phase.** Write meaningful commit messages.

## Architecture Rules

### Modular Apps
Each Django app must be self-contained with its own models, views, templates, static files, and tests.

| App | Purpose |
|-----|---------|
| `accounts` | User registration, login, profiles, addresses, wishlist |
| `catalog` | Categories, products, images, tags, inventory |
| `orders` | Cart, checkout, orders, order history |
| `reviews` | Product reviews and ratings |
| `search` | Full-text search and search analytics |
| `ai_engine` | Recommendation engine, NLP summaries, chatbot assistant |
| `analytics` | Admin dashboard and sales insights |

### Separation of Concerns
- **Models**: Data structure and validation only. No business logic beyond model methods.
- **Views/Controllers**: Request handling, authentication, response formatting. Thin — delegate to services.
- **Services Layer**: Business logic in `services.py` files within each app.
- **Templates**: Presentation only. No complex logic — use template tags/filters.
- **Static files**: Organized per app: `static/app_name/css/`, `static/app_name/js/`.

### URL Structure
```
/                          → Homepage (store app)
/products/                 → Product listing
/products/<slug>/           → Product detail
/cart/                     → Cart view
/checkout/                 → Checkout
/orders/                   → Order history
/orders/<uuid>/            → Order detail
/profile/                  → User profile
/profile/addresses/        → Address management
/wishlist/                 → Wishlist
/search/                   → Search results
/chat/                     → AI shopping assistant
/api/                      → DRF API root
/admin/                    → Django admin
```

## Coding Standards

### Python / Django

1. **PEP 8** compliance. Max line length: 100 characters.
2. **Type hints** on all function signatures (Python 3.10+ syntax).
3. **Docstrings** on all classes and public functions (Google style).
4. **Constants** at module level, UPPER_CASE naming.
5. **No raw SQL** except for migrations. Use Django ORM or `RawSql` for complex FTS queries.
6. **Environment variables** for all secrets (use `django-environ` or `python-decouple`).
7. **Settings split**: `settings/base.py`, `settings/dev.py`, `settings/prod.py`, `settings/test.py`.
8. **Use `pathlib`** for file paths, not `os.path`.
9. **Celery tasks** must be idempotent and handle failures gracefully.
10. **Database transactions** for multi-step operations (checkout, order creation).
11. **Select related / prefetch related** to avoid N+1 queries.

### JavaScript (Vanilla)

1. **ES6+** syntax. Use `const`/`let`, arrow functions, template literals.
2. **No global variables.** Wrap in IIFEs or use modules (`<script type="module">`).
3. **fetch()** for API calls. Handle errors properly.
4. **No jQuery.** Pure vanilla JS.
5. **Organized per page**: `static/js/pages/product_detail.js`.
6. **Event delegation** for dynamic content.
7. **Debounce/throttle** for input handlers (search, scroll).

### HTML / CSS

1. **Semantic HTML5** elements (`header`, `nav`, `main`, `article`, `section`).
2. **CSS custom properties** for theming (colors, spacing, fonts).
3. **Mobile-first** responsive design.
4. **BEM naming** for CSS classes: `.product-card`, `.product-card__title`.
5. **No inline styles.** External stylesheets only.
6. **Accessibility**: ARIA labels, alt text, keyboard navigation, color contrast.

### Templates

1. **Template inheritance**: `base.html` → `base_store.html` → page templates.
2. **Template tags**: Custom tags in `templatetags/` for reusable components.
3. **Escape all output**: Use `|safe` filter only for verified-safe content.
4. **Pagination**: Use Django's built-in paginator.

## Security Requirements

### Authentication & Authorization
- Argon2 password hashing (set `PASSWORD_HASHERS` in settings)
- Login required for checkout, orders, profile, wishlist
- Staff-only access for admin dashboard
- `@login_required` and `@permission_required` decorators on all protected views
- CSRF tokens on all forms (Django middleware)

### Data Protection
- SQL injection prevention via Django ORM only
- XSS prevention via template auto-escaping
- CSP headers via `django-csp`
- Secure cookie settings: `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE='Lax'`
- `SECURE_SSL_REDIRECT` in production
- File upload validation: whitelist extensions, size limits, MIME type checking
- Rate limiting via `django-ratelimit` on login, search, and chat endpoints

### API Security
- DRF permission classes on every viewset
- Token authentication for API (DRF's `TokenAuthentication`)
- Throttling on API endpoints
- Serializer validation for all input
- No sensitive data in API responses (passwords, payment details)

### Infrastructure
- `DEBUG = False` in production
- `ALLOWED_HOSTS` strictly configured
- Environment variables for all secrets (never commit `.env`)
- `SECURE_HSTS_SECONDS`, `SECURE_CONTENT_TYPE_NOSNIFF`
- Database connections encrypted (`sslmode=require`)

## Testing Instructions

### Running Tests
```bash
# All tests
pytest

# Specific app
pytest apps/catalog/

# Specific test file
pytest apps/orders/tests/test_checkout.py

# With coverage
pytest --cov=apps --cov-report=html

# With verbosity
pytest -v
```

### Writing Tests
```python
# Every test file must have:
import pytest
from django.test import TestCase, Client
from factory import Faker

class TestProductDetail(TestCase):
    """Test product detail page."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.product = ProductFactory()

    def test_product_detail_renders(self):
        """Product detail page returns 200 and shows product name."""
        response = self.client.get(reverse('catalog:product_detail',
                                            kwargs={'slug': self.product.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)
```

### AI Model Tests
- Test recommendation output format and ranking
- Test review summary generation (mock transformer model)
- Test chatbot intent classification accuracy
- Include edge cases: empty data, cold start, out-of-vocabulary

### Test Data
- Use `factory_boy` + `Faker` for all test fixtures
- Factories in `tests/factories.py` within each app
- No hardcoded test data in test bodies

## Error Handling

### Django Views
- Custom 404, 503, 500 templates
- Try/except blocks around all external calls
- Log errors with `logging.getLogger(__name__)`
- User-friendly error messages (never expose stack traces)

### API Views
- DRF's `exception_handler` for consistent error format
- Error format: `{"error": {"code": "...", "message": "...", "details": {...}}}`
- Appropriate HTTP status codes (400, 401, 403, 404, 500)

### AI Services
- Graceful fallback when model is unavailable
- Timeout handling for model inference
- Input validation before passing to models
- Log all AI service errors

## Documentation

### Code Documentation
- Docstrings on all classes and functions
- Comments explain WHY, not WHAT
- README.md per app explaining its purpose

### API Documentation
- DRF's built-in browsable API
- OpenAPI schema via `drf-spectacular`

### User Documentation
- `docs/` directory for architecture, deployment, contribution guides
- Inline help text in templates

## Git Workflow

- `main` branch: production-ready code
- `develop` branch: integration branch
- Feature branches: `phase-2-product-catalog`, `phase-5-recommendations`
- Pull requests required for merging to `main` and `develop`
- Commit messages: `feat(products): add image gallery component`
