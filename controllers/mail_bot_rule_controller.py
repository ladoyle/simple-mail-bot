from fastapi import APIRouter, HTTPException
from models.mail_bot_schemas import LabelRequest, RuleRequest
from service.mail_rule_service import MailService

rule_router = APIRouter(prefix="/rules")

@rule_router.post("/create_rule")
def create_rule(req: RuleRequest):
    rule_id = mail_service.add_rule(req.rule_name, req.condition, req.action)
    return {"message": f'Rule {req.rule_name} created successfully', "rule_id": rule_id.id}