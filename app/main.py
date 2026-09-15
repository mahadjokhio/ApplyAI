from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.models import user, cv_profile, job
from app.api import cv, gmail, jobs, users

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ApplyAI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(users.router)
app.include_router(cv.router)
app.include_router(gmail.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ApplyAI Backend"}