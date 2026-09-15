import base64
import html
import json
import os
import re
from dataclasses import dataclass
from email.utils import parseaddr
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
BASE_DIR = Path(__file__).resolve().parents[2]
CREDENTIALS_FILE = Path(os.getenv("GMAIL_CREDENTIALS_FILE", BASE_DIR / "credentials.json"))
TOKEN_FILE = Path(os.getenv("GMAIL_TOKEN_FILE", BASE_DIR / "token.json"))
OAUTH_STATE_FILE = Path(os.getenv("GMAIL_OAUTH_STATE_FILE", BASE_DIR / ".gmail_oauth_state.json"))
REDIRECT_URI = os.getenv("GMAIL_REDIRECT_URI", "http://localhost:8000/gmail/oauth2callback")

# Local-development only: permit the HTTP localhost OAuth callback.
# Production must use an HTTPS redirect URI and must not enable this flag.
if REDIRECT_URI.startswith("http://localhost:"):
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

SEARCH_QUERY = (
    "in:anywhere newer_than:30d -category:promotions "
    "{job OR jobs OR internship OR career OR interview OR recruiter OR "
    "position OR hiring OR offer OR application OR opportunity}"
)

POSITIVE_TERMS = (
    "job", "jobs", "internship", "career opportunity", "interview", "recruiter",
    "position", "hiring", "job opportunity", "application received", "offer letter",
)
NEGATIVE_TERMS = (
    "spotify", "chatgpt", "newsletter", "sale", "discount", "semester registration",
    "club", "societies", "election", "scholarship", "exchange program",
)


@dataclass
class GmailMessage:
    message_id: str
    sender: str
    subject: str
    snippet: str
    status: str


def is_job_related(subject: str, snippet: str) -> bool:
    text = f"{subject} {snippet}".lower()
    return any(term in text for term in POSITIVE_TERMS) and not any(
        term in text for term in NEGATIVE_TERMS
    )


def get_authorization_url() -> str:
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"Missing {CREDENTIALS_FILE.name}. Download an OAuth client JSON from Google Cloud Console."
        )
    flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_FILE), scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    authorization_url, _ = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    OAUTH_STATE_FILE.write_text(
        json.dumps({"code_verifier": flow.code_verifier}), encoding="utf-8"
    )
    return authorization_url


def complete_authorization(authorization_response: str) -> None:
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"Missing {CREDENTIALS_FILE.name}. Download an OAuth client JSON from Google Cloud Console."
        )
    if REDIRECT_URI.startswith("http://localhost:"):
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    if not OAUTH_STATE_FILE.exists():
        raise RuntimeError("OAuth session expired. Open /gmail/auth and try again.")
    oauth_state = json.loads(OAUTH_STATE_FILE.read_text(encoding="utf-8"))
    flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_FILE),
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        code_verifier=oauth_state["code_verifier"],
    )
    query = parse_qs(urlparse(authorization_response).query)
    code = query.get("code", [None])[0]
    if not code:
        raise ValueError("Google did not return an authorization code")
    token_response = requests.post(
        flow.client_config["token_uri"],
        data={
            "code": code,
            "client_id": flow.client_config["client_id"],
            "client_secret": flow.client_config["client_secret"],
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
            "code_verifier": oauth_state["code_verifier"],
        },
        timeout=30,
    )
    token_response.raise_for_status()
    token_data = token_response.json()
    token_data.update(
        {
            "token_uri": flow.client_config["token_uri"],
            "client_id": flow.client_config["client_id"],
            "client_secret": flow.client_config["client_secret"],
            "scopes": SCOPES,
        }
    )
    TOKEN_FILE.write_text(json.dumps(token_data), encoding="utf-8")
    OAUTH_STATE_FILE.unlink(missing_ok=True)


def _get_credentials() -> Credentials:
    credentials = None
    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(GoogleAuthRequest())
        TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")

    if not credentials or not credentials.valid:
        raise RuntimeError("Gmail is not connected. Open GET /gmail/auth first.")
    return credentials


def _header(headers: list[dict], name: str) -> str:
    return next((item["value"] for item in headers if item["name"].lower() == name.lower()), "")


def _decode_body(payload: dict) -> str:
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        result = _decode_body(part)
        if result:
            return result
    return ""


def _plain_text(value: str) -> str:
    value = re.sub(r"<style.*?</style>|<script.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _status_for(subject: str, body: str) -> str:
    text = f"{subject} {body}".lower()
    if any(word in text for word in ("rejection", "rejected", "not selected", "unfortunately")):
        return "Rejected"
    if any(word in text for word in ("interview", "phone screen", "onsite")):
        return "Review"
    if any(word in text for word in ("application received", "application confirmation", "thank you for applying")):
        return "Applied"
    return "Discovered"


def search_messages(max_results: int | None = None) -> list[GmailMessage]:
    service = build("gmail", "v1", credentials=_get_credentials(), cache_discovery=False)
    message_items = []
    page_token = None
    while max_results is None or len(message_items) < max_results:
        page_size = 100 if max_results is None else min(100, max_results - len(message_items))
        result = service.users().messages().list(
            userId="me",
            q=SEARCH_QUERY,
            maxResults=page_size,
            pageToken=page_token,
        ).execute()
        message_items.extend(result.get("messages", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    messages: list[GmailMessage] = []

    for item in message_items if max_results is None else message_items[:max_results]:
        message = service.users().messages().get(
            userId="me", id=item["id"], format="full"
        ).execute()
        payload = message.get("payload", {})
        headers = payload.get("headers", [])
        sender = parseaddr(_header(headers, "From"))[1] or _header(headers, "From")
        subject = _header(headers, "Subject") or "Gmail job-related email"
        body = _plain_text(_decode_body(payload))
        snippet = message.get("snippet", "") or body[:500]
        if not is_job_related(subject, snippet):
            continue
        messages.append(
            GmailMessage(
                message_id=message["id"],
                sender=sender,
                subject=subject,
                snippet=snippet[:1000],
                status=_status_for(subject, body),
            )
        )
    return messages


def gmail_marker(message_id: str) -> str:
    return f"[gmail_message_id:{message_id}]"
