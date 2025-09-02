from fastapi import APIRouter, Depends, HTTPException, Header

from service.mail_oauth_service import get_oauth_service, MailOAuthService

oauth_router = APIRouter(prefix="/oauth")

@oauth_router.get("/login")
def login(oauth_service: MailOAuthService = Depends(get_oauth_service)):
    return {"authUrl": oauth_service.get_authorization_url(), "status": "success"}

@oauth_router.get("/callback")
def callback(code: str, oauth_service: MailOAuthService = Depends(get_oauth_service)):
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")
    user_email, access_token = oauth_service.handle_callback(code)
    return {
        "message": f'User {user_email} successfully logged in',
        "email": user_email,
        "token": access_token,
        "status": 'success'
    }

@oauth_router.post("/logout")
def logout(
        userEmail: str,
        access_token: str = Header(..., alias="Authorization"),
        oauth_service: MailOAuthService = Depends(get_oauth_service)
):
    if not userEmail:
        raise HTTPException(status_code=400, detail="No email provided")

    removed = oauth_service.remove_user(userEmail, access_token)
    if not removed:
        raise HTTPException(status_code=404, detail=f"User not found, {userEmail}")
    return {"message": f'Successfully logged out user {userEmail}', "status": 'success'}