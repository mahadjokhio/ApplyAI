import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-flash-lite-latest"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"


def match_job_to_cv(cv_text: str, job_description: str) -> dict:
    prompt = f"""You are a job-matching assistant. Compare the candidate's CV to the job description below.

Respond ONLY with valid JSON, no markdown, no code fences, in this exact format:
{{"match_score": <integer 0-100>, "reason": "<one sentence explanation>"}}

CV:
{cv_text}

Job Description:
{job_description}
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    try:
        resp = None
        for attempt in range(3):
            try:
                resp = requests.post(API_URL, json=payload, timeout=(10, 120))
                if resp.status_code not in (429, 500, 502, 503, 504):
                    break
            except requests.exceptions.Timeout:
                if attempt == 2:
                    raise
            if attempt < 2:
                time.sleep(2 ** attempt)

        resp.raise_for_status()
        data = resp.json()
        raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw.replace("json", "", 1).strip()

        parsed = json.loads(raw)
        return {
            "match_score": int(parsed.get("match_score", 0)),
            "reason": parsed.get("reason", "")
        }
    except Exception as e:
        return {"match_score": 0, "reason": f"Error: {str(e)}"}