from fastapi import APIRouter, HTTPException
from models.mail_bot_schemas import LabelRequest, RuleRequest

router = APIRouter()
emails = {}
rules = []
stats = {"processed": 0, "unread": 0, "read": 0}


@router.post("/label_email")
def label_email(req: LabelRequest):
    if req.email_id not in emails:
        raise HTTPException(status_code=404, detail="Email not found")
    emails[req.email_id]["label"] = req.label
    return {"message": "Label applied"}

@router.post("/create_rule")
def create_rule(req: RuleRequest):
    rules.append(req.model_dump())
    return {"message": "Rule created"}

@router.get("/stats/processed")
def get_processed():
    return {"processed": stats["processed"]}

@router.get("/stats/unread")
def get_unread():
    return {"unread": stats["unread"]}

@router.get("/stats/read")
def get_read():
    return {"read": stats["read"]}