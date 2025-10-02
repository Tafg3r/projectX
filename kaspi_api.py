import requests
from urllib.parse import quote
import re
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
from bs4 import BeautifulSoup
from config import PROXIES, TIMEOUT, MIN_DELAY, MAX_DELAY
from kaspi_filters import apply_filters

# Глобальный драйвер для повторного использования
driver = None

def init_driver():
    """Инициализация headless Chrome браузера."""
    global driver
    if driver is None:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-dev-shm-usage")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    return driver

def close_driver():
    """Закрытие браузера."""
    global driver
    if driver:
        driver.quit()
        driver = None

def scrape_kaspi(query: str, specs=None) -> str:
    """Получение HTML страницы с результатами поиска Kaspi."""
    driver = init_driver()
    encoded = quote(query, safe='')
    url = f"https://kaspi.kz/shop/search/?text={encoded}"
    
    logging.info(f"Fetching URL: {url}")
    driver.get(url)
    
    # Закрыть баннер с куками если есть
    try:
        cookie_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test-id="cookie-banner-accept-button"]'))
        )
        cookie_btn.click()
    except Exception:
        pass
        
    # Применяем фильтры если они есть
    if specs:
        apply_filters(driver, specs)

    # Прокрутка для загрузки товаров
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)  # Ждем загрузку

    # Дополнительное ожидание для JS-рендеринга
    time.sleep(2)
    
    return driver.page_source

def parse_products(html: str, limit=20):
    """Парсинг результатов поиска и возврат списка товаров."""
    products = []
    soup = BeautifulSoup(html, "html.parser")
    
    # Попытка извлечь данные из Next.js JSON
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if match:
        try:
            data = json.loads(match.group(1))
            items = (data.get('props', {})
                        .get('pageProps', {})
                        .get('initialData', {})
                        .get('data', {})
                        .get('products', []))
            if items:
                for item in items:
                    title = item.get('name')
                    # Проверяем категорию товара если она есть
                    category = item.get('category', {}).get('name', '').lower()
                    subcategory = item.get('category', {}).get('parentCategory', {}).get('name', '').lower()
                    
                    # Если есть название товара и категория подходящая
                    if title and category:
                        products.append({
                            'id': str(item.get('id')),
                            'title': title,
                            'price': item.get('price'),
                            'url': f"https://kaspi.kz/shop/p/{item.get('id')}/",
                            'category': category,
                            'subcategory': subcategory
                        })
                        
                # Сортируем по релевантности (наименование -> цена)
                products = sorted(products[:limit], key=lambda x: (-1 if x.get('category', '').lower() == 'water heaters' else 0, x.get('price', 0) or 0))
                return products[:limit]
        except Exception as e:
            logging.warning(f"JSON parse error: {e}")

    # Запасной вариант - парсинг HTML
    cards = soup.find_all("div", attrs={"data-product-id": True})
    for card in cards:
        prod_id = card.get("data-product-id")
        
        # Название товара
        title_tag = card.find("div", class_=lambda c: c and "item-card__name" in c)
        title = title_tag.get_text().strip() if title_tag else None
        
        # Цена (без рассрочки)
        price_tag = card.find("div", class_=lambda c: c and "item-card__price" in c and "item-card__transfer" not in c)
        price = None
        if price_tag:
            txt = price_tag.get_text()
            m = re.search(r'([\d\s]+)\s*₸', txt)
            if m:
                price = int(m.group(1).replace(' ', ''))
        
        # Категория товара
        category_tag = card.find("span", class_=lambda c: c and "item-card__category" in c)
        category = category_tag.get_text().strip().lower() if category_tag else ""
        
        if prod_id and title and price:
            products.append({
                'id': prod_id,
                'title': title,
                'price': price,
                'url': f"https://kaspi.kz/shop/p/{prod_id}/",
                'category': category
            })
    
    # Сортируем по релевантности
    products = sorted(products[:limit], key=lambda x: (-1 if 'водонагреватель' in x.get('title', '').lower() else 0, x.get('price', 0) or 0))
    return products[:limit]

def fetch_search_results(query, proxy=None, specs=None):
    """Основная функция поиска товаров на Kaspi."""
    try:
        html = scrape_kaspi(query, specs=specs)
        if not html:
            logging.warning(f"No HTML content received for query: {query}")
            return []
            
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        for card in soup.select('div.item-card'):
            try:
                # Ссылка и ID
                link_elem = card.select_one('a.item-card__name-link')
                if not link_elem:
                    continue
                
                link = 'https://kaspi.kz' + link_elem['href']
                item_id = link.split('/')[-1]
                
                # Название
                title = link_elem.text.strip()
                
                # Цена
                price_elem = card.select_one('span.item-card__prices-price')
                price = None
                if price_elem:
                    price_text = price_elem.text.strip()
                    price = int(''.join(filter(str.isdigit, price_text)))
                
                item = {
                    'id': item_id,
                    'title': title,
                    'price': price,
                    'url': link
                }
                items.append(item)
                
            except Exception as e:
                logging.warning(f"Error parsing card: {e}")
                continue
                
        if not items:
            logging.warning(f"No products found for query: {query}")
        return items
        
    except Exception as e:
        logging.error(f"Error fetching results: {e}")
        return []

# Автоматическое закрытие браузера при выходе из программы
import atexit
atexit.register(close_driver)
