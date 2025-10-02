from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
import time

def apply_filters(driver, specs):
    """Применяет фильтры на странице Kaspi"""
    try:
        # Ждем загрузки фильтров
        filter_section = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "side-bar-filter"))
        )
        
        # Применяем фильтр RAM если указан
        if specs.get('ram'):
            try:
                # Находим и раскрываем секцию RAM если она свернута
                ram_filter = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, 
                        f"//div[contains(text(), 'Оперативная память')]"))
                )
                ram_filter.click()
                
                # Выбираем значение RAM
                ram_value = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, 
                        f"//div[contains(text(), 'Оперативная память')]/..//label[contains(text(), '{specs['ram']} ГБ')]"))
                )
                ram_value.click()
                logging.info(f"Applied RAM filter: {specs['ram']} ГБ")
                
                # Ждем обновления результатов
                time.sleep(1)
                
            except (TimeoutException, NoSuchElementException) as e:
                logging.warning(f"Failed to apply RAM filter: {e}")

        # Применяем фильтр Storage если указан
        if specs.get('storage'):
            try:
                # Находим и раскрываем секцию Storage
                storage_filter = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, 
                        f"//div[contains(text(), 'Объем накопителя')]"))
                )
                storage_filter.click()
                
                # Выбираем значение Storage
                storage_value = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, 
                        f"//div[contains(text(), 'Объем накопителя')]/..//label[contains(text(), '{specs['storage']} ГБ')]"))
                )
                storage_value.click()
                logging.info(f"Applied Storage filter: {specs['storage']} ГБ")
                
                # Ждем обновления результатов
                time.sleep(1)
                
            except (TimeoutException, NoSuchElementException) as e:
                logging.warning(f"Failed to apply Storage filter: {e}")

        # Применяем фильтр процессора если указан
        if specs.get('processor'):
            try:
                processor_filter = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, 
                        f"//div[contains(text(), 'Процессор')]"))
                )
                processor_filter.click()
                
                # Выбираем процессор
                processor_value = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, 
                        f"//div[contains(text(), 'Процессор')]/..//label[contains(text(), '{specs['processor']}')]"))
                )
                processor_value.click()
                logging.info(f"Applied Processor filter: {specs['processor']}")
                
                # Ждем обновления результатов
                time.sleep(1)
                
            except (TimeoutException, NoSuchElementException) as e:
                logging.warning(f"Failed to apply Processor filter: {e}")

        # Даем время на применение всех фильтров
        time.sleep(2)
        
    except Exception as e:
        logging.error(f"Error applying filters: {e}")