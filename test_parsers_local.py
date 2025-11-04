#!/usr/bin/env python3
"""Простой тест парсеров для локальной проверки"""
import sys
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_wildberries():
    """Тест Wildberries парсера"""
    print("\n" + "="*60)
    print("ТЕСТ WILDBERRIES")
    print("="*60)
    
    try:
        from parsers.marketplace import WildberriesParser
        
        parser = WildberriesParser(delay=1.0)
        query = "телефон"
        
        print(f"\nЗапрос: {query}")
        products = parser.parse_search(query, limit=5)
        
        print(f"\nРезультат: найдено {len(products)} товаров")
        
        if products:
            print("\nПервый товар:")
            for key, value in products[0].items():
                print(f"  {key}: {value}")
        else:
            print("\n❌ Товары не найдены")
            
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

def test_uzum():
    """Тест Uzum парсера"""
    print("\n" + "="*60)
    print("ТЕСТ UZUM MARKET")
    print("="*60)
    
    try:
        from parsers.marketplace import UzumParser
        
        parser = UzumParser(delay=1.0)
        query = "samsung"
        
        print(f"\nЗапрос: {query}")
        products = parser.parse_search(query, limit=5)
        
        print(f"\nРезультат: найдено {len(products)} товаров")
        
        if products:
            print("\nПервый товар:")
            for key, value in products[0].items():
                print(f"  {key}: {value}")
        else:
            print("\n❌ Товары не найдены")
            
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'wb':
            test_wildberries()
        elif sys.argv[1] == 'uzum':
            test_uzum()
        else:
            print("Использование: python test_parsers_local.py [wb|uzum]")
    else:
        test_wildberries()
        test_uzum()
