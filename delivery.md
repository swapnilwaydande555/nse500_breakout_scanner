# Delivery & Minimal Steps (Non-technical) — Get your live link in ~10-20 minutes

This file contains explicit, minimal steps you must perform. I prepared everything else.

## 1) Download the ZIP and upload to GitHub
- Download `nse500_breakout_scanner.zip` from the link provided by the assistant.
- Create a GitHub account (if you don't have one).
- Create a new repository named `nse500_breakout_scanner`.
- Using GitHub web UI, upload the contents of the unzipped project and commit to `main` branch.

## 2) Create Render account and connect GitHub
- Sign up at https://render.com using "Sign in with GitHub".
- Click **New** → **Web Service** → select the `nse500_breakout_scanner` repo/branch `main`.
- Render will detect Dockerfile. Create the service (`nse500-breakout`). Wait for build.

## 3) Set environment variables on Render
- In your Render service dashboard, go to "Environment" (or "Settings" → "Environment") and add:
  - `TELEGRAM_BOT_TOKEN` (optional) — e.g. `123456:ABC-DEF...`
  - `TELEGRAM_CHAT_ID` (optional) — your chat id or group id
  - No Zerodha keys are required.
- Save and redeploy if necessary.

## 4) Create Render Background Worker (for 24/7 polling)
- Click **New** → **Background Worker** → select same repo/branch.
- Worker start command: `python scheduler.py`
- This runs the scheduler that fetches data and updates signals every 5 minutes.

## 5) Visit the public URL Render provides
- Example: `https://nse500-breakout.onrender.com`
- You will see the Streamlit dashboard with "Last updated" time and current signals.

## 6) Test Telegram alerts (optional)
- If you added `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, open the site and click "Send test Telegram Alert" in the admin area.

## 7) Support & Next steps
- If you want, share Render logs with a developer to troubleshoot.
- To connect private data later (e.g., Zerodha), implement secure OAuth and private-user sessions.

