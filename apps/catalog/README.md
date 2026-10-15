# Catalog

Product catalog and administration for the AI E-Commerce platform.

## Purpose

The `catalog` app owns everything about products: how they are organised
(categories and subcategories), described (brand, SKU, specifications,
images), priced, stocked, and discovered (listing, filtering, sorting,
search). It also provides the Django admin screens used to manage the
catalog day to day.

## Models

| Model | Description |
|-------|-------------|
| `Brand` | Manufacturer/brand with optional logo and website. |
| `Category` | Self-referential tree — a category may have a `parent`, giving subcategories. |
| `Tag` | Free-form tags used for filtering and search. |
| `Product` | Core product: name, description, brand, price, sale price, SKU, stock, weight, JSON `specifications`, rating aggregates, tags. |
| `ProductImage` | Product images with a primary flag and upload validation. |
| `ProductInventory` | One-to-one stock record with reservations and reorder logic. |

### Computed helpers

* `Product.current_price` — sale price when set, otherwise regular price.
* `Product.discount_percentage` — percentage saved when on sale.
* `Product.in_stock` / `is_low_stock` — stock state.
* `Product.primary_image` — primary image, else the first available.
* `Product.refresh_rating()` — recompute `average_rating`/`review_count`.
* `ProductInventory.available_quantity` / `needs_reorder`, plus `reserve()`
  and `release()` with validation.

### Queryset helpers (`Product.objects`)

* `.active()` — only active products.
* `.with_effective_price()` — annotate `effective_price` (sale price or
  price) so price filtering/sorting happens in the database.
* `.search(query)` — portable multi-term keyword search across name,
  description, SKU, brand, category and tags.

## Views & URLs

| URL | View | Description |
|-----|------|-------------|
| `/` | `HomePageView` | Featured + recent products and root categories. |
| `/products/` | `ProductListView` | Listing with filtering, sorting, search and pagination. |
| `/products/category/<slug>/` | `CategoryDetailView` | Products in a category and its subcategories. |
| `/products/<slug>/` | `ProductDetailView` | Detail page with gallery, specifications and reviews. |

Filtering, sorting and search are query parameters: `q`, `category`,
`brand`, `tag`, `min_price`, `max_price`, `in_stock`, `sort`
(`newest`, `price`, `-price`, `name`, `-name`, `rating`, `popular`).

## Admin

Rich admin screens are provided for `Brand`, `Category`, `Product`, `Tag`,
`ProductImage` and `ProductInventory`. The product screen uses inline
images and inventory, a stock-level filter, and visual price/stock/rating
columns. Forms (`ProductForm`, `CategoryForm`, `BrandForm`,
`ProductImageForm`) hold the validation logic and are shared with the admin.

## Image upload safety

Uploads are validated through `validators.py`:

* allow-listed extensions (`jpg`, `jpeg`, `png`, `webp`),
* a maximum file size (`MAX_UPLOAD_SIZE_MB`, default 5 MB),
* a content-type check.

Pillow additionally verifies the real image bytes on save.

## Sample data

```powershell
python manage.py seed_catalog          # create sample data
python manage.py seed_catalog --flush  # wipe catalog data first
```

## API

DRF viewsets are exposed at `/api/products/`, `/api/categories/`,
`/api/brands/` and `/api/tags/`. See `api_urls.py`.

## Tests

```powershell
pytest apps\catalog\tests\
```

Covers models and queryset helpers, inventory validation, forms, upload
validators, views (listing/filter/sort/search/pagination/detail/category),
admin CRUD (including inline images/inventory), the API, and the seed
command.
