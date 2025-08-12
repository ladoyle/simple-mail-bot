from fastapi import FastAPI

from controllers import mail_bot_label_controller as label_ctrl
from controllers import mail_bot_rule_controller as rule_ctrl
from controllers import mail_bot_stats_controller as stats_ctrl


app = FastAPI()
app.include_router(label_ctrl.label_router)
app.include_router(rule_ctrl.rule_router)
app.include_router(stats_ctrl.stats_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)
    