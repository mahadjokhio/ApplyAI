from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.api.users import get_user_or_404
from app.database import get_db
from app.models.cv_profile import CVProfile
from app.schemas.cv import CVProfileCreate, CVProfileResponse

router = APIRouter(prefix="/users", tags=["CV"])


@router.get("/{user_id}/cv", response_model=CVProfileResponse)
def get_cv(user_id: int, db: Session = Depends(get_db)):
    get_user_or_404(user_id, db)
    profile = (
        db.query(CVProfile)
        .filter(CVProfile.user_id == user_id)
        .order_by(CVProfile.created_at.desc(), CVProfile.id.desc())
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="CV not found")
    return profile


@router.post("/{user_id}/cv", response_model=CVProfileResponse)
def save_cv(user_id: int, cv: CVProfileCreate, db: Session = Depends(get_db)):
    get_user_or_404(user_id, db)
    profile = (
        db.query(CVProfile)
        .filter(CVProfile.user_id == user_id)
        .order_by(CVProfile.created_at.desc(), CVProfile.id.desc())
        .first()
    )

    if profile:
        profile.raw_text = cv.raw_text
        profile.file_path = None
    else:
        profile = CVProfile(user_id=user_id, raw_text=cv.raw_text)
        db.add(profile)

    db.commit()
    db.refresh(profile)
    return profile


@router.post("/{user_id}/cv/upload", response_model=CVProfileResponse)
async def upload_cv(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    get_user_or_404(user_id, db)
    filename = (file.filename or "").lower()
    if not filename.endswith((".txt", ".pdf")):
        raise HTTPException(status_code=400, detail="Only .txt and .pdf files are supported")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="CV file must be smaller than 5 MB")

    try:
        if filename.endswith(".pdf"):
            reader = PdfReader(BytesIO(content))
            raw_text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        else:
            raw_text = content.decode("utf-8").strip()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not extract text from this file") from exc

    if not raw_text:
        raise HTTPException(status_code=400, detail="The uploaded file contains no readable text")

    profile = (
        db.query(CVProfile)
        .filter(CVProfile.user_id == user_id)
        .order_by(CVProfile.created_at.desc(), CVProfile.id.desc())
        .first()
    )
    if profile:
        profile.raw_text = raw_text
        profile.file_path = file.filename
    else:
        profile = CVProfile(user_id=user_id, raw_text=raw_text, file_path=file.filename)
        db.add(profile)

    db.commit()
    db.refresh(profile)
    return profile