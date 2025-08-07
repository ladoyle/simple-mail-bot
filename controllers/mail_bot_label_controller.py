from typing import List

from fastapi import APIRouter, Depends, HTTPException

from models.mail_bot_schemas import LabelRequest, LabelResponse
from service.mail_label_service import get_label_service, MailLabelService

label_router = APIRouter(prefix="/labels")


@label_router.get("/", response_model=List[LabelResponse])
def list_labels(mail_label_service: MailLabelService = Depends(get_label_service)):
    return mail_label_service.list_labels()


@label_router.post("/", response_model=dict)
def create_label(req: LabelRequest, mail_label_service: MailLabelService = Depends(get_label_service)):
    label_id = mail_label_service.create_label(req)
    return {"message": "Label created", "labels": label_id}


@label_router.delete("/{label_id}", response_model=dict)
def delete_label(label_id: int, mail_label_service: MailLabelService = Depends(get_label_service)):
    deleted = mail_label_service.delete_label(label_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Label not found")
    return {"message": "Label deleted", "labels": label_id}
