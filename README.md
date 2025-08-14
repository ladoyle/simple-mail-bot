# TechNoise Mail Bot — README

This project automates Gmail label/rule management and collects processing statistics, exposed via a FastAPI service.

Contents
- Architecture and layers
- FastAPI usage
- Gmail API notes
- REST API reference (controllers)
- Local setup and run
- Background History Engine
- Data model (quick reference)


## Architecture and layers

The codebase follows a clear layering pattern:

- Controllers (HTTP layer)
    - Define REST endpoints with FastAPI routers.
    - Validate I/O via Pydantic models (request/response schemas).
    - Delegate business logic to services.
    - Examples: rule, label, and stats controllers.

- Services (business logic)
    - Encapsulate domain workflows such as creating rules/labels in Gmail and syncing to the local DB, computing statistics, and aggregating Gmail history.
    - Examples:
        - MailRuleService: CRUD and sync of Gmail filters with the EmailRule table.
        - MailLabelService: CRUD and sync of Gmail labels with the EmailLabel table.
        - MailStatsService: DB-based processed counts; Gmail-based read/unread counts.
        - HistoryEngine: background aggregator that reads Gmail history daily, maps events to rules, and writes EmailStatistic records.

- Backend database and client (infrastructure)
    - Database:
        - SQLAlchemy ORM, SQLite by default (sqlite:///.../mail_bot.db).
        - Models include EmailRule, EmailLabel, EmailStatistic.
    - Gmail client:
        - A thin wrapper over googleapiclient that manages OAuth, Gmail service initialization, and helper calls for labels, filters, counts, and history.
        - Maintains a local in-memory history cursor for incremental history retrieval.


## FastAPI usage

- Dependency Injection (DI):
    - Uses FastAPI Depends to inject shared resources (database session and GmailClient) into services and controller endpoints.
    - Each service exposes a get_*_service(...) provider that creates or returns a singleton service wired with the current Session and GmailClient.

- Lifespan / startup:
    - The background HistoryEngine can be initialized once at app startup using FastAPI’s lifespan context or startup event, then stopped on shutdown.
    - The scheduler runs an async loop that sleeps until the next 4:00 AM UTC and performs daily aggregation.

- Pydantic models:
    - Request/response models define the schema of inputs/outputs.
    - For ORM responses, Pydantic is configured with from_attributes = True, allowing direct serialization of ORM objects returned by services.

Example app entry (lifespan):

```python
# Python
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
    - The app uses InstalledAppFlow and stores tokens securely via keyring.
    - Scopes used:
        - https://www.googleapis.com/auth/gmail.labels
        - https://www.googleapis.com/auth/gmail.modify
        - https://www.googleapis.com/auth/gmail.settings.basic

- Key features used:
    - Labels API: list/get/create/delete system and custom labels.
    - Filters (rules) API: create/list/delete filters (rules that apply actions based on criteria).
    - Users profile: read messagesTotal (used for read count computation).
    - History API: incremental changes since a historyId (labelAdded/labelRemoved events) for daily aggregation.

- History handling:
    - The Gmail client retains an in-memory history cursor.
    - First call initializes the cursor using users.getProfile().historyId and returns no data (no backfill).
    - Subsequent calls return a bounded set of changes (assumed <= 500 per day), and the cursor advances.


## REST API reference (controllers)

Base path: / (service root)

- Rules controller (/rules)
    - GET /rules
        - Returns the list of rules from the database (synced with Gmail).
    - POST /rules
        - Body: RuleRequest
        - Action: Create filter in Gmail, persist to DB, returns new rule id.
    - DELETE /rules/{rule_id}
        - Deletes in Gmail first, then removes from DB.

Example create request:

```python
# Python
{
  "rule_name": "Move notifications",
  "criteria": "{\"from\":\"notify@example.com\"}",
  "addLabelIds": ["Label_123"],
  "removeLabelIds": ["INBOX"],
  "forward": ""
}
```


- Labels controller (/labels)
    - GET /labels
        - Lists labels from DB after syncing with Gmail.
    - POST /labels
        - Body: LabelRequest { name }
        - Creates a Gmail label and stores it in the DB.
    - DELETE /labels/{label_id}
        - Deletes label in Gmail, then from DB.

- Stats controller (/stats)
    - GET /stats/total_processed?rule_id={id}
        - Sum of EmailStatistic.processed for the rule across all time.
    - GET /stats/daily_processed?rule_id={id}
        - Sum for last 24 hours.
    - GET /stats/weekly_processed?rule_id={id}
        - Sum from start of week (Monday 00:00 UTC) to now.
    - GET /stats/monthly_processed?rule_id={id}
        - Sum from start of month (00:00 UTC on day 1) to now.
    - GET /stats/unread
        - Returns unread message count from Gmail.
    - GET /stats/read
        - Returns (total - unread) computed using Gmail totals.

Example responses:

```python
# Python
# GET /stats/total_processed?rule_id=42
{"processed": 128}

# GET /stats/unread
{"unread": 17}

# GET /stats/read
{"read": 2034}
```



## Local setup and run

1) Install dependencies (Python 3.9+ recommended)
- Use virtualenv per your project tooling.
- Ensure packages like fastapi, uvicorn, sqlalchemy, google-auth, google-api-python-client, keyring, pydantic are installed as required by your environment.

2) Configure OAuth credentials
- Place credentials.json in the working directory for InstalledAppFlow.
- First run will prompt authorization and securely store tokens via keyring.

3) Run the API server

```shell script
# Bash
uvicorn main:app --reload
```


4) Explore docs
- Open http://127.0.0.1:8000/docs for Swagger UI.
- Open http://127.0.0.1:8000/redoc for ReDoc.

5) Verify background engine
- Look for startup logs indicating the History Engine scheduled its next run.
- Optionally enable an initial run at startup (see the comments in HistoryEngine.start()).


## Background History Engine

- Runs daily at 04:00 UTC.
- Loads EmailRule entries and creates a mapping of labelIds to rule_ids.
- Calls gmail_client.list_history(...) to retrieve labelAdded/labelRemoved events since the last run.
- For each rule, counts unique messages that had matching label changes (deduplicated per rule).
- Persists a record in EmailStatistic with the current timestamp and processed count.

This approach yields accurate “processed” totals that your Stats API can aggregate by day/week/month.


## Data model (quick reference)

- EmailRule
    - id (PK)
    - gmail_id (filter id in Gmail)
    - name
    - criteria (stringified JSON of Gmail criteria)
    - addLabelIds (JSON array of label ids)
    - removeLabelIds (JSON array of label ids)
    - forward (email address or empty)

- EmailLabel
    - id (PK)
    - gmail_id
    - name

- EmailStatistic
    - timestamp (epoch seconds, PK)
    - processed (int)
    - rule_id (FK-like reference to EmailRule.id)
    - rule_name (denormalized for convenience)
