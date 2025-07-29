from pydantic import BaseModel

class LabelRequest(BaseModel):
    email_id: str
    label: str

class RuleRequest(BaseModel):
    rule_name: str
    condition: str
    action: str