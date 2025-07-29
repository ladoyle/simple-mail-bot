from fastapi import FastAPI
from controllers import mail_bot_controller

app = FastAPI()
app.include_router(mail_bot_controller.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
    