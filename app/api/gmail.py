from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import JobApplication
from app.schemas.gmail import GmailSyncRequest
from app.services.gmail import (
    REDIRECT_URI,
    complete_authorization,
    get_authorization_url,
    gmail_marker,
    search_messages,
)

router = APIRouter(prefix="/gmail", tags=["Gmail"])


@router.get("/auth")
def gmail_auth():
    try:
        return RedirectResponse(url=get_authorization_url())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/oauth2callback")
def gmail_oauth_callback(request: Request):
    if request.query_params.get("error"):
        return {"connected": False, "error": request.query_params["error"]}
    try:
        complete_authorization(str(request.url))
        return {"connected": True, "message": "Gmail connected. You can close this page."}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Gmail authorization failed: {exc}") from exc


@router.post("/sync")
def sync_gmail(
    request: GmailSyncRequest | None = None,
    db: Session = Depends(get_db),
    max_results: int | None = None,
):
    if max_results is not None and not 1 <= max_results <= 5000:
        raise HTTPException(status_code=400, detail="max_results must be between 1 and 5000")
    try:
        messages = search_messages(max_results=max_results)
    except (RuntimeError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gmail sync failed: {exc}") from exc

    selected_ids = set(request.message_ids) if request and request.message_ids else None
    created = []
    skipped = 0
    for message in messages:
        if selected_ids is not None and message.message_id not in selected_ids:
            continue
        marker = gmail_marker(message.message_id)
        existing = db.query(JobApplication).filter(JobApplication.description.contains(marker)).first()
        if existing:
            skipped += 1
            continue

        job = JobApplication(
            user_id=1,
            title=message.subject[:255],
            company=message.sender[:255] or "Unknown sender",
            description=f"From: {message.sender}\n\n{message.snippet}\n\n{marker}",
            status=message.status,
        )
        db.add(job)
        created.append({"subject": message.subject, "sender": message.sender, "status": message.status})

    db.commit()
    return {"created": len(created), "skipped": skipped, "jobs": created}


@router.get("/preview")
def preview_gmail(max_results: int | None = None):
    if max_results is not None and not 1 <= max_results <= 5000:
        raise HTTPException(status_code=400, detail="max_results must be between 1 and 5000")
    try:
        messages = search_messages(max_results=max_results)
    except (RuntimeError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gmail preview failed: {exc}") from exc

    return [
        {
            "message_id": message.message_id,
            "sender": message.sender,
            "subject": message.subject,
            "snippet": message.snippet,
            "status": message.status,
        }
        for message in messages
    ]
