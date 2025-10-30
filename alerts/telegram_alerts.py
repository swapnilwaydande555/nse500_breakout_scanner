# alerts/telegram_alerts.py
import os
import requests
import urllib.parse

TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELE_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")

def send_test_alert(msg):
    if not TELE_TOKEN or not TELE_CHAT:
        return {'ok': False, 'info': 'Telegram token/chat not set. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in environment.'}
    text = urllib.parse.quote_plus(msg)
    url = f'https://api.telegram.org/bot{TELE_TOKEN}/sendMessage?chat_id={TELE_CHAT}&text={text}'
    try:
        r = requests.get(url, timeout=10)
        return {'ok': r.status_code == 200, 'code': r.status_code, 'resp': r.text}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
