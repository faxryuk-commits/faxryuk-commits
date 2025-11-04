#!/usr/bin/env python3
"""
Тестовый скрипт для проверки парсеров локально
"""

import logging
from parsers.marketplace import WildberriesParser
from parsers.maps import YandexMapsParser

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_wildberries():
    """Тестирование парсера Wildberries"""
    print("=" * 50)
    print("Тест Wildberries")
    print("=" * 50)
    
    parser = WildberriesParser(delay=1.0)
    query = "телефон"
    
    print(f"Поиск: {query}")
    products = parser.parse_search(query, limit=5)
    
    print(f"\nНайдено товаров: {len(products)}")
    if products:
        for i, product in enumerate(products[:3], 1):
            print(f"\n{i}. {product.get('name', 'N/A')}")
            print(f"   Цена: {product.get('price', 0)} ₽")
            print(f"   ID: {product.get('id', 'N/A')}")
    else:
        print("❌ Товары не найдены")
    
    return products

def test_yandex_maps():
    """Тестирование парсера Яндекс.Карт"""
    print("\n" + "=" * 50)
    print("Тест Яндекс.Карты")
    print("=" * 50)
    
    parser = YandexMapsParser(delay=1.0)
    query = "рестораны"
    location = "Ташкент"
    
    print(f"Поиск: {query}, {location}")
    organizations = parser.search_organizations(query, location, limit=5)
    
    print(f"\nНайдено организаций: {len(organizations)}")
    if organizations:
        for i, org in enumerate(organizations[:3], 1):
            print(f"\n{i}. {org.get('name', 'N/A')}")
            print(f"   Адрес: {org.get('address', 'N/A')}")
    else:
        print("❌ Организации не найдены")
    
    return organizations

if __name__ == "__main__":
    print("�� Тестирование парсеров\n")
    
    try:
        test_wildberries()
        # test_yandex_maps()  # Раскомментируйте для теста Яндекс.Карт
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
