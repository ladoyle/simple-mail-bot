import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from models.mail_bot_schemas import OauthRequest
from service.mail_oauth_service import get_oauth_service, MailOAuthService

oauth_router = APIRouter(prefix="/oauth")

@oauth_router.get("/login")
def login(oauth_service: MailOAuthService = Depends(get_oauth_service)):
    auth_url = oauth_service.get_authorization_url()
    return RedirectResponse(auth_url)

@oauth_router.get("/callback")
def callback(req: OauthRequest, oauth_service: MailOAuthService = Depends(get_oauth_service)):
    code = req.code
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")
    user_email, access_token = oauth_service.handle_callback(code)
    response = RedirectResponse(url="/")
    response.body = json.dumps({"email": user_email, "token": access_token}).encode("utf-8")
    return response

@oauth_router.post("/logout")
def logout(request: OauthRequest, oauth_service: MailOAuthService = Depends(get_oauth_service)):
    user_email = request.email
    if user_email:
        removed = oauth_service.remove_user(user_email)
        if not removed:
            raise HTTPException(status_code=404, detail="User not found")
        response = RedirectResponse(url="/")
        response.body = json.dumps({"message": f'Successfully logged out user {user_email}', "status": 'success'}).encode("utf-8")
        return response
    raise HTTPException(status_code=401, detail="No email provided")