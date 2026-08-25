# Backend Developer Assignment

A Django REST Framework backend for store inventory management, order processing, product search and autocomplete, Redis caching and rate limiting, Celery background jobs, and Dockerized development.

## Features

* Store and inventory management
* Product management
* Order creation and stock validation
* Transaction-safe inventory deduction
* Product search and autocomplete
* Redis-based caching
* API rate limiting
* Celery background tasks
* Daily inventory summary
* PostgreSQL database
* Swagger / OpenAPI documentation
* Postman API collection
* Docker and Docker Compose support
* Automated tests

---

## Project Structure

```text
Backend_Developer_Assignment/
│
├── project/
│   ├── apps/
│   │   ├── products/
│   │   ├── stores/
│   │   ├── orders/
│   │   └── search/
│   │
│   ├── tests/
│   ├── __init__.py
│   ├── asgi.py
│   ├── celery_app.py
│   ├── requirements.txt
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── manage.py
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .gitignore
├── APIs_postman_collection.json
└── README.md
```

---

## Tech Stack

* **Python**
* **Django**
* **Django REST Framework**
* **PostgreSQL**
* **Redis**
* **Celery**
* **Docker**
* **Docker Compose**
* **drf-spectacular**
* **Postman**

---

# Docker Setup

Docker Compose is provided to run the application and its supporting services.

The stack includes:

* Django application
* PostgreSQL
* Redis
* Celery worker
* Celery Beat

### Start the application

From the repository root:

```bash
docker-compose up --build
```

The API will be available at:

```text
http://localhost:8000/
```

### Stop the containers

```bash
docker-compose down
```

### Run tests inside the web container

```bash
docker-compose exec web python manage.py test
```

---

# Environment Variables

The application uses environment variables for database, Redis, and Celery configuration.

Example configuration:

```env
# Database
DB_NAME=ecommerce_system
DB_USER=postgres
DB_PASSWORD=password123
DB_HOST=localhost
DB_PORT=5432

# Redis and Celery
USE_REDIS=False
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/1
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
```

### Important settings

`DB_HOST`

For local development, use:

```text
localhost
```

or:

```text
127.0.0.1
```

When connecting to PostgreSQL from Docker, the database service hostname should be used according to the Docker Compose configuration.

`USE_REDIS`

Set:

```env
USE_REDIS=False
```

for local development when Redis is not available.

In this mode, the application can use an in-memory cache and synchronous Celery task execution for local development and testing.

When running through Docker Compose, Redis is used by the application according to the Docker configuration.

> Do not commit real production credentials or sensitive secrets to the repository.

---

# Local Development Setup

## 1. Create and activate a virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

Linux / macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

## 2. Install dependencies

From the repository root:

```bash
pip install -r project/requirements.txt
```

## 3. Configure environment variables

Create/configure the required `.env` file according to the environment variables described above.

## 4. Apply migrations

```bash
python manage.py migrate
```

## 5. Seed dummy data

To populate the database with sample data:

```bash
python manage.py seed_data
```

## 6. Start the Django development server

```bash
python manage.py runserver
```

The API will be available at:

```text
http://localhost:8000/
```

---

# Celery

Celery is used for background processing.

## Start Celery worker

Run from the repository root:

```bash
celery -A project worker --loglevel=info
```

## Start Celery Beat

Run in a separate terminal:

```bash
celery -A project beat --loglevel=info
```

When using Docker Compose, the Celery worker and Celery Beat services are started as part of the Docker environment.

---

# API Examples

## Create an Order

```bash
curl -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "store_id": 1,
    "items": [
      {
        "product_id": 10,
        "quantity_requested": 5
      },
      {
        "product_id": 15,
        "quantity_requested": 2
      }
    ]
  }'
```

## List Store Orders

```bash
curl http://localhost:8000/stores/1/orders/
```

## List Store Inventory

```bash
curl http://localhost:8000/stores/1/inventory/
```

## Search Products

```bash
curl "http://localhost:8000/api/search/products/?q=phone&store_id=1&in_stock=true&sort=relevance"
```

## Autocomplete Suggestions

```bash
curl "http://localhost:8000/api/search/suggest/?q=pho"
```

> The exact API routes and request schemas can also be viewed in the Swagger documentation and Postman collection.

---

# Redis Usage

Redis is used for caching and rate limiting.

### Autocomplete caching

Autocomplete suggestions are cached in Redis for five minutes.

Example cache key:

```text
suggest:q:<query>
```

### Rate limiting

The autocomplete endpoint uses Django REST Framework throttling with a limit of:

```text
20 requests per minute per user/IP
```

### Cache invalidation

Product save and delete operations invalidate relevant autocomplete cache entries to prevent stale product titles from being returned.

---

# Celery Usage

Celery is used for asynchronous background processing.

### Order confirmation

When an order is confirmed, the `send_order_confirmation` task is queued after the database transaction successfully commits.

This ensures that the background task is not executed for a transaction that later rolls back.

### Daily inventory summary

Celery Beat schedules:

```text
generate_daily_inventory_summary
```

to run daily and generate aggregate inventory metrics.

---

# Database Consistency and Concurrency

Order creation uses Django's transaction management to maintain database consistency.

The order creation process uses:

```python
transaction.atomic()
```

and:

```python
select_for_update()
```

on relevant inventory rows.

This provides row-level locking in PostgreSQL and helps prevent concurrent requests from deducting the same inventory simultaneously.

### Insufficient stock

If any requested product has insufficient stock at the selected store:

* The order is created with status `REJECTED`.
* No inventory is deducted.
* The requested order information is retained for auditing.

### Duplicate product lines

Duplicate product entries within the same order request are aggregated before stock validation and inventory deduction.

---

# Database Indexing

The application uses database indexes to improve query performance.

* Store and Product primary keys are automatically indexed.
* The `Inventory` model uses a uniqueness constraint for the store/product combination.
* Inventory lookups and order processing can therefore efficiently identify the relevant inventory record.

For larger-scale deployments, product title search can be further optimized using PostgreSQL features such as:

* Trigram indexes (`gin_trgm_ops`)
* PostgreSQL full-text search
* A dedicated search engine when search requirements grow significantly

---

# Scalability Considerations

## Redis Scaling

For high-volume caching and rate limiting, Redis can be scaled using:

* Redis Cluster
* Redis Sentinel
* Replication

## Celery Scaling

Celery workers can be scaled horizontally based on workload.

Background tasks can also be separated into dedicated queues. For example:

* Lightweight order confirmation tasks
* Heavy inventory reporting tasks

This allows different workloads to be scaled independently.

## Database Scaling

For larger workloads, PostgreSQL performance can be improved through:

* Appropriate indexes
* Query optimization
* Connection pooling
* Read replicas
* Database monitoring

---

# Interactive API Documentation

The project integrates `drf-spectacular` for OpenAPI documentation.

Start the application and open:

### Swagger UI

```text
http://localhost:8000/api/docs/swagger/
```

### ReDoc

```text
http://localhost:8000/api/docs/redoc/
```

### OpenAPI Schema

```text
http://localhost:8000/api/schema/
```

These endpoints provide interactive documentation and allow API requests to be tested directly from the browser.

---

# Postman Collection

A pre-configured Postman collection is included in the repository:

```text
Aforro_APIs.postman_collection.json
```

The collection is located at the repository root.

### Import the collection

1. Open Postman.
2. Select **Import**.
3. Select:

```text
Aforro_APIs.postman_collection.json
```

4. Import the collection.
5. Configure the `base_url` variable if required.

Default base URL:

```text
http://localhost:8000
```

The collection contains sample requests for the implemented API endpoints.

---

# Testing

Run the Django test suite locally:

```bash
python manage.py test
```

Or run the tests inside Docker:

```bash
docker-compose exec web python manage.py test
```

The tests cover the implemented application functionality and API behavior.

---

# Assumptions and Technical Decisions

## 1. Database Atomicity

Order creation, inventory validation, and stock deduction are performed within a single database transaction.

```python
transaction.atomic()
```

This ensures that inventory changes are committed consistently.

## 2. Row-Level Locking

Relevant inventory records are locked using:

```python
select_for_update()
```

This prevents concurrent order requests from causing stock deduction races.

## 3. Redis Fallback

When Redis is disabled for local development, the application can fall back to Django's in-memory cache and synchronous Celery task execution.

This allows the project to be developed and tested without requiring a separate Redis installation.

## 4. Order Audit Trail

Rejected orders are preserved in the database together with their requested order lines.

This provides an audit trail for unsuccessful checkout attempts and can be useful for inventory and supply-chain analysis.

## 5. Dockerized Development

Docker Compose provides a consistent development environment containing the required application services and infrastructure dependencies.

---

# Running the Project Quickly

The easiest way to run the complete environment is:

```bash
docker-compose up --build
```

Then open:

```text
http://localhost:8000/
```

Swagger documentation:

```text
http://localhost:8000/api/docs/swagger/
```

ReDoc:

```text
http://localhost:8000/api/docs/redoc/
```

---

# Submission Notes

This repository contains the complete backend implementation along with:

* Django REST APIs
* PostgreSQL database integration
* Redis caching and rate limiting
* Celery background processing
* Docker configuration
* Automated tests
* Swagger/OpenAPI documentation
* Postman API collection

The root `README.md` serves as the primary project documentation.
