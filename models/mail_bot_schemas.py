from pydantic import BaseModel


class LabelRequest(BaseModel):
    email_id: str
    label: str


class LabelResponse(BaseModel):
    id: int
    gmail_id: str
    name: str

    class Config:
        from_attributes = True


class RuleRequest(BaseModel):
    rule_name: str
    criteria: str
    addLabelIds: list[str]
    removeLabelIds: list[str]
    forward: str


class RuleResponse(BaseModel):
    id: int
    gmail_id: str
    name: str
    criteria: str
    addLabelIds: list[str]
    removeLabelIds: list[str]
    forward: str

    class Config:
        from_attributes = True


class OauthRequest(BaseModel):
    email: str
    code: str