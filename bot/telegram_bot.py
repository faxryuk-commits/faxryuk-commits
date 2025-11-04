import os
import logging
import asyncio
from typing import List, Dict, Any
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from parsers.marketplace import WildberriesParser, OzonParser
from parsers.maps import GoogleMapsParser, YandexMapsParser, TwoGISParser
from models.data_models import Product, Organization
from storage import JSONStorage
from parsers.marketplace import UzumParser

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram бот для управления парсером"""
    
    def __init__(self, token: str):
        """
        Args:
            token: Токен Telegram бота от @BotFather
        """
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.storage = JSONStorage()
        self._register_handlers()
    
    def _register_handlers(self):
        """Регистрирует обработчики команд"""
        # Основные команды
        self.dp.message(Command("start"))(self.cmd_start)
        self.dp.message(Command("help"))(self.cmd_help)
        
        # Команды маркетплейсов
        self.dp.message(Command("wb"))(self.cmd_wildberries)
        self.dp.message(Command("ozon"))(self.cmd_ozon)
        self.dp.message(Command("uzum"))(self.cmd_uzum)
        
        # Команды карт
        self