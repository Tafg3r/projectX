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

def apply_filters(driver, specs):
    """Применяет фильтры поиска на странице Kaspi"""
    try:
        # Открываем фильтры
        filter_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-test-id="filter-button"]'))
        )
        filter_button.click()
        
        # Применяем фильтры RAM
        if specs['ram']:
            try:
                ram_filter = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, f"//div[contains(text(),'Оперативная память')]/following-sibling::div//span[contains(text(),'{specs['ram']} ГБ')]"))
                )
                ram_filter.click()
            except Exception as e:
                logging.warning(f"RAM filter not found: {e}")
        
        # Применяем фильтры процессора
        if specs['processor']:
            try:
                proc_filter = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, f"//div[contains(text(),'Процессор')]/following-sibling::div//span[contains(text(),'{specs['processor']}')]"))
                )
                proc_filter.click()
            except Exception as e:
                logging.warning(f"Processor filter not found: {e}")
        
        # Применяем фильтры накопителя
        if specs['storage']:
            try:
                storage_filter = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, f"//div[contains(text(),'Объем накопителя')]/following-sibling::div//span[contains(text(),'{specs['storage']}')]"))
                )
                storage_filter.click()
            except Exception as e:
                logging.warning(f"Storage filter not found: {e}")
        
        # Показать результаты
        show_results = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-test-id="show-results-button"]'))
        )
        show_results.click()
        
    except Exception as e:
        logging.warning(f"Failed to apply filters: {e}")

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

def fetch_search_results(query, proxy=None):
    """Основная функция поиска товаров на Kaspi."""
    try:
        html = scrape_kaspi(query)
        products = parse_products(html)
        if not products:
            logging.warning(f"No products found for query: {query}")
        return products
    except Exception as e:
        logging.error(f"Error fetching results: {e}")
        return []

# Автоматическое закрытие браузера при выходе из программы
import atexit
atexit.register(close_driver)
