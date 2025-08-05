from fastapi import FastAPI

import service
import controllers as ctrls

app = FastAPI()
app.include_router(ctrls.mail_bot_label_controller.label_router)
app.include_router(ctrls.mail_bot_rule_controller.rule_router)
app.include_router(ctrls.mail_bot_stats_controller.stats_router)
# Create database tables
Base.metadata.create_all(bind=engine)

# Global instance pool

## Service Instances
mail_label_service = None

## Gmail Client Instance
gmail_client = None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
    