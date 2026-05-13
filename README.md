# AI Support Desk

AI Support Desk is a small backend project for handling customer support tickets. It shows how to combine FastAPI, PostgreSQL, Celery, Redis, LangGraph and Alembic in one application.

The main goal of the project is to accept a ticket, save it in the database, analyze it in the background and store the analysis result.

---

## Features

- Create support tickets with `POST /tickets`
- List tickets with `GET /tickets`
- Read one ticket with `GET /tickets/{ticket_id}`
- Validate request and response data with Pydantic
- Store tickets in PostgreSQL with SQLAlchemy
- Run ticket analysis asynchronously with Celery
- Use Redis as the Celery queue and result backend
- Analyze tickets through a LangGraph workflow
- Manage database schema changes with Alembic
- Prepare read-only MCP access for ticket data

---

## Architecture

```text
Client / Swagger
      |
      v
FastAPI API
      |
      v
PostgreSQL
      |
      v
Celery task -> Redis queue -> Celery worker
                              |
                              v
                           LangGraph
                              |
                              v
                       PostgreSQL update

MCP server -> read-only ticket access
```

### Ticket flow

```text
POST /tickets
    |
    v
create_ticket_endpoint()
    |
    v
create_ticket()
    |
    v
Ticket saved in PostgreSQL with status = "pending"
    |
    v
analyze_ticket.delay(ticket.id)
    |
    v
Redis queue
    |
    v
Celery worker runs analyze_ticket(ticket_id)
    |
    v
build_ticket_graph()
    |
    v
LangGraph workflow
    |
    v
update_ticket_analysis()
    |
    v
Ticket updated in PostgreSQL
```
---

## How to run

### 1. Build and start containers

```bash
docker compose up --build
```

This starts:

- FastAPI API
- Celery worker
- PostgreSQL
- Redis

---

### 2. Create an Alembic migration

```bash
docker compose exec api alembic revision --autogenerate -m "create tickets table"
```

---

### 3. Apply migrations

```bash
docker compose exec api alembic upgrade head
```

---

### 4. Open Swagger UI

```text
http://localhost:8000/docs
```

---

## Example request

```http
POST /tickets
Content-Type: application/json
```

```json
{
  "customer_email": "customer@example.com",
  "subject": "Problem with delivery",
  "message": "My package has not arrived yet and the tracking number does not work."
}
```

After creating the ticket, the API returns quickly. The ticket analysis runs in the Celery worker in the background.

Check the result with:

```http
GET /tickets/{ticket_id}
```
---

## Important files and functions

### `app/main.py`

Creates the FastAPI application and registers routes.

Important code:

```python
app.include_router(tickets_router)
```

---

### `app/api/tickets.py`

Defines ticket API endpoints.

Important functions:

- `create_ticket_endpoint()` handles `POST /tickets`
- `list_tickets_endpoint()` handles `GET /tickets`
- `get_ticket_endpoint()` handles `GET /tickets/{ticket_id}`

The most important line is:

```python
analyze_ticket.delay(ticket.id)
```

It sends the ticket analysis to Celery instead of running it inside the HTTP request.

---

### `app/services/ticket_service.py`

Contains ticket database logic.

Important functions:

- `create_ticket()` creates a ticket with status `pending`
- `get_ticket()` returns one ticket by ID
- `list_tickets()` returns all tickets
- `update_ticket_analysis()` saves the analysis result

---

### `app/tasks/ticket_tasks.py`

Contains the Celery background task.

Important function:

```python
analyze_ticket(ticket_id)
```

It is called from the API using:

```python
analyze_ticket.delay(ticket.id)
```

Inside this task:

1. the worker loads the ticket from PostgreSQL,
2. sets the status to `processing`,
3. calls `build_ticket_graph()`,
4. runs the LangGraph workflow with `graph.invoke(...)`,
5. saves the final analysis with `update_ticket_analysis()`.

---

### `app/graphs/ticket_graph.py`

Contains the LangGraph workflow.

Important functions:

- `build_ticket_graph()` builds and compiles the workflow
- `classify_ticket()` detects the ticket category
- `assign_priority()` assigns priority
- `draft_reply()` creates a draft response
- `decide_human_review()` decides if a human should review the ticket

Workflow:

```text
START
  |
  v
classify_ticket
  |
  v
assign_priority
  |
  v
draft_reply
  |
  v
decide_human_review
  |
  v
END
```

`build_ticket_graph()` is called in `analyze_ticket()`.

---

### `app/models/ticket.py`

Defines the SQLAlchemy `Ticket` model and the `tickets` table.

The table stores:

- customer email
- subject
- message
- status
- category
- priority
- draft reply
- human review flag
- timestamps

---

### `app/schemas/ticket.py`

Defines Pydantic schemas.

- `TicketCreate` is used for input data
- `TicketResponse` is used for full ticket responses
- `TicketListItem` is used for list responses

---

### `app/core/settings.py`

Loads configuration from environment variables and `.env`.

Important function:

```python
get_settings()
```

It is used by the API, database setup and Celery setup.

---

### `alembic/env.py`

Configures Alembic migrations.

It loads `DATABASE_URL` from `.env` and gives Alembic access to SQLAlchemy models through:

```python
target_metadata = Base.metadata
```

Alembic uses this to generate and apply database migrations.



