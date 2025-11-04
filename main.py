#!/usr/bin/env python3
"""
Главный файл для запуска Telegram бота
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
from bot import TelegramBot

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        logger.error("Создайте файл .env и добавьте TELEGRAM_BOT_TOKEN=your_token")
        return
    
    bot = TelegramBot(token=token)
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Остановка бота...")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
