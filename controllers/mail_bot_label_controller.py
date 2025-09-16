import logging as log
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Header

from models.mail_bot_schemas import LabelRequest, LabelResponse
from service.mail_label_service import get_label_service, MailLabelService

label_router = APIRouter(prefix="/v1/labels")


@label_router.get("/list", response_model=List[LabelResponse])
def list_labels(
        access_token: str = Header(..., alias="Authorization"),
        user_email: str = Header(..., alias="user-email"),
        mail_label_service: MailLabelService = Depends(get_label_service)
):
    log.info("Listing labels")
    return mail_label_service.list_labels(user_email, access_token)


@label_router.post("/create", response_model=dict)
def create_label(
        req: LabelRequest,
        access_token: str = Header(..., alias="Authorization"),
        user_email: str = Header(..., alias="user-email"),
        mail_label_service: MailLabelService = Depends(get_label_service)
):
    log.info(f"Creating label with name={req.label}")
    label = mail_label_service.create_label(user_email, access_token, req)
    return {"message": f"Label created, {label.name}", "labelId": label.id}


@label_router.delete("/delete", response_model=dict)
def delete_label(
        labelId: int,
        access_token: str = Header(..., alias="Authorization"),
        user_email: str = Header(..., alias="user-email"),
        mail_label_service: MailLabelService = Depends(get_label_service)
):
    log.info(f"Deleting label with id={labelId}")
    deleted = mail_label_service.delete_label(user_email, access_token, labelId)
    if not deleted:
        raise HTTPException(status_code=404, detail="Label not found")
    return {"message": "Label deleted", "labelId": labelId}
