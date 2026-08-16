from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.auth.dependencies import get_current_user
from apps.api.database.session import get_db
from apps.api.models.user import User
from apps.api.schemas.script import ScriptPreviewRequest, ScriptPreviewResponse
from apps.api.services import script_service

router = APIRouter()


@router.post("/preview", response_model=ScriptPreviewResponse)
def preview_script(
    payload: ScriptPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScriptPreviewResponse:
    return script_service.preview_script(
        db,
        current_user.id,
        payload.workspace_id,
        payload.topic,
        payload.video_language,
        payload.paragraph_number,
    )
