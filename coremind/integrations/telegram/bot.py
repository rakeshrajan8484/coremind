from fastapi import APIRouter, Request
import requests
import os

router = APIRouter()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


@router.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" not in data:
        return {"ok": True}

    chat_id = data["message"]["chat"]["id"]
    user_text = data["message"].get("text", "")

    # Call your internal /chat endpoint
    response = requests.post(
        "http://localhost:8000/chat",
        json={
            "message": user_text,
            "user_id": str(chat_id),
        }
    )

    reply_text = response.json().get("reply", "Error")

    # Send response back to Telegram
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": reply_text,
        }
    )

    return {"ok": True}
