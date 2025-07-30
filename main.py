from fastapi import FastAPI

import controllers as ctrls

app = FastAPI()
app.include_router(ctrls.mail_bot_label_controller.stats_router)
app.include_router(ctrls.mail_bot_rule_controller.label_router)
app.include_router(ctrls.mail_bot_stats_controller.rule_router)
# Create database tables
Base.metadata.create_all(bind=engine)
# Create services
mail_service = MailService()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
    