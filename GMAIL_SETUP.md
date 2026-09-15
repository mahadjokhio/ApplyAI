# Gmail integration setup

This integration is read-only and is intended for the current single-user setup (`user_id=1`). It reads matching Gmail messages and creates reviewable `JobApplication` rows. It does not send, modify, label, or delete email.

## 1. Create Google Cloud credentials

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project or select the project used for ApplyAI.
3. Open **APIs & Services -> Library**.
4. Search for **Gmail API** and click **Enable**.
5. Open **APIs & Services -> OAuth consent screen**.
6. Choose **External** for a personal Gmail account, or **Internal** if you use a Google Workspace organization.
7. Enter an app name such as `ApplyAI`, add your email as the support/developer contact, and save.
8. In **Scopes**, add the Gmail read-only scope if requested:
   `https://www.googleapis.com/auth/gmail.readonly`
9. In **Test users**, add the Gmail account you will connect when the app is External and still in testing.
10. Open **APIs & Services -> Credentials -> Create Credentials -> OAuth client ID**.
11. Choose **Web application**.
12. Add this exact authorized redirect URI:
    `http://localhost:8000/gmail/oauth2callback`
13. Create the client, download the JSON, rename it to `credentials.json`, and place it in `C:\Projects\ApplyAI`.

The redirect URI must match exactly. Use `localhost` in the browser and in the URI; do not substitute `127.0.0.1` unless you also register that exact URI in Google Cloud.

## 2. Install dependencies

From PowerShell:

```powershell
cd C:\Projects\ApplyAI
python -m pip install -r requirements.txt
```

The Gmail additions are `google-api-python-client`, `google-auth`, and `google-auth-oauthlib`.

## 3. Start the backend

```powershell
cd C:\Projects\ApplyAI
uvicorn app.main:app --reload
```

## 4. Connect Gmail once

Open this URL in your browser:

`http://localhost:8000/gmail/auth`

Copy the returned `authorization_url` into the browser, sign in, and approve read-only Gmail access. Google redirects to `/gmail/oauth2callback`, which saves `token.json` locally. Future requests refresh the token automatically.

If Google shows an unverified-app warning while the OAuth consent screen is in testing, choose **Advanced -> Go to ApplyAI** only if you recognize your own local app.

## 5. Sync messages

After authorization:

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/gmail/sync"
```

Optional result limit:

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/gmail/sync?max_results=50"
```

The response reports `created`, `skipped`, and imported job summaries. Repeating the sync is safe because each imported row contains a Gmail message ID marker and is skipped on later runs.

## Files and security

- `credentials.json`: OAuth client secret downloaded from Google; do not commit it.
- `token.json`: user access/refresh token; do not commit it.
- Both files are ignored by `.gitignore`.
- The Gmail scope is read-only. Revoke access from your Google Account security page if needed.
