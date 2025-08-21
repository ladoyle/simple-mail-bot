import logging as log
from fastapi import APIRouter, Header
from fastapi.params import Depends

from service.mail_stats_service import MailStatsService, get_stats_service

stats_router = APIRouter(prefix="/stats")

@stats_router.get("/total_processed")
def get_total_processed(
        ruleId: int,
        user_email: str = Header(..., alias="user-email"),
        mail_stats_service: MailStatsService = Depends(get_stats_service)
):
    log.info(f"Getting total processed for rule={ruleId}")
    return {"processed": mail_stats_service.get_total_processed(user_email, ruleId)}

@stats_router.get("/daily_processed")
def get_daily_processed(
        ruleId: int,
        user_email: str = Header(..., alias="user-email"),
        mail_stats_service: MailStatsService = Depends(get_stats_service)
):
    log.info(f"Getting daily processed for rule={ruleId}")
    return {"processed": mail_stats_service.get_daily_processed(user_email, ruleId)}

@stats_router.get("/weekly_processed")
def get_weekly_processed(
        ruleId: int,
        user_email: str = Header(..., alias="user-email"),
        mail_stats_service: MailStatsService = Depends(get_stats_service)
):
    log.info(f"Getting weekly processed for rule={ruleId}")
    return {"processed": mail_stats_service.get_weekly_processed(user_email, ruleId)}

@stats_router.get("/monthly_processed")
def get_monthly_processed(
        ruleId: int,
        user_email: str = Header(..., alias="user-email"),
        mail_stats_service: MailStatsService = Depends(get_stats_service)
):
    log.info(f"Getting monthly processed for rule={ruleId}")
    return {"processed": mail_stats_service.get_monthly_processed(user_email, ruleId)}

@stats_router.get("/unread")
def get_unread(
        user_email: str = Header(..., alias="user-email"),
        mail_stats_service: MailStatsService = Depends(get_stats_service)
):
    log.info(f"Getting unread count from gmail")
    return {
        "message": f"Unread message count for {user_email}",
        "unread": mail_stats_service.get_unread_count(user_email)
    }

@stats_router.get("/read")
def get_read(
        user_email: str = Header(..., alias="user-email"),
        mail_stats_service: MailStatsService = Depends(get_stats_service)
):
    log.info(f"Getting read count from gmail")
    return {
        "message": f"Read message count for {user_email}",
        "read": mail_stats_service.get_read_count(user_email)
    }