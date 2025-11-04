#!/usr/bin/env python3
"""Тестовый скрипт для отладки парсеров"""
import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_uzum():
    """Тестируем Uzum Market"""
    print("\n" + "="*60)
    print("ТЕСТ UZUM MARKET")
    print("="*60)
    
    url = "https://uzum.uz/ru/search?query=samsung"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Content Length: {len(response.text)}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем разные элементы
        print("\n--- Поиск элементов ---")
        print(f"Все div: {len(soup.find_all('div'))}")
        print(f"Все a: {len(soup.find_all('a'))}")
        print(f"Все article: {len(soup.find_all('article'))}")
        
        # Ищем по классам
        classes_found = set()
        for div in soup.find_all('div', class_=True)[:50]:
            classes_found.add(' '.join(div.get('class', [])))
        print(f"\nНайдено классов (первые 20): {list(classes_found)[:20]}")
        
        # Ищем текст с "samsung"
        samsung_elements = soup.find_all(string=lambda text: text and 'samsung' in text.lower())
        print(f"\nЭлементов с 'samsung': {len(samsung_elements)}")
        if samsung_elements:
            print(f"Пример: {samsung_elements[0][:100]}")
        
        # Сохраняем HTML для анализа
        with open('uzum_debug.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("\nHTML сохранен в uzum_debug.html")
        
    except Exception as e:
        print(f"Ошибка: {e}")

def test_wildberries():
    """Тестируем Wildberries"""
    print("\n" + "="*60)
    print("ТЕСТ WILDBERRIES")
    print("="*60)
    
    # Сначала пробуем API
    api_url = "https://search.wb.ru/exactmatch/ru/common/v4/search"
    params = {
        'query': 'телефон',
        'resultset': 'catalog',
        'limit': 10,
        'appType': 1,
        'curr': 'rub',
        'dest': -1257786,
        'lang': 'ru',
        'locale': 'ru',
    }
    
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    try:
        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        print(f"API Status Code: {response.status_code}")
        print(f"API Response Length: {len(response.text)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"\nAPI JSON Keys: {list(data.keys())}")
                if 'data' in data:
                    print(f"Data Keys: {list(data['data'].keys()) if isinstance(data['data'], dict) else 'list'}")
                    if 'products' in data.get('data', {}):
                        print(f"Products count: {len(data['data']['products'])}")
            except:
                print("Не JSON ответ")
                print(f"Первые 500 символов: {response.text[:500]}")
        
        # Теперь веб-версия
        web_url = "https://www.wildberries.ru/catalog/0/search.aspx?search=телефон"
        response = requests.get(web_url, headers=headers, timeout=10)
        print(f"\nWeb Status Code: {response.status_code}")
        print(f"Web Content Length: {len(response.text)}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        print(f"Все div: {len(soup.find_all('div'))}")
        
        # Сохраняем для анализа
        with open('wb_debug.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("HTML сохранен в wb_debug.html")
        
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == '__main__':
    test_uzum()
    test_wildberries()
