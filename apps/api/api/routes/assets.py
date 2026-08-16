from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from apps.api.api.deps import get_storage
from apps.api.auth.dependencies import get_current_user
from apps.api.database.session import get_db
from apps.api.models.user import User
from apps.api.schemas.asset import AssetResponse
from apps.api.services import asset_service
from shared.storage.storage_provider import StorageProvider

router = APIRouter()


def storage_from_app(request: Request) -> StorageProvider:
    return getattr(request.app.state, "storage", None) or get_storage()


@router.get("", response_model=list[AssetResponse])
def list_assets(
    workspace_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AssetResponse]:
    return asset_service.list_assets(db, current_user.id, workspace_id)


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    request: Request,
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssetResponse:
    content = await file.read()
    return asset_service.create_asset(
        db,
        storage_from_app(request),
        current_user.id,
        workspace_id,
        file.filename or "upload.bin",
        content,
        file.content_type,
    )


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    asset_service.delete_asset(db, storage_from_app(request), asset_id, current_user.id)
