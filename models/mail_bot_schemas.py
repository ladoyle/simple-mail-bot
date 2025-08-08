from pydantic import BaseModel


class LabelRequest(BaseModel):
    email_id: str
    label: str


class LabelResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class RuleRequest(BaseModel):
    rule_name: str
    condition: str
    action: str
