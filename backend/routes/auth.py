from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from models.schemas import AuthResponse, CurrentUserResponse, LoginRequest
from services.auth_service import authenticate_user, create_access_token, decode_token, get_user_by_username

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    user = authenticate_user(payload.username.strip().lower(), payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(subject=user["username"])
    return AuthResponse(access_token=token, username=user["username"])


def get_current_username(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    username = decode_token(credentials.credentials)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    return username


@router.get("/me", response_model=CurrentUserResponse)
def me(username: str = Depends(get_current_username)) -> CurrentUserResponse:
    return CurrentUserResponse(username=username)
