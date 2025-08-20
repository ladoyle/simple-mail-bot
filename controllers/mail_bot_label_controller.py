import logging as log
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Header

from models.mail_bot_schemas import LabelRequest, LabelResponse
from service.mail_label_service import get_label_service, MailLabelService

label_router = APIRouter(prefix="/labels")


@label_router.get("/", response_model=List[LabelResponse])
def list_labels(
        user_email: str = Header(..., alias="user-email"),
        mail_label_service: MailLabelService = Depends(get_label_service)
):
    log.info("Listing labels")
    return mail_label_service.list_labels(user_email)


@label_router.post("/", response_model=dict)
def create_label(
        req: LabelRequest,
        user_email: str = Header(..., alias="user-email"),
        mail_label_service: MailLabelService = Depends(get_label_service)
):
    log.info(f"Creating label with name={req.name}")
    label_id = mail_label_service.create_label(user_email, req)
    return {"message": "Label created", "label": label_id}


@label_router.delete("/{label_id}", response_model=dict)
def delete_label(
        label_id: int,
        user_email: str = Header(..., alias="user-email"),
        mail_label_service: MailLabelService = Depends(get_label_service)
):
    log.info(f"Deleting label with id={label_id}")
    deleted = mail_label_service.delete_label(user_email, label_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Label not found")
    return {"message": "Label deleted", "label": label_id}
