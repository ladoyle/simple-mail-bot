from fastapi import APIRouter
from fastapi.params import Depends

from service.mail_stats_service import MailStatsService, get_stats_service

stats_router = APIRouter(prefix="/stats")

@stats_router.get("/total_processed")
def get_total_processed(rule_id: int, mail_stats_service: MailStatsService = Depends(get_stats_service)):
    return {"processed": mail_stats_service.get_total_processed(rule_id)}

@stats_router.get("/daily_processed")
def get_daily_processed(rule_id: int, mail_stats_service: MailStatsService = Depends(get_stats_service)):
    return {"processed": mail_stats_service.get_daily_processed(rule_id)}

@stats_router.get("/weekly_processed")
def get_weekly_processed(rule_id: int, mail_stats_service: MailStatsService = Depends(get_stats_service)):
    return {"processed": mail_stats_service.get_weekly_processed(rule_id)}

@stats_router.get("/monthly_processed")
def get_monthly_processed(rule_id: int, mail_stats_service: MailStatsService = Depends(get_stats_service)):
    return {"processed": mail_stats_service.get_monthly_processed(rule_id)}

@stats_router.get("/unread")
def get_unread(mail_stats_service: MailStatsService = Depends(get_stats_service)):
    return {"unread": mail_stats_service.get_unread_count()}

@stats_router.get("/read")
def get_read(mail_stats_service: MailStatsService = Depends(get_stats_service)):
    return {"read": mail_stats_service.get_read_count()}