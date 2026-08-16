from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from apps.api.api.deps import queue_from_app
from apps.api.auth.dependencies import get_current_user
from apps.api.database.session import get_db
from apps.api.models.user import User
from apps.api.schemas.job import JobCancelResponse, JobResponse
from apps.api.services import job_service

router = APIRouter()


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    return JobResponse.model_validate(job_service.get_job(db, job_id, current_user.id))


@router.post("/{job_id}/cancel", response_model=JobCancelResponse)
def cancel_job(
    job_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobCancelResponse:
    job = job_service.cancel_job(db, queue_from_app(request), job_id, current_user.id)
    return JobCancelResponse(id=job.id, status=job.status, message="job cancelled")


@router.post("/{job_id}/retry", response_model=JobResponse)
def retry_job(
    job_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    return JobResponse.model_validate(
        job_service.retry_job(db, queue_from_app(request), job_id, current_user.id)
    )
