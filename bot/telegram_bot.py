import os
import logging
import asyncio
from typing import List, Dict, Any, Optional
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from parsers.marketplace import WildberriesParser, OzonParser, UzumParser
from parsers.maps import GoogleMapsParser, YandexMapsParser, TwoGISParser
from models.data_models import Product, Organization
from storage import JSONStorage

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
        self.dp.message(Command("yandex"))(self.cmd_yandex_maps)
        self.dp.message(Command("google"))(self.cmd_google_maps)
        self.dp.message(Command("2gis"))(self.cmd_2gis)
        
        # Управление данными
        self.dp.message(Command("stats"))(self.cmd_stats)
        self.dp.message(Command("clear"))(self.cmd_clear)
        
        # Обработка инлайн-кнопок
        self.dp.callback_query()(self.handle_callback)
    
    def _validate_and_normalize_product(self, product: Dict[str, Any]) -> Optional[Product]:
        """
        Валидирует и нормализует данные товара перед созданием модели Product
        
        Returns:
            Product объект или None, если данные невалидны
        """
        # Проверяем обязательные поля
        if not product.get('name') or not product.get('url') or not product.get('source'):
            logger.warning(f"Товар пропущен из-за отсутствия обязательных полей: {product}")
            return None
        
        try:
            # Нормализуем данные
            normalized = {
                'id': product.get('id'),
                'name': str(product.get('name', '')).strip(),
                'brand': product.get('brand'),
                'price': float(product.get('price', 0)),
                'rating': float(product.get('rating', 0)),
                'reviews_count': int(product.get('reviews_count', 0)),
                'url': str(product.get('url', '')).strip(),
                'image_url': product.get('image_url'),
                'description': product.get('description'),
                'characteristics': product.get('characteristics', {}),
                'source': str(product.get('source', '')).strip(),
            }
            
            return Product(**normalized)
        except Exception as e:
            logger.warning(f"Ошибка создания модели Product: {e}, данные: {product}")
            return None
    
    async def cmd_start(self, message: Message):
        """Обработчик команды /start"""
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="📦 Маркетплейсы", callback_data="menu_marketplace"))
        keyboard.add(InlineKeyboardButton(text="🗺️ Карты", callback_data="menu_maps"))
        keyboard.add(InlineKeyboardButton(text="📊 Статистика", callback_data="stats"))
        
        await message.answer(
            "🤖 Добро пожаловать в бот-парсер!\n\n"
            "Я могу парсить данные с:\n"
            "• Маркетплейсов (Wildberries, Ozon)\n"
            "• Карт (Google Maps, Яндекс.Карты, 2ГИС)\n\n"
            "Используйте /help для списка команд",
            reply_markup=keyboard.as_markup()
        )
    
    async def cmd_help(self, message: Message):
        """Обработчик команды /help"""
        help_text = """
📚 <b>Доступные команды:</b>

<b>Маркетплейсы:</b>
/wb <i>запрос</i> - Поиск на Wildberries
/ozon <i>запрос</i> - Поиск на Ozon
/uzum <i>запрос</i> - Поиск на Uzum Market

<b>Карты:</b>
/yandex <i>запрос [город]</i> - Поиск в Яндекс.Картах
/yandex <i>запрос [город] --email</i> - Поиск с сбором email адресов
/google <i>запрос [город]</i> - Поиск в Google Maps
/2gis <i>запрос [город]</i> - Поиск в 2ГИС

<b>Управление:</b>
/stats - Статистика сохраненных данных
/clear - Очистить данные

<b>Примеры:</b>
/wb ноутбук
/yandex ресторан Москва
/google кафе Санкт-Петербург
/2gis аптека Москва
"""
        await message.answer(help_text, parse_mode="HTML")
    
    async def cmd_wildberries(self, message: Message):
        """Парсинг Wildberries"""
        query = message.text.replace("/wb", "").strip()
        if not query:
            await message.answer("❌ Укажите запрос. Пример: /wb ноутбук")
            return
        
        await message.answer(f"⏳ Ищу товары на Wildberries по запросу: <b>{query}</b>", parse_mode="HTML")
        
        try:
            parser = WildberriesParser(delay=1.5)
            logger.info(f"Начинаю парсинг Wildberries для запроса: {query}")
            products = parser.parse_search(query, limit=10)
            logger.info(f"Парсер вернул {len(products)} товаров")
            
            if not products:
                await message.answer(
                    "❌ Товары не найдены\n\n"
                    "Возможные причины:\n"
                    "• Запрос не дал результатов\n"
                    "• Временные проблемы с API\n"
                    "• Попробуйте другой запрос"
                )
                logger.warning(f"Товары не найдены для запроса: {query}")
                return
            
            # Сохранение с валидацией
            try:
                product_models = []
                for p in products:
                    product = self._validate_and_normalize_product(p)
                    if product:
                        product_models.append(product)
                
                if product_models:
                    self.storage.save_products(product_models)
            except Exception as e:
                logger.error(f"Ошибка сохранения: {e}")
            
            # Отправка результатов
            text = f"✅ Найдено товаров: {len(products)}\n\n"
            for i, product in enumerate(products[:5], 1):
                name = product.get('name', 'N/A')[:50]
                price = product.get('price', 0)
                rating = product.get('rating', 0)
                
                text += f"{i}. <b>{name}</b>\n"
                if price > 0:
                    text += f"   💰 {price:.0f} ₽\n"
                if rating > 0:
                    text += f"   ⭐ {rating}\n"
                text += "\n"
            
            if len(products) > 5:
                text += f"... и еще {len(products) - 5} товаров\n"
            
            text += "\n✅ Данные сохранены!"
            await message.answer(text, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Ошибка парсинга Wildberries: {e}", exc_info=True)
            await message.answer(f"❌ Ошибка: {str(e)}")
    
    async def cmd_ozon(self, message: Message):
        """Парсинг Ozon"""
        query = message.text.replace("/ozon", "").strip()
        if not query:
            await message.answer("❌ Укажите запрос. Пример: /ozon телефон")
            return
        
        await message.answer(f"⏳ Ищу товары на Ozon по запросу: <b>{query}</b>", parse_mode="HTML")
        
        try:
            parser = OzonParser(delay=1.5)
            logger.info(f"Начинаю парсинг Ozon для запроса: {query}")
            products = parser.parse_search(query, limit=10)
            logger.info(f"Парсер вернул {len(products)} товаров")
            
            if not products:
                await message.answer("❌ Товары не найдены")
                return
            
            # Сохранение с валидацией
            product_models = []
            for p in products:
                product = self._validate_and_normalize_product(p)
                if product:
                    product_models.append(product)
            
            if product_models:
                self.storage.save_products(product_models)
            
            text = f"✅ Найдено товаров: {len(products)}\n\n"
            for i, product in enumerate(products[:5], 1):
                text += f"{i}. <b>{product.get('name', 'N/A')[:50]}</b>\n"
                text += f"   💰 {product.get('price', 0):.0f} ₽\n\n"
            
            if len(products) > 5:
                text += f"... и еще {len(products) - 5} товаров\n"
            
            text += "\n✅ Данные сохранены!"
            await message.answer(text, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Ошибка парсинга Ozon: {e}")
            await message.answer(f"❌ Ошибка: {str(e)}")
    
    async def cmd_uzum(self, message: Message):
        """Парсинг Uzum Market"""
        query = message.text.replace("/uzum", "").strip()
        if not query:
            await message.answer("❌ Укажите запрос. Пример: /uzum телефон")
            return
        
        await message.answer(f"⏳ Ищу товары на Uzum Market по запросу: <b>{query}</b>", parse_mode="HTML")
        
        try:
            parser = UzumParser(delay=1.5)
            logger.info(f"Начинаю парсинг Uzum Market для запроса: {query}")
            products = parser.parse_search(query, limit=10)
            logger.info(f"Парсер вернул {len(products)} товаров")
            
            if not products:
                await message.answer(
                    "❌ Товары не найдены\n\n"
                    "Возможные причины:\n"
                    "• Запрос не дал результатов\n"
                    "• Временные проблемы с сайтом\n"
                    "• Попробуйте другой запрос"
                )
                logger.warning(f"Товары не найдены для запроса: {query}")
                return
            
            # Сохранение с валидацией
            try:
                product_models = []
                for p in products:
                    product = self._validate_and_normalize_product(p)
                    if product:
                        product_models.append(product)
                
                if product_models:
                    self.storage.save_products(product_models)
            except Exception as e:
                logger.error(f"Ошибка сохранения: {e}")
            
            # Отправка результатов
            text = f"✅ Найдено товаров: {len(products)}\n\n"
            for i, product in enumerate(products[:5], 1):
                name = product.get('name', 'N/A')[:50]
                price = product.get('price', 0)
                rating = product.get('rating', 0)
                
                text += f"{i}. <b>{name}</b>\n"
                if price > 0:
                    text += f"   💰 {price:.0f} сум\n"
                if rating > 0:
                    text += f"   ⭐ {rating}\n"
                text += "\n"
            
            if len(products) > 5:
                text += f"... и еще {len(products) - 5} товаров\n"
            
            text += "\n✅ Данные сохранены!"
            await message.answer(text, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Ошибка парсинга Uzum Market: {e}", exc_info=True)
            await message.answer(f"❌ Ошибка: {str(e)}")
    
    async def cmd_yandex_maps(self, message: Message):
        """Парсинг Яндекс.Карт"""
        parts = message.text.replace("/yandex", "").strip().split(maxsplit=1)
        query = parts[0] if parts else ""
        location = parts[1] if len(parts) > 1 else None
        
        if not query:
            await message.answer("❌ Укажите запрос. Пример: /yandex ресторан Москва")
            return
        
        await message.answer(
            f"⏳ Ищу организации в Яндекс.Картах:\n"
            f"Запрос: <b>{query}</b>\n"
            f"Локация: <b>{location or 'не указана'}</b>",
            parse_mode="HTML"
        )
        
        try:
            parser = YandexMapsParser(delay=1.5)
            organizations = parser.search_organizations(query, location, limit=10)
            
            if not organizations:
                await message.answer("❌ Организации не найдены")
                return
            
            org_models = [Organization(**o) for o in organizations if o.get('name')]
            self.storage.save_organizations(org_models)
            
            text = f"✅ Найдено организаций: {len(organizations)}\n\n"
            for i, org in enumerate(organizations[:5], 1):
                text += f"{i}. <b>{org.get('name', 'N/A')}</b>\n"
                if org.get('address'):
                    text += f"   📍 {org.get('address')[:40]}\n"
                if org.get('rating'):
                    text += f"   ⭐ {org.get('rating')} ({org.get('reviews_count', 0)} отзывов)\n"
                text += "\n"
            
            if len(organizations) > 5:
                text += f"... и еще {len(organizations) - 5} организаций\n"
            
            text += "\n✅ Данные сохранены!"
            await message.answer(text, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Ошибка парсинга Яндекс.Карт: {e}")
            await message.answer(f"❌ Ошибка: {str(e)}")
    
    async def cmd_google_maps(self, message: Message):
        """Парсинг Google Maps"""
        parts = message.text.replace("/google", "").strip().split(maxsplit=1)
        query = parts[0] if parts else ""
        location = parts[1] if len(parts) > 1 else None
        
        if not query:
            await message.answer("❌ Укажите запрос. Пример: /google кофейня Москва")
            return
        
        await message.answer(
            f"⏳ Ищу организации в Google Maps:\n"
            f"Запрос: <b>{query}</b>\n"
            f"Локация: <b>{location or 'не указана'}</b>",
            parse_mode="HTML"
        )
        
        try:
            parser = GoogleMapsParser(delay=1.5)
            organizations = parser.search_organizations(query, location, limit=10)
            
            if not organizations:
                await message.answer("❌ Организации не найдены")
                return
            
            org_models = [Organization(**o) for o in organizations if o.get('name')]
            self.storage.save_organizations(org_models)
            
            text = f"✅ Найдено организаций: {len(organizations)}\n\n"
            for i, org in enumerate(organizations[:5], 1):
                text += f"{i}. <b>{org.get('name', 'N/A')}</b>\n"
                if org.get('address'):
                    text += f"   📍 {org.get('address')[:40]}\n"
                text += "\n"
            
            text += "\n✅ Данные сохранены!"
            await message.answer(text, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Ошибка парсинга Google Maps: {e}")
            await message.answer(f"❌ Ошибка: {str(e)}")
    
    async def cmd_2gis(self, message: Message):
        """Парсинг 2ГИС"""
        parts = message.text.replace("/2gis", "").strip().split(maxsplit=1)
        query = parts[0] if parts else ""
        location = parts[1] if len(parts) > 1 else "moscow"
        
        if not query:
            await message.answer("❌ Укажите запрос. Пример: /2gis кафе Москва")
            return
        
        await message.answer(
            f"⏳ Ищу организации в 2ГИС:\n"
            f"Запрос: <b>{query}</b>\n"
            f"Город: <b>{location}</b>",
            parse_mode="HTML"
        )
        
        try:
            parser = TwoGISParser(city=location.lower(), delay=1.5)
            organizations = parser.search_organizations(query, limit=10)
            
            if not organizations:
                await message.answer("❌ Организации не найдены")
                return
            
            org_models = [Organization(**o) for o in organizations if o.get('name')]
            self.storage.save_organizations(org_models)
            
            text = f"✅ Найдено организаций: {len(organizations)}\n\n"
            for i, org in enumerate(organizations[:5], 1):
                text += f"{i}. <b>{org.get('name', 'N/A')}</b>\n"
                if org.get('address'):
                    text += f"   📍 {org.get('address')[:40]}\n"
                if org.get('category'):
                    text += f"   🏷️ {org.get('category')}\n"
                text += "\n"
            
            text += "\n✅ Данные сохранены!"
            await message.answer(text, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Ошибка парсинга 2ГИС: {e}")
            await message.answer(f"❌ Ошибка: {str(e)}")
    
    async def cmd_stats(self, message: Message):
        """Статистика сохраненных данных"""
        products = self.storage.get_products()
        organizations = self.storage.get_organizations()
        
        # Статистика по источникам
        wb_count = len(self.storage.get_products(filters={'source': 'wildberries'}))
        ozon_count = len(self.storage.get_products(filters={'source': 'ozon'}))
        uzum_count = len(self.storage.get_products(filters={'source': 'uzum'}))
        yandex_count = len(self.storage.get_organizations(filters={'source': 'yandex_maps'}))
        google_count = len(self.storage.get_organizations(filters={'source': 'google_maps'}))
        gis_count = len(self.storage.get_organizations(filters={'source': '2gis'}))
        
        text = f"""
📊 <b>Статистика данных:</b>

<b>Товары:</b>
• Всего: {len(products)}
• Wildberries: {wb_count}
• Ozon: {ozon_count}
• Uzum Market: {uzum_count}

<b>Организации:</b>
• Всего: {len(organizations)}
• Яндекс.Карты: {yandex_count}
• Google Maps: {google_count}
• 2ГИС: {gis_count}
"""
        await message.answer(text, parse_mode="HTML")
    
    async def cmd_clear(self, message: Message):
        """Очистка данных"""
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="✅ Да", callback_data="clear_confirm"))
        keyboard.add(InlineKeyboardButton(text="❌ Нет", callback_data="clear_cancel"))
        
        await message.answer(
            "⚠️ Вы уверены, что хотите очистить все данные?",
            reply_markup=keyboard.as_markup()
        )
    
    async def handle_callback(self, callback: types.CallbackQuery):
        """Обработка инлайн-кнопок"""
        data = callback.data
        
        if data == "clear_confirm":
            # Очистка данных (удаление файлов)
            import os
            from pathlib import Path
            data_dir = Path("data")
            products_file = data_dir / "products.json"
            orgs_file = data_dir / "organizations.json"
            
            if products_file.exists():
                products_file.unlink()
            if orgs_file.exists():
                orgs_file.unlink()
            
            # Переинициализация
            self.storage = JSONStorage()
            
            await callback.message.edit_text("✅ Данные очищены!")
        elif data == "clear_cancel":
            await callback.message.edit_text("❌ Отменено")
        elif data == "stats":
            await self.cmd_stats(callback.message)
        
        await callback.answer()
    
    async def start(self):
        """Запуск бота"""
        logger.info("Бот запущен")
        await self.dp.start_polling(self.bot)
    
    async def stop(self):
        """Остановка бота"""
        await self.bot.session.close()
        logger.info("Бот остановлен")
