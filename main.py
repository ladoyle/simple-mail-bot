from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from controllers import mail_bot_oauth_controller as oauth_ctrl
from controllers import mail_bot_label_controller as label_ctrl
from controllers import mail_bot_rule_controller as rule_ctrl
from controllers import mail_bot_stats_controller as stats_ctrl
from service.mail_history_engine_service import get_history_engine_service
from backend import database
from backend.gmail_client import get_gmail_client

import logging


@asynccontextmanager
async def lifespan(bot_app: FastAPI):
    db = next(database.get_db())
    gmail_client = get_gmail_client()
    engine = get_history_engine_service(db=db, gmail_client=gmail_client)
    engine.start()
    try:
        yield
    finally:
        engine.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(oauth_ctrl.oauth_router)
app.include_router(label_ctrl.label_router)
app.include_router(rule_ctrl.rule_router)
app.include_router(stats_ctrl.stats_router)

origins = [
    "http://localhost:5000",  # Example frontend URL
    "https://your-frontend-domain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,  # Disallow cookies and authorization headers
    allow_methods=["*"],     # Allow all HTTP methods (GET, POST, PUT, etc.)
    allow_headers=["*"],     # Allow all headers
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


if __name__ == "__main__":
    import uvicorn
    from util.util import print_startup_banner

    print_startup_banner()
    uvicorn.run("main:app", host="127.0.0.1", port=5000, reload=True)
