from fastapi import APIRouter, HTTPException
from models.mail_bot_schemas import LabelRequest, RuleRequest
from service.mail_rule_service import MailService

stats_router = APIRouter(prefix="/stats")

@stats_router.get("/total_processed")
def get_total_processed():
    return {"processed": mail_service.get_total_processed()}

@stats_router.get("/daily_processed")
def get_daily_processed():
    return {"processed": mail_service.get_daily_processed()}

@stats_router.get("/weekly_processed")
def get_weekly_processed():
    return {"processed": mail_service.get_weekly_processed()}

@stats_router.get("/monthly_processed")
def get_monthly_processed():
    return {"processed": mail_service.get_monthly_processed()}

@stats_router.get("/unread")
def get_unread():
    return {"unread": mail_service.get_unread_count()}

@stats_router.get("/read")
def get_read():
    return {"read": mail_service.get_read_count()}