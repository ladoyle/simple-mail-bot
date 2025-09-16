from pydantic import BaseModel, Field


class LabelRequest(BaseModel):
    label: str
    text_color: str = Field(..., alias="textColor")
    background_color: str = Field(..., alias="backgroundColor")


class LabelResponse(BaseModel):
    id: int
    gmail_id: str
    name: str
    text_color: str 
    background_color: str

    class Config:
        from_attributes = True


class RuleRequest(BaseModel):
    rule_name: str = Field(..., alias="ruleName")
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