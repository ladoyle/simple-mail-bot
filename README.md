# My Email Rules Server — README

This project automates Gmail label/filter management and collects processing statistics, exposed via a FastAPI service.

## Summary

A Python FastAPI application for managing Gmail filters and labels with background aggregation of email processing statistics.  
It uses SQLAlchemy for persistence, Google API for Gmail integration, and supports daily background jobs for statistics.

## Key features

Primary feature of the My Email Rules Server is the History Engine, which runs daily to aggregate email processing statistics based on Gmail label changes.

The History Engine is a background service that automatically aggregates activity for all authorized users every day at 04:00 UTC. Its main purpose is to track how many emails matched each rule (filter) by analyzing Gmail's history of label changes. For each user, it:
Loads all EmailRule entries and builds a mapping from Gmail label IDs to rule IDs.
Uses the Gmail API to fetch incremental history events (label additions/removals) since the last processed point, ensuring no duplicate processing.
For each rule, counts unique messages that had relevant label changes, so each message is only counted once per rule per run.
Persists a summary record in the EmailStatistic table, including the timestamp, processed count, rule ID, rule name, and user email.
Updates the user's last_history_id to mark progress and avoid reprocessing the same events.

This engine enables automated, reliable statistics collection on rule activity, supporting analytics and monitoring for Gmail automation workflows.

## Architecture and layers

The codebase follows a clear layering pattern:

- Controllers (HTTP layer)
    - Define REST endpoints with FastAPI routers.
    - Validate I/O via Pydantic models (request/response schemas).
    - Delegate business logic to services.

- Services (business logic)
    - Encapsulate domain workflows such as creating rules/labels in Gmail and syncing to the local DB, computing statistics, and aggregating Gmail history.

- Backend database and client (infrastructure)
    - Database: SQLAlchemy ORM, SQLite by default.
    - Gmail client: Wrapper over googleapiclient for OAuth and Gmail operations.

## FastAPI usage

- Dependency Injection (DI):
    - Uses FastAPI Depends to inject shared resources (database session and GmailClient) into services and controller endpoints.

- Lifespan / startup:
    - The background HistoryEngine is initialized at app startup and stopped on shutdown.

- Pydantic models:
    - Request/response models define the schema of inputs/outputs.
    - ORM responses are serialized directly using `from_attributes = True`.

Example app entry (lifespan):

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend import database
from backend.gmail_client import get_gmail_client
from service.mail_history_engine_service import get_history_engine_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = next(database.get_db())
    gmail_client = get_gmail_client()
    engine = get_history_engine_service(db=db, gmail_client=gmail_client)
    engine.start()
    try:
        yield
    finally:
        engine.stop()

app = FastAPI(lifespan=lifespan)
```

## Gmail API notes

- OAuth and scopes:
    - Uses InstalledAppFlow and stores tokens securely via keyring.
    - Scopes:
        - https://www.googleapis.com/auth/gmail.labels
        - https://www.googleapis.com/auth/gmail.modify
        - https://www.googleapis.com/auth/gmail.settings.basic

- Key features used:
    - Labels API, Filters (rules) API, Users profile, History API.

- History handling:
    - The Gmail client retains an in-memory history cursor for incremental sync.

## Local setup and run

1) **Install dependencies** (Python 3.9+ recommended)
- Use virtualenv per your project tooling.
- Ensure packages like fastapi, uvicorn, sqlalchemy, google-auth, google-api-python-client, keyring, pydantic are installed.

2) **Configure OAuth credentials**
- Place `credentials.json` in the working directory for InstalledAppFlow.
- First run will prompt authorization and securely store tokens via keyring.

3) **Environment configuration:**
   Configure `.env.{APP_ENV}` file by setting run configuration to include environment variable `APP_ENV=local` (default: `local`)
   Set the following environment variables as needed (see `.env.local` for reference):

- `HOST_URL`: Host address for the server (default: `localhost`)
- `PORT`: Port for the server (default: `5000`)
- `ORIGIN`: Allowed CORS origin (default: `http://localhost:5000`)
- `SSL_KEY_PATH`: Path to SSL key file (default: empty)
- `SSL_CERT_PATH`: Path to SSL certificate file (default: empty)
- `APP_RELOAD`: Enable auto-reload for development (default: `true`)
- `DEBUG`: Enable debug mode (default: `true`)
- `GMAIL_REDIRECT_URI`: OAuth redirect URI for Gmail (default: `http://localhost:5000/v1/oauth/callback`)


4) **Run the API server**

```
python3 main.py
```

5) **Explore docs**
- Open http://127.0.0.1:8000/docs for Swagger UI.
- Open http://127.0.0.1:8000/redoc for ReDoc.

6) **Verify background engine**
- Look for startup logs indicating the History Engine scheduled its next run.

## Background History Engine

- Runs daily at 04:00 UTC (configurable).
- Loads EmailRule entries and creates a mapping of labelIds to rule_ids.
- Calls gmail_client.list_history(...) to retrieve labelAdded/labelRemoved events since the last run.
- For each rule, counts unique messages that had matching label changes.
- Persists a record in EmailStatistic with the current timestamp and processed count.

## Data model (quick reference)

- EmailStatistic
    - id (PK, int)
    - email_address (PK, str)
    - timestamp (int)
    - processed (int)
    - rule_id (int, not null)
    - rule_name (str, not null)

- EmailRule
    - id (PK, int)
    - email_address (str)
    - gmail_id (str, not null)
    - name (str)
    - criteria (str)
    - addLabelIds (JSON, not null)
    - removeLabelIds (JSON, not null)
    - forward (str)

- EmailLabel
    - id (PK, int)
    - email_address (str)
    - gmail_id (str, not null)
    - name (str, not null)
    - text_color (str)
    - background_color (str)

- AuthorizedUsers
    - id (unique, int)
    - email (PK, str)
    - last_history_id (str - from Gmail profile)
