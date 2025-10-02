import re

def extract_specs(query):
    """Извлекает характеристики из строки запроса"""
    specs = {
        'ram': None,
        'storage': None,
        'processor': None,
        'graphics': None,
        'screen_size': None,
        'os': None
    }
    
    # Извлечение RAM
    ram_match = re.search(r'(\d+)\s*(?:GB|Gb|ГБ|Гб)', query)
    if ram_match:
        specs['ram'] = ram_match.group(1)
    
    # Извлечение storage
    storage_match = re.search(r'(?:SSD|HDD)\s*(\d+)\s*(?:GB|Gb|ГБ|Гб|TB|Tb|ТБ|Тб)', query)
    if storage_match:
        specs['storage'] = storage_match.group(1)
    
    # Извлечение процессора
    cpu_patterns = [
        (r'Core i(\d+)[- ](\d+)', 'Intel Core i{0} {1}'),
        (r'Ryzen (\d+)[- ](\d+)', 'AMD Ryzen {0} {1}'),
        (r'Core Ultra (\d+)[- ](\d+)', 'Intel Core Ultra {0} {1}')
    ]
    
    for pattern, template in cpu_patterns:
        cpu_match = re.search(pattern, query, re.IGNORECASE)
        if cpu_match:
            specs['processor'] = template.format(*cpu_match.groups())
            break
    
    # Извлечение видеокарты
    gpu_patterns = [
        r'(?:GeForce|NVIDIA)\s*(?:RTX|GTX)\s*(\d+)',
        r'Radeon\s*(?:RX)?\s*(\d+)',
        r'Intel\s*(?:UHD|Iris)\s*(\d+)?'
    ]
    
    for pattern in gpu_patterns:
        gpu_match = re.search(pattern, query, re.IGNORECASE)
        if gpu_match:
            specs['graphics'] = gpu_match.group(0)
            break
    
    # Извлечение размера экрана
    screen_match = re.search(r'(\d+\.?\d*)\s*[\'\"]\']', query)
    if screen_match:
        specs['screen_size'] = screen_match.group(1)
    
    # Определение ОС
    os_patterns = {
        'windows': r'Windows\s*\d+(?:\s*(?:Home|Pro))?',
        'no_os': r'(?:Без ОС|Без операционн)',
        'dos': r'DOS',
        'linux': r'Linux'
    }
    
    for os_name, pattern in os_patterns.items():
        if re.search(pattern, query, re.IGNORECASE):
            specs['os'] = os_name
            break
    
    return specs