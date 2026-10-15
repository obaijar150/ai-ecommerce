# AI-Powered E-Commerce Platform — Project Plan

## 1. Project Overview

A full-featured, open-source E-commerce platform with AI capabilities for product recommendations, search, review summarization, and chat-based shopping assistance. Built with Django, Django REST Framework, PostgreSQL, HTML, CSS, and vanilla JavaScript. No paid APIs or services — all AI features use free, open-source models.

## 2. Technology Stack

| Layer | Technology | License |
|-------|-----------|---------|
| Backend Framework | Django 5.x | BSD-3 |
| API Framework | Django REST Framework | BSD-3 |
| Database | PostgreSQL 15+ | PostgreSQL License |
| AI/ML Framework | scikit-learn | BSD-3 |
| NLP (Review Summaries) | transformers (Hugging Face) | Apache-2.0 |
| NLP Fallback | NLTK | Apache-2.0 |
| Recommendation Engine | Surprise (scikit-surprise) | BSD-3 |
| Task Queue | Celery + Redis | BSD-3 |
| Search | PostgreSQL Full-Text Search | PostgreSQL License |
| Frontend | HTML5, CSS3, Vanilla JS (ES6+) | — |
| Templates | Django Template Language | BSD-3 |
| Forms | Django Crispy Forms | MIT |
| Testing | pytest, factory_boy | MIT |
| Task | — | — |

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    Browser                          │
│              HTML + CSS + Vanilla JS                │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP
┌──────────────────▼──────────────────────────────────┐
│              Django Application                      │
│  ┌────────────┐ ┌────────────┐ ┌────────────────┐  │
│  │   Store    │ │    API     │ │  AI Services   │  │
│  │  (Views)   │ │  (DRF)     │ │  (Celery)      │  │
│  └────────────┘ └────────────┘ └────────────────┘  │
│  ┌────────────┐ ┌────────────┐ ┌────────────────┐  │
│  │  Catalog   │ │   Orders   │ │  Accounts      │  │
│  └────────────┘ └────────────┘ └────────────────┘  │
└──────┬───────────────┬──────────────┬───────────────┘
       │               │              │
  ┌────▼────┐   ┌──────▼──────┐  ┌───▼────┐
  │ Postgres │   │    Redis    │  │Static/  │
  │          │   │  (Cache +   │  │Media    │
  │          │   │   Queue)    │  │Files    │
  └──────────┘   └─────────────┘  └─────────┘
```

## 4. Phase Breakdown

### Phase 1: Foundation (Week 1)
- Project scaffolding, settings, environment config
- Docker Compose for PostgreSQL + Redis
- Base templates (layout, navigation, footer)
- User authentication (registration, login, logout)
- Static files pipeline

### Phase 2: Product Catalog (Week 2)
- Category and Product models with migrations
- Product listing, detail, search pages
- Admin panel configuration
- Product image handling

### Phase 3: Shopping Cart & Orders (Week 3)
- Session-based cart
- Checkout flow
- Order management
- Order confirmation emails

### Phase 4: User Dashboard (Week 4)
- User profile management
- Order history and detail views
- Wishlist functionality

### Phase 5: AI Recommendation Engine (Week 5-6)
- Data collection pipeline (views, purchases, ratings)
- Surprise SVD model training
- "Customers also bought" feature
- "Recommended for you" on homepage
- Model retraining via Celery tasks

### Phase 6: AI Search & NLP (Week 7)
- PostgreSQL full-text search integration
- Search result ranking with AI
- NLTK-based review summarization
- Optional: Hugging Face transformer for advanced summaries

### Phase 7: AI Shopping Assistant (Week 8)
- Chat-based product assistant
- Intent detection with scikit-learn classifier
- Product Q&A from catalog data

### Phase 8: Admin & Analytics (Week 9)
- Sales dashboard with charts
- Inventory management
- AI-powered sales insights

### Phase 9: Polish & Testing (Week 10)
- End-to-end testing
- Performance optimization
- Security hardening
- Documentation finalization

## 5. AI Features Detail

### 5.1 Product Recommendations
- **Algorithm**: Collaborative filtering via Surprise SVD
- **Data Sources**: Purchase history, product ratings, cart additions
- **Output**: Ranked product lists per user
- **Trigger**: Celery periodic retraining (every 6 hours)
- **Fallback**: Popular products for new users

### 5.2 Review Summarization
- **Primary**: NLTK-based extractive summarization (offline, free)
- **Optional Upgrade**: Hugging Face transformers pipeline (distilbart-cnn)
- **Output**: 3-5 sentence summary per product's reviews
- **Trigger**: Generated on-demand, cached in database

### 5.3 Smart Search
- **Engine**: PostgreSQL Full-Text Search + ts_rank
- **Enhancement**: scikit-learn classifier for query intent
- **Features**: Fuzzy matching, synonym support, relevance ranking

### 5.4 Shopping Assistant Chatbot
- **NLP**: scikit-learn Naive Bayes / SVM intent classifier
- **Intents**: Product search, order status, recommendations, FAQ
- **Training Data**: Hand-curated JSON dataset (open source)
- **Fallback**: Keyword matching for unmatched queries

## 6. Security Requirements

- CSRF protection on all forms
- SQL injection prevention (ORM only, parameterized queries)
- XSS prevention (template escaping, CSP headers)
- Rate limiting on API endpoints
- Secure password hashing (Argon2)
- HTTPS enforcement in production
- Content Security Policy headers
- Input validation and sanitization
- File upload validation (type, size, content)
- Session security (HttpOnly, Secure, SameSite cookies)

## 7. Testing Strategy

| Type | Tool | Coverage Target |
|------|------|----------------|
| Unit Tests | pytest + pytest-django | 80%+ |
| Integration Tests | Django TestCase | Critical paths |
| API Tests | DRF APITestCase | All endpoints |
| AI Model Tests | pytest | Accuracy thresholds |
| Frontend Tests | Jest (optional) | Critical JS |
| E2E Tests | Selenium (optional) | Key user flows |

## 8. Project Success Criteria

- All 9 phases completed and verified
- 80%+ test coverage
- All AI features functional with fallback modes
- Responsive design (mobile, tablet, desktop)
- Page load < 2 seconds (excluding AI generation)
- Complete documentation
- Zero known security vulnerabilities
