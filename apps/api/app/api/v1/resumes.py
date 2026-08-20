import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.security import get_current_user
from app.core.storage import StorageError, create_signed_url, upload_object
from app.models.resume import FileType, Resume, ResumeStatus, ResumeVersion
from app.models.user import User
from app.schemas.envelope import Envelope, meta_from_request
from app.schemas.resume import ResumeDetailRead, ResumeRead, ResumeStatusRead, ResumeVersionRead
from app.workers.resume_tasks import process_resume_task

router = APIRouter(prefix="/resumes", tags=["resumes"])

UserDep = Annotated[User, Depends(get_current_user)]
DbDep = Annotated[AsyncSession, Depends(get_db)]

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
_CONTENT_TYPE_TO_FILE_TYPE = {
    "application/pdf": FileType.PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileType.DOCX,
}
_EXTENSION_TO_FILE_TYPE = {".pdf": FileType.PDF, ".docx": FileType.DOCX}


def _resolve_file_type(file: UploadFile) -> FileType:
    if file.content_type in _CONTENT_TYPE_TO_FILE_TYPE:
        return _CONTENT_TYPE_TO_FILE_TYPE[file.content_type]
    name = (file.filename or "").lower()
    for ext, file_type in _EXTENSION_TO_FILE_TYPE.items():
        if name.endswith(ext):
            return file_type
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Only PDF and DOCX files are supported.",
    )


async def _get_owned_resume(resume_id: uuid.UUID, user: User, db: AsyncSession) -> Resume:
    result = await db.execute(
        select(Resume).where(
            Resume.id == resume_id, Resume.user_id == user.id, Resume.deleted_at.is_(None)
        )
    )
    resume = result.scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")
    return resume


async def _to_detail_read(resume: Resume) -> ResumeDetailRead:
    download_url = None
    try:
        download_url = await create_signed_url(resume.file_url)
    except StorageError:
        # The analysis itself doesn't depend on being able to re-sign a download link — show
        # everything else and simply omit the link rather than failing the whole response.
        pass
    return ResumeDetailRead(
        id=resume.id,
        file_name=resume.file_name,
        file_type=resume.file_type,
        status=resume.status,
        overall_score=float(resume.overall_score) if resume.overall_score is not None else None,
        failure_reason=resume.failure_reason,
        created_at=resume.created_at,
        structured_data=resume.structured_data,
        score_breakdown=resume.score_breakdown,
        file_download_url=download_url,
    )


@router.get("", response_model=Envelope[list[ResumeRead]])
async def list_resumes(request: Request, user: UserDep, db: DbDep) -> Envelope[list[ResumeRead]]:
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == user.id, Resume.deleted_at.is_(None))
        .order_by(Resume.created_at.desc())
    )
    rows = result.scalars().all()
    return Envelope(
        data=[ResumeRead.model_validate(r) for r in rows], meta=meta_from_request(request)
    )


@router.post("/upload", response_model=Envelope[ResumeRead], status_code=status.HTTP_202_ACCEPTED)
async def upload_resume(
    request: Request, user: UserDep, db: DbDep, file: UploadFile
) -> Envelope[ResumeRead]:
    file_type = _resolve_file_type(file)
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="File exceeds the 10MB upload limit.",
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="The uploaded file is empty."
        )

    resume = Resume(
        user_id=user.id,
        file_url="",
        file_name=file.filename or f"resume.{file_type.value.lower()}",
        file_type=file_type,
        status=ResumeStatus.UPLOADED,
    )
    db.add(resume)
    await db.flush()

    extension = ".pdf" if file_type == FileType.PDF else ".docx"
    storage_path = f"{settings.storage_bucket}/{user.id}/{resume.id}{extension}"

    try:
        await upload_object(storage_path, content, file.content_type or "application/octet-stream")
    except StorageError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Could not store the file: {exc}"
        ) from exc

    resume.file_url = storage_path
    await db.commit()
    await db.refresh(resume)

    process_resume_task.delay(str(resume.id))

    return Envelope(data=ResumeRead.model_validate(resume), meta=meta_from_request(request))


@router.get("/{resume_id}", response_model=Envelope[ResumeDetailRead])
async def get_resume(
    request: Request, resume_id: uuid.UUID, user: UserDep, db: DbDep
) -> Envelope[ResumeDetailRead]:
    resume = await _get_owned_resume(resume_id, user, db)
    return Envelope(data=await _to_detail_read(resume), meta=meta_from_request(request))


@router.get("/{resume_id}/status", response_model=Envelope[ResumeStatusRead])
async def get_resume_status(
    request: Request, resume_id: uuid.UUID, user: UserDep, db: DbDep
) -> Envelope[ResumeStatusRead]:
    resume = await _get_owned_resume(resume_id, user, db)
    return Envelope(data=ResumeStatusRead.model_validate(resume), meta=meta_from_request(request))


@router.get("/{resume_id}/versions", response_model=Envelope[list[ResumeVersionRead]])
async def list_resume_versions(
    request: Request, resume_id: uuid.UUID, user: UserDep, db: DbDep
) -> Envelope[list[ResumeVersionRead]]:
    resume = await _get_owned_resume(resume_id, user, db)
    result = await db.execute(
        select(ResumeVersion)
        .where(ResumeVersion.resume_id == resume.id)
        .order_by(ResumeVersion.version_number.desc())
    )
    rows = result.scalars().all()
    return Envelope(
        data=[ResumeVersionRead.model_validate(r) for r in rows], meta=meta_from_request(request)
    )


@router.post(
    "/{resume_id}/analyze",
    response_model=Envelope[ResumeRead],
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyze_resume(
    request: Request,
    resume_id: uuid.UUID,
    user: UserDep,
    db: DbDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Envelope[ResumeRead]:
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Idempotency-Key header is required."
        )
    resume = await _get_owned_resume(resume_id, user, db)
    if resume.status == ResumeStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This resume is already being analyzed."
        )

    resume.status = ResumeStatus.PROCESSING
    await db.commit()
    await db.refresh(resume)

    process_resume_task.delay(str(resume.id))

    return Envelope(data=ResumeRead.model_validate(resume), meta=meta_from_request(request))


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(resume_id: uuid.UUID, user: UserDep, db: DbDep) -> None:
    resume = await _get_owned_resume(resume_id, user, db)
    resume.soft_delete()
    await db.commit()
