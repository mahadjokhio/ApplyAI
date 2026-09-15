import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise SystemExit("GEMINI_API_KEY is missing in .env")

MODEL_NAME = "gemini-flash-lite-latest"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"

payload = {
    "contents": [
        {"parts": [{"text": "Say hello in one word."}]}
    ]
}

print("Using API key:", api_key[:8] + "..." + api_key[-4:])
print("Request URL:", url)

response = requests.post(url, params={"key": api_key}, json=payload, timeout=30)

print("Status:", response.status_code)
print(response.text)

try:
    data = response.json()
    print("JSON keys:", list(data.keys())[:10])
except Exception:
    pass
