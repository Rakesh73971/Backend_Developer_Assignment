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
│   ├── .env
│   ├── .env.example
│   ├── asgi.py
│   ├── celery_app.py
│   ├── requirements.txt
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── .dockerignore
├── .gitignore
├── APIs_postman_collection.json
├── docker-compose.yml
├── Dockerfile
├── manage.py
└── README.md
```

> **Note:** `project/.env` is a local environment file and should not be committed to the repository. `project/.env.example` is provided as a configuration template. Celery-generated files such as `celerybeat-schedule` and Python `__pycache__` directories are runtime/generated files and are not part of the source structure.

---

# Quick Start with Docker

Docker Compose provides the easiest way to run the complete application environment.

The Docker environment includes:

* Django web application
* PostgreSQL database
* Redis
* Celery worker
* Celery Beat

From the repository root, run:

```bash
docker-compose up --build
```

The API will be available at:

```text
http://localhost:8000/
```

### Stop the application

```bash
docker-compose down
```

### Run tests inside Docker

```bash
docker-compose exec web python manage.py test
```

---

# Environment Configuration

The project uses environment variables for PostgreSQL, Redis, and Celery configuration.

A template is provided at:

```text
project/.env.example
```

Create your local `.env` file from the example.

### Windows

```bash
copy project\.env.example project\.env
```

### Linux / macOS

```bash
cp project/.env.example project/.env
```

Then update the values in:

```text
project/.env
```

### Example configuration

```env
# Database Configuration
DB_NAME=ecommerce_system
DB_USER=postgres
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=5432

# Redis Configuration
USE_REDIS=False
REDIS_URL=redis://127.0.0.1:6379/0

# Celery Configuration
CELERY_BROKER_URL=redis://127.0.0.1:6379/1
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
```

### Important

The actual `.env` file may contain local credentials and should not be committed.

The repository provides `.env.example` so that another developer can create their own environment configuration.

---

# Local Development Setup

## 1. Create a virtual environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

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

Create:

```text
project/.env
```

using:

```text
project/.env.example
```

and update the values for your local environment.

## 4. Apply database migrations

```bash
python manage.py migrate
```

## 5. Seed sample data

```bash
python manage.py seed_data
```

## 6. Start the Django server

```bash
python manage.py runserver
```

The API will be available at:

```text
http://localhost:8000/
```

---

# Celery Setup

Celery is used for background processing and scheduled jobs.

## Start Celery Worker

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

The complete API schema and request/response details are available through the Swagger documentation and Postman collection.

---

# Redis and Rate Limiting

Redis is used for caching and API rate limiting.

## Autocomplete Caching

Autocomplete suggestions are cached in Redis for five minutes.

Example cache key:

```text
suggest:q:<query>
```

## Rate Limiting

The autocomplete endpoint uses Django REST Framework throttling with a limit of:

```text
20 requests per minute per user/IP
```

## Cache Invalidation

Product save and delete operations invalidate relevant autocomplete cache entries so that stale product titles are not served.

---

# Celery Background Jobs

Celery is used for asynchronous background processing.

## Order Confirmation

When an order is confirmed, the:

```text
send_order_confirmation
```

task is queued after the database transaction successfully commits.

This ensures that the background task is not executed if the surrounding database transaction is rolled back.

## Daily Inventory Summary

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

together with:

```python
select_for_update()
```

on relevant inventory rows.

This provides row-level locking in PostgreSQL and helps prevent concurrent requests from deducting the same inventory simultaneously.

## Insufficient Stock

If any requested product has insufficient stock at the selected store:

* The order is created with status `REJECTED`.
* No inventory is deducted.
* The requested order information is retained for auditing.

## Duplicate Product Lines

Duplicate product entries within the same order request are aggregated before stock validation and inventory deduction.

---

# Database Indexing

The application uses database constraints and indexes to improve query performance.

* Store and Product primary keys are automatically indexed.
* The `Inventory` model uses a uniqueness constraint for the store/product combination.
* Inventory lookups and order processing can efficiently identify the relevant inventory record.

For larger datasets, product title search can be further optimized using PostgreSQL features such as:

* Trigram indexes (`gin_trgm_ops`)
* PostgreSQL full-text search
* A dedicated search engine if search requirements grow significantly

---

# Interactive API Documentation

The project integrates `drf-spectacular` for OpenAPI documentation.

Start the application and open the following URLs.

## Swagger UI

```text
http://localhost:8000/api/docs/swagger/
```

## ReDoc

```text
http://localhost:8000/api/docs/redoc/
```

## OpenAPI Schema

```text
http://localhost:8000/api/schema/
```

Swagger UI provides an interactive interface for exploring and testing the API endpoints.

---

# Postman Collection

A pre-configured Postman collection is included in the repository root:

```text
APIs_postman_collection.json
```

## Import the Collection

1. Open Postman.
2. Select **Import**.
3. Select `APIs_postman_collection.json`.
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

The test suite covers the implemented application functionality and API behavior.

---

# Scalability Considerations

## Redis Scaling

For high-volume caching and rate limiting, Redis can be scaled using:

* Redis Cluster
* Redis Sentinel
* Replication

## Celery Scaling

Celery workers can be scaled horizontally based on workload.

Background tasks can also be separated into dedicated queues, for example:

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

# Assumptions and Technical Decisions

## 1. Database Atomicity

Order creation, inventory validation, and stock deduction are performed within a single database transaction using:

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

When Redis is disabled for local development, the application can use Django's in-memory cache and synchronous Celery task execution.

This allows the project to be developed and tested locally without requiring a separate Redis installation.

## 4. Order Audit Trail

Rejected orders are preserved in the database together with their requested order lines.

This provides an audit trail for unsuccessful checkout attempts and can be useful for inventory and supply-chain analysis.

## 5. Dockerized Development

Docker Compose provides a consistent development environment containing the application and its infrastructure dependencies.

---

# Submission

This repository contains the complete backend implementation with:

* Django REST APIs
* PostgreSQL database integration
* Redis caching and rate limiting
* Celery background processing
* Docker and Docker Compose configuration
* Automated tests
* Swagger / OpenAPI documentation
* Postman API collection
* Environment configuration template

The root `README.md` is the primary documentation for the project.
