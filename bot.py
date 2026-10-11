
import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=20
    )
    response.raise_for_status()
    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(result)

    print("Telegram message sent successfully!")

def main():
    now = datetime.now(ZoneInfo("Asia/Singapore"))

    message = (
        "🎮 MPL DRAFT ALERT BOT ONLINE!\n\n"
        "✅ GitHub Actions connection successful\n"
        f"🕒 Singapore time: {now:%d %b %Y, %I:%M %p}\n\n"
        "Next: Connect MPL match schedules."
    )

    send_telegram(message)

if __name__ == "__main__":
    main()
