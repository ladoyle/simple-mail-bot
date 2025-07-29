from fastapi import APIRouter, HTTPException
from models.mail_bot_schemas import LabelRequest, RuleRequest
from service.mail_service import MailService

router = APIRouter()
mail_service = MailService()
emails = {}
rules = []
stats = {"processed": 0, "unread": 0, "read": 0}


@router.post("/label_email")
def label_email(req: LabelRequest):
    label_id = mail_service.label_email(req.email_id, req.label)
    return {"message": f'Email {req.email_id} labeled with {req.label}', "label_id": label_id}

@router.post("/create_rule")
def create_rule(req: RuleRequest):
    rule_id = mail_service.add_rule(req.rule_name, req.condition, req.action)
    return {"message": f'Rule {req.rule_name} created successfully', "rule_id": rule_id.id}

@router.get("/stats/total_processed")
def get_total_processed():
    return {"processed": mail_service.get_total_processed()}

@router.get("/stats/daily_processed")
def get_daily_processed():
    return {"processed": mail_service.get_daily_processed()}

@router.get("/stats/weekly_processed")
def get_weekly_processed():
    return {"processed": mail_service.get_weekly_processed()}

@router.get("/stats/monthly_processed")
def get_monthly_processed():
    return {"processed": mail_service.get_monthly_processed()}

@router.get("/stats/unread")
def get_unread():
    return {"unread": mail_service.get_unread_count()}

@router.get("/stats/read")
def get_read():
    return {"read": mail_service.get_read_count()}