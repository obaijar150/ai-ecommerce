# AI-Powered E-Commerce Platform

A complete, open-source E-commerce platform with AI-powered product recommendations, smart search, review summarization, and a chat-based shopping assistant. Built with Django, PostgreSQL, HTML/CSS, and vanilla JavaScript.

## Features

- **User Accounts**: Registration, login, profiles, addresses, wishlist
- **Product Catalog**: Categories, products, images, tags, inventory
- **Shopping Cart & Orders**: Session cart, checkout, order tracking
- **Product Reviews**: Ratings, verified purchases, helpful votes
- **AI Recommendations**: Collaborative filtering with scikit-learn (SVD)
- **AI Review Summaries**: NLP extractive summarization with NLTK
- **Smart Search**: PostgreSQL Full-Text Search with relevance ranking
- **AI Shopping Assistant**: Chatbot with intent classification
- **Admin Analytics**: Sales dashboard with AI-powered insights

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5, Django REST Framework |
| Database | PostgreSQL 16 (SQLite for local dev) |
| AI/ML | scikit-learn, Surprise, NLTK |
| Task Queue | Celery + Redis |
| Frontend | HTML5, CSS3, Vanilla JavaScript |

## Quick Start

### Prerequisites

- Python 3.12+
- (Optional) Docker + Docker Compose for PostgreSQL and Redis

### Local Development Setup

1. **Create a virtual environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. **Install dependencies:**
   ```powershell
   pip install -r requirements\base.txt
   ```

3. **Create environment file:**
   ```powershell
   copy .env.example .env
   ```

4. **Run migrations:**
   ```powershell
   $env:DJANGO_SETTINGS_MODULE="config.settings.dev"
   python manage.py migrate
   ```

5. **Create a superuser:**
   ```powershell
   python manage.py createsuperuser
   ```

6. **Start the development server:**
   ```powershell
   python manage.py runserver
   ```

7. **Open in browser:**
   ```
   http://127.0.0.1:8000
   ```

### Using Docker (PostgreSQL + Redis)

1. **Start infrastructure containers:**
   ```powershell
   docker-compose up -d db redis
   ```

2. **Update `.env` with PostgreSQL credentials:**
   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=ecommerce
   DB_USER=ecommerce_user
   DB_PASSWORD=change-me
   ```

3. **Switch to PostgreSQL settings** by setting in `.env`:
   ```
   DJANGO_SETTINGS_MODULE=config.settings.dev_postgres
   ```

4. **Run migrations and start the app:**
   ```powershell
   python manage.py migrate
   python manage.py runserver
   ```

## Project Structure

```
AI-Ecommerce/
├── apps/
│   ├── accounts/       # User management
│   ├── catalog/        # Product catalog
│   ├── orders/         # Cart and orders
│   ├── reviews/        # Product reviews + AI summaries
│   ├── search/         # Full-text search
│   ├── ai_engine/      # Recommendations, chatbot, NLP
│   └── analytics/      # Admin dashboard
├── config/             # Django settings, URLs, Celery
├── templates/          # Base templates and includes
├── static/             # Global CSS and JS
├── requirements/       # Pinned dependencies
├── docs/               # Architecture and design docs
├── docker-compose.yml  # PostgreSQL + Redis
└── Dockerfile          # Production container
```

## API Documentation

Interactive API docs are available at:
```
http://127.0.0.1:8000/api/docs/
```

## Sample Data

Populate the catalog with sample categories, brands, products, images and
inventory for local development:

```powershell
python manage.py seed_catalog          # create sample data
python manage.py seed_catalog --flush  # wipe catalog data first, then seed
```

The command generates placeholder product images in memory, so no binary
assets need to be committed.

## Testing

```powershell
# Run all tests (settings are configured in pytest.ini)
pytest

# Run with coverage
pytest --cov=apps --cov-report=html

# Run specific app tests
pytest apps\catalog\tests\
```

## Environment Variables

See [.env.example](.env.example) for all available configuration options. **Never commit `.env` to version control.**

## License

MIT License — See [LICENSE](LICENSE) for details.
