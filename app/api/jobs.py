from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.cv_profile import CVProfile
from app.models.job import JobApplication
from app.schemas.job import JobCreate, JobResponse, JobStatusUpdate
from app.services.matcher import match_job_to_cv

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/", response_model=JobResponse)
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    new_job = JobApplication(
        title=job.title,
        company=job.company,
        description=job.description,
        user_id=1  # placeholder until auth is added
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job


@router.get("/", response_model=list[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(JobApplication).all()


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(JobApplication).filter(JobApplication.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/{job_id}/status", response_model=JobResponse)
def update_status(job_id: int, update: JobStatusUpdate, db: Session = Depends(get_db)):
    job = db.query(JobApplication).filter(JobApplication.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = update.status
    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/match")
def run_match(job_id: int, db: Session = Depends(get_db)):
    job = db.query(JobApplication).filter(JobApplication.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    cv_profile = (
        db.query(CVProfile)
        .filter(CVProfile.user_id == job.user_id)
        .order_by(CVProfile.created_at.desc(), CVProfile.id.desc())
        .first()
    )
    if not cv_profile:
        raise HTTPException(status_code=400, detail="Save a CV before matching jobs")

    result = match_job_to_cv(cv_profile.raw_text, job.description or "")

    job.match_score = result["match_score"]
    db.commit()
    db.refresh(job)

    return {"match_score": result["match_score"], "reason": result["reason"]}