import asyncio
import os
from telegram import Bot

async def check_webhook():
    token = "8303694170:AAFUUdd_4vds67yYeXZQGGI7tYKuA7H48lI"
    bot = Bot(token)
    info = await bot.get_webhook_info()
    print(f"Webhook URL: {info.url}")
    print(f"Has Custom Certificate: {info.has_custom_certificate}")
    print(f"Pending Update Count: {info.pending_update_count}")
    if info.last_error_date:
        print(f"Last Error Date: {info.last_error_date}")
        print(f"Last Error Message: {info.last_error_message}")

if __name__ == "__main__":
    asyncio.run(check_webhook())
