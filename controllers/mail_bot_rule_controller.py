import logging as log
from typing import List

from fastapi import APIRouter, HTTPException, Depends, Header
from models.mail_bot_schemas import RuleRequest, RuleResponse
from service.mail_rule_service import get_rule_service, MailRuleService

rule_router = APIRouter(prefix="/rules")


@rule_router.get("/list", response_model=List[RuleResponse])
def list_rules(
        access_token: str = Header(..., alias="Authorization"),
        user_email: str = Header(..., alias="user-email"),
        mail_rule_service: MailRuleService = Depends(get_rule_service)
):
    log.info("Listing rules")
    return mail_rule_service.list_rules(user_email, access_token)


@rule_router.post("/create", response_model=dict)
def create_rule(
        req: RuleRequest,
        access_token: str = Header(..., alias="Authorization"),
        user_email: str = Header(..., alias="user-email"),
        mail_rule_service: MailRuleService = Depends(get_rule_service)
):
    log.info(f"Creating rule with name={req.rule_name}")
    rule = mail_rule_service.create_rule(user_email, access_token, req)
    return {"message": f"Rule created, {rule.name}", "ruleId": rule.id}


@rule_router.delete("/delete", response_model=dict)
def delete_rule(
        ruleId: int,
        access_token: str = Header(..., alias="Authorization"),
        user_email: str = Header(..., alias="user-email"),
        mail_rule_service: MailRuleService = Depends(get_rule_service)
):
    log.info(f"Deleting rule with id={ruleId}")
    deleted = mail_rule_service.delete_rule(user_email, access_token, ruleId)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Rule deleted", "ruleId": ruleId}