from pydantic import BaseModel


class LabelRequest(BaseModel):
    label: str
    text_color: str
    background_color: str


class LabelResponse(BaseModel):
    id: int
    gmail_id: str
    name: str
    text_color: str
    background_color: str

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