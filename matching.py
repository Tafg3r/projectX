from rapidfuzz import fuzz, process
from collections import defaultdict
import re

# Кэш для обработанных названий
_processed_titles = {}
_brand_models = {}

def preprocess_text(text):
    """Предварительная обработка текста"""
    if text in _processed_titles:
        return _processed_titles[text]
    
    # Приведение к нижнему регистру и базовая очистка
    text = text.lower().strip()
    
    # Стандартизация единиц измерения
    text = re.sub(r'(\d+)\s*(gb|гб)', r'\1gb', text)
    text = re.sub(r'(\d+)\s*(tb|тб)', r'\1tb', text)
    text = re.sub(r'(\d+)\s*(мл|ml)', r'\1ml', text)
    
    # Удаление специальных символов
    text = re.sub(r'[^\w\s-]', ' ', text)
    
    # Нормализация пробелов
    text = ' '.join(text.split())
    
    _processed_titles[text] = text
    return text

def extract_brand_model(title):
    """Извлекает бренд и модель из названия товара"""
    if title in _brand_models:
        return _brand_models[title]
    
    words = preprocess_text(title).split()
    if not words:
        return '', ''
    
    # Определение бренда (первое слово или известные бренды)
    brand = words[0]
    
    # Извлечение модели (обычно следует за брендом и содержит цифры/буквы)
    model_words = []
    for word in words[1:3]:  # Берем до 2 слов после бренда
        if re.search(r'\d', word) or len(word) >= 4:  # Предполагаем, что это часть модели
            model_words.append(word)
    
    model = ' '.join(model_words) if model_words else ''
    
    result = (brand, model)
    _brand_models[title] = result
    return result

def get_category_weights(category):
    """Возвращает веса для конкретной категории товаров"""
    # Можно настроить разные веса для разных категорий
    weights = defaultdict(lambda: {
        'title': 0.5,
        'brand': 0.3,
        'model': 0.2,
        'ngram': 0.1,
        'token_sort': 0.2
    })
    
    # Специальные веса для электроники (где модель важнее)
    weights['электроника'] = {
        'title': 0.4,
        'brand': 0.3,
        'model': 0.3,
        'ngram': 0.2,
        'token_sort': 0.2
    }
    
    return weights.get(category.lower(), weights['default'])

def score_match(source_title, candidate):
    """Комплексная оценка соответствия с улучшенными метриками"""
    if not source_title or not candidate or not candidate.get('title'):
        return 0
    
    # Предварительная обработка текста
    source_title = preprocess_text(source_title)
    candidate_title = preprocess_text(candidate.get('title', ''))
    category = candidate.get('category', '').lower()
    
    # Извлекаем бренд и модель
    source_brand, source_model = extract_brand_model(source_title)
    candidate_brand, candidate_model = extract_brand_model(candidate_title)
    
    # Получаем веса для категории
    weights = get_category_weights(category)
    
    # Расширенные метрики сходства
    metrics = {
        'title': fuzz.token_set_ratio(source_title, candidate_title),
        'brand': fuzz.ratio(source_brand, candidate_brand),
        'model': fuzz.ratio(source_model, candidate_model),
        'ngram': fuzz.QRatio(source_title, candidate_title),  # Учитывает опечатки
        'token_sort': fuzz.token_sort_ratio(source_title, candidate_title)  # Учитывает порядок слов
    }
    
    # Расчет взвешенного счета
    score = sum(weights[key] * metrics[key] for key in metrics)
    
    # Штрафы и бонусы
    if category:
        # Штраф за несоответствие категории
        if source_brand.lower() in ['водонагреватель'] and 'водонагреватель' not in category:
            score *= 0.5
        
        # Бонус за полное совпадение бренда и модели
        if source_brand == candidate_brand and source_model == candidate_model:
            score = min(100, score * 1.2)
    
    return score

def choose_best_candidate(source_title, candidates, topn=5):
    """Выбор лучших кандидатов с учетом всех параметров"""
    if not candidates:
        return []
    
    scored = []
    for cand in candidates:
        cand_score = score_match(source_title, cand)
        cand_copy = cand.copy()
        cand_copy['_score'] = cand_score
        scored.append(cand_copy)
    
    # Сортируем по убыванию оценки
    scored.sort(key=lambda x: x.get('_score', 0), reverse=True)
    return scored[:topn]