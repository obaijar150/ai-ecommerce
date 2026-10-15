# Project Folder Structure

```
AI-Ecommerce/
├── AGENTS.md                          # Project rules (this file's purpose)
├── README.md                          # Project overview and setup guide
├── LICENSE                            # MIT License
├── CHANGELOG.md                       # Version history
├── .env.example                       # Environment variable template
├── .env                               # Local secrets (NEVER commit)
├── .gitignore                         # Git ignore rules
├── .flake8                            # Flake8 config
├── pyproject.toml                     # Project metadata + tool config
├── pytest.ini                         # Pytest configuration
├── requirements/
│   ├── base.txt                       # Core dependencies
│   ├── dev.txt                        # Development dependencies
│   ├── production.txt                 # Production dependencies
│   └── ai.txt                         # AI/ML dependencies
├── docker-compose.yml                 # PostgreSQL + Redis containers
├── Dockerfile                         # Application container
├── docker/
│   ├── entrypoint.sh                  # Container startup script
│   └── nginx.conf                     # Nginx reverse proxy config
├── docs/
│   ├── PROJECT_PLAN.md                # Full project plan
│   ├── DATABASE_DESIGN.md             # ERD and table definitions
│   ├── FOLDER_STRUCTURE.md            # This file
│   ├── DEPLOYMENT.md                  # Deployment guide
│   ├── API_REFERENCE.md               # API endpoint documentation
│   └── CONTRIBUTING.md                # Contribution guidelines
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py                    # Shared settings
│   │   ├── dev.py                     # Development settings
│   │   ├── production.py              # Production settings
│   │   └── test.py                    # Test settings
│   ├── urls.py                        # Root URL configuration
│   ├── wsgi.py                        # WSGI entry point
│   └── asgi.py                        # ASGI entry point
├── apps/
│   ├── __init__.py
│   ├── accounts/                      # User management
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py                # Business logic
│   │   ├── signals.py                 # Post-save signals
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── templates/
│   │   │   └── accounts/
│   │   │       ├── login.html
│   │   │       ├── register.html
│   │   │       ├── profile.html
│   │   │       ├── profile_edit.html
│   │   │       ├── address_list.html
│   │   │       ├── address_form.html
│   │   │       └── wishlist.html
│   │   ├── templatetags/
│   │   │   ├── __init__.py
│   │   │   └── account_tags.py
│   │   ├── static/
│   │   │   └── accounts/
│   │   │       ├── css/
│   │   │       │   └── accounts.css
│   │   │       └── js/
│   │   │           └── profile.js
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── factories.py
│   │   │   ├── test_forms.py
│   │   │   ├── test_models.py
│   │   │   ├── test_views.py
│   │   │   └── test_services.py
│   │   └── migrations/
│   ├── catalog/                       # Product catalog
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── templates/
│   │   │   └── catalog/
│   │   │       ├── product_list.html
│   │   │       ├── product_detail.html
│   │   │       ├── category_list.html
│   │   │       └── product_card.html
│   │   ├── templatetags/
│   │   │   ├── __init__.py
│   │   │   └── catalog_tags.py
│   │   ├── static/
│   │   │   └── catalog/
│   │   │       ├── css/
│   │   │       │   └── catalog.css
│   │   │       └── js/
│   │   │           ├── product_detail.js
│   │   │           └── product_list.js
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── factories.py
│   │   │   ├── test_models.py
│   │   │   ├── test_views.py
│   │   │   ├── test_search.py
│   │   │   └── test_services.py
│   │   └── migrations/
│   ├── orders/                        # Cart and orders
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── templates/
│   │   │   └── orders/
│   │   │       ├── cart.html
│   │   │       ├── checkout.html
│   │   │       ├── order_list.html
│   │   │       ├── order_detail.html
│   │   │       └── order_confirmation.html
│   │   ├── static/
│   │   │   └── orders/
│   │   │       ├── css/
│   │   │       │   └── cart.css
│   │   │       └── js/
│   │   │           ├── cart.js
│   │   │           └── checkout.js
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── factories.py
│   │   │   ├── test_models.py
│   │   │   ├── test_views.py
│   │   │   ├── test_checkout.py
│   │   │   └── test_services.py
│   │   └── migrations/
│   ├── reviews/                       # Product reviews
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py                # AI summary generation
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── templates/
│   │   │   └── reviews/
│   │   │       ├── review_form.html
│   │   │       └── review_list.html
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── factories.py
│   │   │   ├── test_models.py
│   │   │   ├── test_views.py
│   │   │   └── test_ai_summary.py
│   │   └── migrations/
│   ├── search/                        # Search functionality
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── templates/
│   │   │   └── search/
│   │   │       └── search_results.html
│   │   ├── static/
│   │   │   └── search/
│   │   │       ├── css/
│   │   │       │   └── search.css
│   │   │       └── js/
│   │   │           └── search.js
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── test_search.py
│   │   │   └── test_services.py
│   │   └── migrations/
│   ├── ai_engine/                     # AI features
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                  # Recommendation cache, chat sessions
│   │   ├── serializers.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── recommendations.py     # Surprise SVD engine
│   │   │   ├── nlp.py                  # NLTK summarization
│   │   │   ├── chatbot.py             # Intent classifier
│   │   │   └── popular.py             # Fallback: popularity engine
│   │   ├── tasks.py                   # Celery tasks for training
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── templates/
│   │   │   └── ai_engine/
│   │   │       └── chat.html
│   │   ├── static/
│   │   │   └── ai_engine/
│   │   │       ├── css/
│   │   │       │   └── chat.css
│   │   │       └── js/
│   │   │           └── chat.js
│   │   ├── training_data/
│   │   │   ├── chatbot_intents.json    # Intent training dataset
│   │   │   └── README.md              # How to add training data
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── factories.py
│   │   │   ├── test_recommendations.py
│   │   │   ├── test_nlp.py
│   │   │   ├── test_chatbot.py
│   │   │   └── test_tasks.py
│   │   └── migrations/
│   └── analytics/                     # Admin dashboard
│       ├── __init__.py
│       ├── apps.py
│       ├── models.py
│       ├── services.py
│       ├── urls.py
│       ├── views.py
│       ├── templates/
│       │   └── analytics/
│       │       ├── dashboard.html
│       │       └── sales_report.html
│       ├── static/
│       │   └── analytics/
│       │       ├── css/
│       │       │   └── dashboard.css
│       │       └── js/
│       │           └── dashboard.js
│       ├── tests/
│       │   ├── __init__.py
│       │   └── test_views.py
│       └── migrations/
├── templates/                         # Project-level templates
│   ├── base.html                      # Master layout
│   ├── base_store.html                # Store layout (header/footer)
│   ├── base_minimal.html              # Login/register layout
│   ├── 404.html
│   ├── 500.html
│   ├── 503.html
│   ├── includes/
│   │   ├── header.html
│   │   ├── footer.html
│   │   ├── navigation.html
│   │   ├── pagination.html
│   │   ├── messages.html
│   │   └── ai_recommendations.html
│   └── emails/
│       ├── order_confirmation.html
│       ├── password_reset.html
│       └── welcome.html
├── static/                            # Project-level static files
│   ├── css/
│   │   └── global.css                 # Global styles, CSS variables
│   ├── js/
│   │   └── global.js                  # Global utilities, API helper
│   ├── images/
│   │   ├── logo.svg
│   │   └── placeholder.png
│   └── favicon.ico
├── locale/                            # i18n translations
│   └── en/
│       └── LC_MESSAGES/
│           └── django.po
├── media/                             # User uploads (gitignored)
│   ├── products/
│   ├── avatars/
│   └── reviews/
├── scripts/
│   ├── seed_data.py                   # Populate test catalog
│   ├── train_recommendations.py       # Manual model training
│   └── generate_review_summaries.py   # Batch AI summary generation
├── fixtures/                          # Data fixtures
│   ├── categories.json
│   ├── sample_products.json
│   └── sample_users.json
└── manage.py
```
