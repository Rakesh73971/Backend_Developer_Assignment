# Aforro - Backend Developer Assignment (Round 2)

Backend module for store inventory, order handling, product search, autocomplete, Redis caching/rate limiting, Celery background jobs, and Dockerized development.

## Project Structure

```text
Afforo Assignment/
|-- Dockerfile
|-- docker-compose.yml
|-- manage.py
`-- project/
    |-- settings.py
    |-- urls.py
    |-- celery.py
    |-- apps/
    |   |-- products/
    |   |-- stores/
    |   |-- orders/
    |   `-- search/
    `-- tests/
```

## Docker Setup

Start Django, PostgreSQL, Redis, Celery worker, and Celery beat:

```bash
docker-compose up --build
```

The web service automatically runs migrations, seeds dummy data (if not already seeded), and starts the API at:

```text
http://localhost:8000/
```

Run tests inside the container:

```bash
docker-compose exec web python manage.py test
```

## Environment Variables (.env)

The application reads configurations from the `.env` file located inside the `project/` subdirectory (`project/.env`). A template `.env` is provided:

```env
# Database Configurations
DB_NAME=ecommerce_system
DB_USER=postgres
DB_PASSWORD=password123
DB_HOST=localhost
DB_PORT=5432

# Redis and Celery configurations
USE_REDIS=False
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/1
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
```

### Key Settings:
- `DB_HOST`: Set to `localhost` or `127.0.0.1` for local running, and ensure your local PostgreSQL credentials match `DB_USER` and `DB_PASSWORD`.
- `USE_REDIS`: Set to `False` for local development if you do not have Redis installed. This activates an in-memory cache fallback and eager (synchronous) Celery task execution. When running inside Docker, this is automatically bypassed to use the docker containers.

## Local Setup

Install dependencies:

```bash
pip install -r project/requirements.txt
```

Apply migrations:

```bash
python manage.py migrate
```

Seed dummy data (first time or if you want to populate the database):

```bash
python manage.py seed_data
```

Run the API:

```bash
python manage.py runserver
```

Run Celery worker and beat in separate terminals:

```bash
celery -A project worker --loglevel=info
celery -A project beat --loglevel=info
```

## API Examples

Create an order:

```bash
curl -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "store_id": 1,
    "items": [
      {"product_id": 10, "quantity_requested": 5},
      {"product_id": 15, "quantity_requested": 2}
    ]
  }'
```

List store orders:

```bash
curl http://localhost:8000/stores/1/orders/
```

List store inventory:

```bash
curl http://localhost:8000/stores/1/inventory/
```

Search products:

```bash
curl "http://localhost:8000/api/search/products/?q=phone&store_id=1&in_stock=true&sort=relevance"
```

Autocomplete suggestions:

```bash
curl "http://localhost:8000/api/search/suggest/?q=pho"
```

## Redis Usage

Autocomplete suggestions are cached in Redis for five minutes using keys such as `suggest:q:<query>`.

The suggest endpoint also uses DRF throttling with a limit of 20 requests per minute per user/IP.

Product save/delete signals invalidate autocomplete cache keys so stale product titles are not served.

## Celery Usage

When an order is confirmed, `send_order_confirmation` is queued after the database transaction commits.

Celery beat is configured to run `generate_daily_inventory_summary` daily and log aggregate inventory metrics.

## Consistency Notes

Order creation uses `transaction.atomic()` and `select_for_update()` on inventory rows to avoid concurrent stock deduction races.

If any requested product has insufficient stock at the store, the order is created as `REJECTED` and no stock is deducted.

Duplicate product lines in a request are aggregated before stock validation and deduction.

## Scalability Considerations

1. **Database Indexing**:
   * Store and Product IDs are primary keys (auto-indexed).
   * A UniqueConstraint on `(store_id, product_id)` in the `Inventory` model automatically creates a compound index, speeding up lock acquisitions, joins, and order checkouts.
   * Product title search can be migrated to a PostgreSQL Trigram Index (`gin_trgm_ops`) or full-text search to maintain high performance under larger datasets.
2. **Redis Scaling**:
   * For heavy search query caching and rate limits, Redis can be clustered or run in a Sentinel replica configuration.
3. **Celery Worker Scaling**:
   * Celery workers can be scaled horizontally. Heavy background reports (like daily summary generation) can be directed to dedicated queues separate from lightweight tasks (like sending order confirmations).

---

## Interactive Documentation & Postman Collection

### 1. Swagger / OpenAPI Documentation
The project integrates `drf-spectacular` for generating OpenAPI 3.0 schemas. Visit these routes in your browser while the server is running:
- **Interactive Swagger UI**: [http://localhost:8000/api/docs/swagger/](http://localhost:8000/api/docs/swagger/)
- **Alternative Redoc UI**: [http://localhost:8000/api/docs/redoc/](http://localhost:8000/api/docs/redoc/)
- **Raw OpenAPI JSON Schema**: [http://localhost:8000/api/schema/](http://localhost:8000/api/schema/)

### 2. Postman Collection
A pre-configured Postman Collection is included in the workspace root:
- **File name**: [`Aforro_APIs.postman_collection.json`](file:///c:/Users/Rakes/OneDrive/Desktop/DSA/Afforo%20Assignment/Aforro_APIs.postman_collection.json)
- **Importing**: Open Postman, click **Import**, select this JSON file, and set the `base_url` variable to your host address (default: `http://localhost:8000`). It includes sample requests for all implemented endpoints.

---

## Assumptions & Technical Decisions

1. **Database Atomicity & Concurrency Protection**:
   * During `POST /orders/`, order creation, inventory checks, and stock deductions are performed inside a single `transaction.atomic()` block.
   * We apply `.select_for_update()` on relevant `Inventory` rows. This places a row-level update lock in PostgreSQL, preventing concurrent race conditions (like double-selling stock) when multiple checkouts occur for the same products simultaneously.
2. **Celery Worker & Cache Fallbacks**:
   * Setting `USE_REDIS=False` (default for local setups) dynamically shifts Django caching to an in-memory `LocMemCache` sandbox and tells Celery to execute tasks synchronously via `CELERY_TASK_ALWAYS_EAGER = True`. This allows running and testing the entire project locally without installing a Redis server, while using full Redis capabilities inside Docker container networks.
3. **Audit Trail**:
   * Orders are preserved as `REJECTED` along with their requested order lines in the database instead of being discarded. This retains a complete audit log of out-of-stock checkouts for supply chain analytics.
