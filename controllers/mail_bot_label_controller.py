from fastapi import APIRouter, HTTPException

from backend.database import EmailLabel
from models.mail_bot_schemas import LabelRequest
from service.mail_label_service import mail_label_service

label_router = APIRouter(prefix="/labels")

@label_router.get("/", response_model=list[EmailLabel])
def list_labels():
    return mail_label_service.list_labels()

@label_router.post("/", response_model=dict)
def create_label(req: LabelRequest):
    label_id = mail_label_service.create_label(req)
    return {"message": "Label created", "label_id": label_id}

@label_router.delete("/{label_id}", response_model=dict)
def delete_label(label_id: int):
    deleted = mail_label_service.delete_label(label_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Label not found")
    return {"message": "Label deleted", "label_id": label_id}
