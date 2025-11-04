"""
Примеры использования парсеров маркетплейсов и карт
"""

from parsers.marketplace import WildberriesParser, OzonParser
from parsers.maps import GoogleMapsParser, YandexMapsParser, TwoGISParser
from models.data_models import Product, Organization
from storage import JSONStorage


def example_wildberries():
    """Пример парсинга Wildberries"""
    print("=" * 50)
    print("Парсинг Wildberries")
    print("=" * 50)
    
    parser = WildberriesParser(delay=2.0)  # Задержка 2 секунды между запросами
    products = parser.parse_search("ноутбук", limit=5)
    
    print(f"Найдено товаров: {len(products)}")
    for product in products[:3]:
        print(f"\nТовар: {product.get('name', 'N/A')}")
        print(f"Цена: {product.get('price', 0)} руб.")
        print(f"Рейтинг: {product.get('rating', 0)}")
        print(f"URL: {product.get('url', 'N/A')}")
    
    # Сохранение в хранилище
    storage = JSONStorage()
    product_models = [Product(**p) for p in products if p.get('name')]
    storage.save_products(product_models)
    print("\n✅ Данные сохранены!")


def example_ozon():
    """Пример парсинга Ozon"""
    print("\n" + "=" * 50)
    print("Парсинг Ozon")
    print("=" * 50)
    
    parser = OzonParser(delay=2.0)
    products = parser.parse_search("телефон", limit=5)
    
    print(f"Найдено товаров: {len(products)}")
    for product in products[:3]:
        print(f"\nТовар: {product.get('name', 'N/A')}")
        print(f"Цена: {product.get('price', 0)} руб.")
        print(f"Рейтинг: {product.get('rating', 0)}")


def example_yandex_maps():
    """Пример парсинга Яндекс.Карт"""
    print("\n" + "=" * 50)
    print("Парсинг Яндекс.Карт")
    print("=" * 50)
    
    parser = YandexMapsParser(delay=2.0)
    organizations = parser.search_organizations("ресторан", location="Москва", limit=5)
    
    print(f"Найдено организаций: {len(organizations)}")
    for org in organizations[:3]:
        print(f"\nОрганизация: {org.get('name', 'N/A')}")
        print(f"Адрес: {org.get('address', 'N/A')}")
        print(f"Рейтинг: {org.get('rating', 0)}")
        print(f"Отзывов: {org.get('reviews_count', 0)}")
    
    # Сохранение в хранилище
    storage = JSONStorage()
    org_models = [Organization(**o) for o in organizations if o.get('name')]
    storage.save_organizations(org_models)
    print("\n✅ Данные сохранены!")


def example_2gis():
    """Пример парсинга 2ГИС"""
    print("\n" + "=" * 50)
    print("Парсинг 2ГИС")
    print("=" * 50)
    
    parser = TwoGISParser(city="moscow", delay=2.0)
    organizations = parser.search_organizations("кафе", limit=5)
    
    print(f"Найдено организаций: {len(organizations)}")
    for org in organizations[:3]:
        print(f"\nОрганизация: {org.get('name', 'N/A')}")
        print(f"Адрес: {org.get('address', 'N/A')}")
        print(f"Категория: {org.get('category', 'N/A')}")


def example_google_maps():
    """Пример парсинга Google Maps"""
    print("\n" + "=" * 50)
    print("Парсинг Google Maps")
    print("=" * 50)
    
    parser = GoogleMapsParser(delay=2.0)
    organizations = parser.search_organizations("кофейня", location="Санкт-Петербург", limit=3)
    
    print(f"Найдено организаций: {len(organizations)}")
    for org in organizations:
        print(f"\nОрганизация: {org.get('name', 'N/A')}")
        print(f"Адрес: {org.get('address', 'N/A')}")
        print(f"Рейтинг: {org.get('rating', 0)}")


def example_storage():
    """Пример работы с хранилищем данных"""
    print("\n" + "=" * 50)
    print("Работа с хранилищем")
    print("=" * 50)
    
    storage = JSONStorage()
    
    # Получение всех товаров
    all_products = storage.get_products()
    print(f"Всего товаров в хранилище: {len(all_products)}")
    
    # Фильтрация товаров
    wb_products = storage.get_products(filters={'source': 'wildberries'})
    print(f"Товаров с Wildberries: {len(wb_products)}")
    
    # Получение организаций
    all_orgs = storage.get_organizations()
    print(f"Всего организаций в хранилище: {len(all_orgs)}")


def example_uzum():
    """Пример парсинга Uzum Market"""
    print("\n" + "=" * 50)
    print("Парсинг Uzum Market")
    print("=" * 50)
    
    parser = UzumParser(delay=2.0)
    products = parser.parse_search("телефон", limit=5)
    
    print(f"Найдено товаров: {len(products)}")
    for product in products[:3]:
        print(f"\nТовар: {product.get('name', 'N/A')}")
        print(f"Цена: {product.get('price', 0):.0f} сум")
        print(f"Рейтинг: {product.get('rating', 0)}")


if __name__ == "__main__":
    print("🚀 Запуск примеров парсинга\n")
    print("⚠️  Внимание: Парсинг может занять некоторое время из-за задержек между запросами\n")
    
    try:
        # Раскомментируйте нужные примеры
        # example_wildberries()
        # example_ozon()
        # example_uzum()
        # example_yandex_maps()
        # example_2gis()
        # example_google_maps()
        # example_storage()
        
        print("\n✅ Примеры готовы к использованию!")
        print("Раскомментируйте нужные функции в __main__ для запуска")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
