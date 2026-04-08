import asyncio
import os
import sys
from telegram import Bot

async def set_webhook(url: str):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
        return

    print(f"Setting webhook to: {url}")
    bot = Bot(token)
    await bot.set_webhook(url=url)
    print("Webhook set successfully!")
    
    info = await bot.get_webhook_info()
    print(f"Verified Webhook Info: {info}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m coremind.scripts.set_webhook <WEBHOOK_URL>")
        sys.exit(1)
        
    webhook_url = sys.argv[1]
    asyncio.run(set_webhook(webhook_url))
