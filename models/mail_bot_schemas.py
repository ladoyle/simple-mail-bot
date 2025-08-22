from typing import Optional

from pydantic import BaseModel, Field


class LabelRequest(BaseModel):
    label: str
    text_color: str = Field(..., alias="textColor")
    background_color: str = Field(..., alias="backgroundColor")


class LabelResponse(BaseModel):
    id: int
    gmail_id: str = Field(..., alias="gmailId")
    name: str
    text_color: str = Field(..., alias="textColor")
    background_color: str = Field(..., alias="backgroundColor")

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
    gmail_id: str = Field(..., alias="gmailId")
    name: str
    criteria: str
    addLabelIds: list[str]
    removeLabelIds: list[str]
    forward: str

    class Config:
        from_attributes = True