from typing import List

from fastapi import APIRouter, HTTPException, Depends
from models.mail_bot_schemas import RuleRequest, RuleResponse
from service.mail_rule_service import get_rule_service, MailRuleService

rule_router = APIRouter(prefix="/rules")


@rule_router.get("/", response_model=List[RuleResponse])
def list_rules(mail_rule_service: MailRuleService = Depends(get_rule_service)):
    return mail_rule_service.list_rules()


@rule_router.post("/", response_model=dict)
def create_rule(req: RuleRequest, mail_rule_service: MailRuleService = Depends(get_rule_service)):
    rule_id = mail_rule_service.create_rule(req)
    return {"message": "Rule created", "rules": rule_id}


@rule_router.delete("/{rule_id}", response_model=dict)
def delete_rule(rule_id: int, mail_rule_service: MailRuleService = Depends(get_rule_service)):
    deleted = mail_rule_service.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Rule deleted", "rules": rule_id}