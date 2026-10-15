# Database Design — AI E-Commerce Platform

## Entity-Relationship Overview

```
users ──────< order_items >────── orders
  │                                 │
  │                            order_status_history
  │
  ├──< reviews >────── products ────< product_images
  │                        │
  ├──< cart_items >──────│
  │                 product_inventory
  │
  ├──< wishlist_items >── products
  │
  ├──< user_activity_log
  │
  └──< addresses

categories ────< products (self-referential for subcategories)
tags ────< product_tags >────── products

recommendations_cache (AI-generated, per user)
search_queries (logged for analytics)
chat_sessions ────< chat_messages
```

## Table Definitions

### auth_user (Django built-in, extended via Profile)
Core user: id, username, email, password (Argon2), is_staff, is_active, date_joined

### accounts_profile
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | INT | FK → auth_user, UNIQUE |
| phone | VARCHAR(20) | |
| avatar | VARCHAR(255) | upload path |
| bio | TEXT | |
| date_of_birth | DATE | nullable |
| newsletter_subscribed | BOOLEAN | default False |
| created_at | TIMESTAMP | auto |
| updated_at | TIMESTAMP | auto |

### accounts_address
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | INT | FK → auth_user |
| label | VARCHAR(50) | e.g., "Home", "Work" |
| street | VARCHAR(255) | |
| city | VARCHAR(100) | |
| state | VARCHAR(100) | |
| postal_code | VARCHAR(20) | |
| country | VARCHAR(100) | |
| is_default | BOOLEAN | default False |

### catalog_category
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | VARCHAR(100) | NOT NULL |
| slug | VARCHAR(120) | UNIQUE |
| description | TEXT | |
| parent_id | UUID | FK → self, nullable |
| image | VARCHAR(255) | |
| is_active | BOOLEAN | default True |
| sort_order | INT | default 0 |

### catalog_product
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| category_id | UUID | FK → catalog_category |
| name | VARCHAR(200) | NOT NULL |
| slug | VARCHAR(220) | UNIQUE |
| description | TEXT | |
| price | DECIMAL(10,2) | NOT NULL, CHECK >= 0 |
| sale_price | DECIMAL(10,2) | nullable |
| sku | VARCHAR(50) | UNIQUE |
| stock_quantity | INT | default 0, CHECK >= 0 |
| weight_kg | DECIMAL(6,2) | nullable |
| is_active | BOOLEAN | default True |
| is_featured | BOOLEAN | default False |
| average_rating | DECIMAL(2,1) | default 0.0 |
| review_count | INT | default 0 |
| view_count | INT | default 0 |
| search_vector | TSVECTOR | GIN index for FTS |
| created_at | TIMESTAMP | auto |
| updated_at | TIMESTAMP | auto |

### catalog_product_image
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| product_id | UUID | FK → catalog_product |
| image | VARCHAR(255) | upload path |
| alt_text | VARCHAR(200) | |
| is_primary | BOOLEAN | default False |
| sort_order | INT | default 0 |

### catalog_tag
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | VARCHAR(50) | UNIQUE |
| slug | VARCHAR(60) | UNIQUE |

### catalog_product_tag (junction)
| Column | Type | Constraints |
|--------|------|-------------|
| product_id | UUID | FK → catalog_product |
| tag_id | UUID | FK → catalog_tag |
| PRIMARY KEY (product_id, tag_id) | | |

### catalog_product_inventory
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| product_id | UUID | FK → catalog_product, UNIQUE |
| quantity | INT | default 0 |
| reserved_quantity | INT | default 0 |
| last_restocked | TIMESTAMP | nullable |
| reorder_level | INT | default 10 |

### orders_order
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | INT | FK → auth_user |
| status | VARCHAR(20) | choices: pending/paid/shipped/delivered/cancelled/refunded |
| subtotal | DECIMAL(10,2) | NOT NULL |
| tax | DECIMAL(10,2) | default 0.00 |
| shipping_cost | DECIMAL(10,2) | default 0.00 |
| total | DECIMAL(10,2) | NOT NULL |
| shipping_address_id | UUID | FK → accounts_address |
| billing_address_id | UUID | FK → accounts_address |
| payment_method | VARCHAR(50) | |
| tracking_number | VARCHAR(100) | nullable |
| notes | TEXT | |
| created_at | TIMESTAMP | auto |
| updated_at | TIMESTAMP | auto |

### orders_order_item
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| order_id | UUID | FK → orders_order |
| product_id | UUID | FK → catalog_product |
| quantity | INT | NOT NULL, CHECK > 0 |
| unit_price | DECIMAL(10,2) | NOT NULL |
| total_price | DECIMAL(10,2) | NOT NULL |

### orders_order_status_history
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| order_id | UUID | FK → orders_order |
| status | VARCHAR(20) | |
| notes | TEXT | |
| created_at | TIMESTAMP | auto |

### reviews_review
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| product_id | UUID | FK → catalog_product |
| user_id | INT | FK → auth_user |
| rating | INT | CHECK 1-5 |
| title | VARCHAR(200) | |
| body | TEXT | |
| is_verified_purchase | BOOLEAN | default False |
| helpful_count | INT | default 0 |
| created_at | TIMESTAMP | auto |
| updated_at | TIMESTAMP | auto |

### reviews_review_summary (AI-generated)
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| product_id | UUID | FK → catalog_product, UNIQUE |
| summary | TEXT | |
| sentiment_score | DECIMAL(3,2) | -1.0 to 1.0 |
| model_version | VARCHAR(50) | |
| generated_at | TIMESTAMP | auto |

### cart_cart_item (session-based for guests, user-linked for auth)
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | INT | FK → auth_user, nullable |
| session_key | VARCHAR(40) | nullable, indexed |
| product_id | UUID | FK → catalog_product |
| quantity | INT | default 1, CHECK > 0 |
| added_at | TIMESTAMP | auto |

### accounts_wishlist_item
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | INT | FK → auth_user |
| product_id | UUID | FK → catalog_product |
| added_at | TIMESTAMP | auto |

### ai_recommendation_cache
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | INT | FK → auth_user |
| product_id | UUID | FK → catalog_product |
| score | DECIMAL(5,4) | 0.0000 to 1.0000 |
| algorithm | VARCHAR(50) | e.g., "svd", "popular", "content" |
| rank | INT | |
| created_at | TIMESTAMP | auto |

### ai_user_activity_log
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | INT | FK → auth_user, nullable |
| session_key | VARCHAR(40) | nullable |
| activity_type | VARCHAR(30) | view/search/purchase/cart_add/rate |
| product_id | UUID | FK → catalog_product, nullable |
| metadata | JSONB | |
| created_at | TIMESTAMP | auto |

### ai_search_query_log
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | INT | FK → auth_user, nullable |
| session_key | VARCHAR(40) | nullable |
| query | VARCHAR(500) | |
| results_count | INT | |
| clicked_product_id | UUID | FK → catalog_product, nullable |
| created_at | TIMESTAMP | auto |

### ai_chat_session
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | INT | FK → auth_user, nullable |
| session_key | VARCHAR(40) | nullable |
| started_at | TIMESTAMP | auto |
| ended_at | TIMESTAMP | nullable |

### ai_chat_message
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| session_id | UUID | FK → ai_chat_session |
| sender | VARCHAR(10) | "user" or "bot" |
| message | TEXT | |
| intent | VARCHAR(50) | nullable, classified intent |
| confidence | DECIMAL(3,2) | nullable |
| created_at | TIMESTAMP | auto |

## Key Indexes

```sql
-- Full-text search on products
CREATE INDEX idx_product_search ON catalog_product USING GIN(search_vector);

-- Activity log for recommendations
CREATE INDEX idx_activity_user ON ai_user_activity_log(user_id, activity_type, created_at DESC);

-- Order lookups
CREATE INDEX idx_order_user ON orders_order(user_id, created_at DESC);
CREATE INDEX idx_order_status ON orders_order(status);

-- Recommendation cache
CREATE INDEX idx_recommendations_user ON ai_recommendation_cache(user_id, score DESC);

-- Cart session cleanup
CREATE INDEX idx_cart_session ON cart_cart_item(session_key) WHERE user_id IS NULL;
```

## PostgreSQL Full-Text Search Configuration

```sql
-- English text search configuration
CREATE TEXT SEARCH CONFIGURATION english_nostem (COPY = english);
CREATE TEXT SEARCH DICTIONARY english_stem_nostem
    (TEMPLATE = snowball, Language = english, StopWords = english);
ALTER TEXT SEARCH CONFIGURATION english_nostem
    ALTER MAPPING FOR asciiword, word WITH english_stem_nostem;
```
