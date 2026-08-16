from fastapi import APIRouter, Depends

from apps.api.auth.dependencies import get_current_user
from apps.api.models.user import User
from apps.api.schemas.user import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
