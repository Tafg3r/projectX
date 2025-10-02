import argparse, os, time, random, math, logging
from config import PROXIES, CHUNK_SIZE, FUZZY_THRESHOLD, SECONDARY_THRESHOLD
from excel_utils import read_input_excel, write_output_chunks
from kaspi_api import fetch_search_results
from matching import choose_best_candidate, score_match
from filters import extract_specs
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def process_file(input_path, sheet_name=None, input_col='Номенклатура поставщика', out_dir='./output', start_row=0, max_rows=None):
    df = read_input_excel(input_path, sheet_name=sheet_name)
    # Skip rows if needed
    df = df.iloc[start_row:].reset_index(drop=True)
    if max_rows:
        df = df.head(int(max_rows))
    if input_col not in df.columns:
        raise KeyError(f"Column '{input_col}' not found in input file. Columns: {df.columns.tolist()}")
    
    queries = df[input_col].astype(str).fillna('').tolist()
    results = []
    
    for idx, q in enumerate(queries):
        original_query = q.strip()
        if not original_query:
            results.append({'query': q, 'best_id': None, 'best_title': None, 'best_price': None, 'score': None, 'url': None})
            continue
        
        # Создаем варианты поисковых запросов
        search_queries = []
        
        # 1. Сначала пробуем полное название с характеристиками
        parts = original_query.split('/')
        if len(parts) > 1:
            # Извлекаем ключевые характеристики
            specs = []
            for part in parts[1:]:
                # Ищем объем памяти, процессор, видеокарту
                if any(x in part.lower() for x in ['gb', 'гб', 'tb', 'тб', 'core', 'ryzen', 'radeon', 'geforce', 'rtx', 'gtx']):
                    specs.append(part.strip())
            
            # Формируем запрос с характеристиками
            base_query = parts[0].strip()
            if specs:
                # Добавляем запрос с полными характеристиками
                full_query = f"{base_query} {' '.join(specs[:2])}"  # Берем первые 2 важные характеристики
                search_queries.append(full_query)
            
            # Добавляем запрос только с брендом и моделью
            search_queries.append(base_query)
        else:
            search_queries.append(original_query)
            
        # 2. Если запрос не дал результатов, пробуем только бренд и модель
        words = parts[0].split()
        if len(words) >= 2:
            brand_model = ' '.join(words[:2])
            if brand_model not in search_queries:
                search_queries.append(brand_model)
        
        logging.info(f"Search variations for '{original_query}': {search_queries}")
        
        # Пробуем каждый вариант поиска
        best_result = None
        best_score = -1
        proxy = random.choice(PROXIES) if PROXIES else None
        
        # Извлекаем характеристики для фильтров
        specs = extract_specs(original_query)
        logging.info(f"Extracted specs: {specs}")
        
        for search_query in search_queries:
            try:
                logging.info(f"Trying search query: {search_query}")
                # Передаем характеристики для использования фильтров
                candidates = fetch_search_results(search_query, proxy=proxy, specs=specs)
                if candidates:
                    logging.info(f"Found {len(candidates)} products")
                    # Для каждого кандидата проверяем соответствие оригинальному запросу
                    scored = choose_best_candidate(original_query, candidates, topn=5)
                    if scored:
                        current_score = scored[0].get('_score', 0)
                        if current_score > best_score:
                            best_result = scored[0]
                            best_score = current_score
                            logging.info(f"Found better match: {best_result.get('title')} (score: {best_score})")
                            logging.info(f"Product ID: {best_result.get('id')}, Price: {best_result.get('price')}")
            except Exception as e:
                logging.warning(f"Failed to fetch for '{search_query}': {e}")
                continue
            
            # Если нашли хороший результат, можно прекратить поиск
            if best_score >= FUZZY_THRESHOLD:
                break
        
        # Определяем статус поиска
        status = "не найден"
        if best_result and best_score >= FUZZY_THRESHOLD:
            status = "найден"
        elif best_result and best_score > 0:
            status = f"возможное совпадение (score: {best_score})"
        
        # Добавляем результат всегда, независимо от score
        results.append({
            'query': q,
            'best_id': best_result.get('id') if best_result else None,
            'best_title': best_result.get('title') if best_result else None,
            'best_price': best_result.get('price') if best_result else None,
            'score': best_score if best_score > -1 else None,
            'url': best_result.get('url') if best_result else None,
            'status': f"{status} (score: {best_score:.2f})" if best_result else "не найден"
        })
        
        # Прогресс с дополнительной информацией
        if (idx + 1) % 10 == 0:
            found = sum(1 for r in results[-10:] if r['best_id'] is not None)
            not_found = 10 - found
            logging.info(f"Processed {idx + 1} / {len(queries)} items. Last 10 items: {found} found, {not_found} not found")
    
    # Обновляем колонки в DataFrame
    out_df = df.copy()
    
    # Создаем временные колонки для Kaspi данных
    kaspi_ids = [str(result['best_id']) if result['best_id'] else "не найден" for result in results]
    kaspi_prices = [float(result['best_price']) if result['best_price'] else None for result in results]
    kaspi_status = [result['status'] for result in results]
    
    # Добавляем колонки для Kaspi данных
    out_df['код каспи'] = pd.Series(kaspi_ids, dtype='object')
    out_df['цена каспи'] = pd.Series(kaspi_prices, dtype='float64')
    out_df['статус поиска'] = pd.Series(kaspi_status, dtype='object')
    
    # Записываем результат
    paths = write_output_chunks(out_df, out_dir, base_name=os.path.splitext(os.path.basename(input_path))[0], chunk_size=CHUNK_SIZE)
    logging.info(f"Wrote {len(paths)} files to {out_dir}")
    return paths

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--input', '-i', help='Input Excel file path')
    group.add_argument('--query', '-q', help='Single query to process')
    
    parser.add_argument('--sheet', '-s', default=None, help='Sheet name (optional, for Excel input)')
    parser.add_argument('--col', '-c', default='Номенклатура поставщика', help='Column name with queries (for Excel input)')
    parser.add_argument('--out', default='./output', help='Output directory')
    parser.add_argument('--start-row', type=int, default=0, help='Start processing from this row (0-based index)')
    parser.add_argument('--max-rows', type=int, default=None, help='Limit input rows to first N rows (for testing)')
    args = parser.parse_args()
    
    try:
        if args.input:
            paths = process_file(args.input, sheet_name=args.sheet, input_col=args.col,
                               out_dir=args.out, start_row=args.start_row, max_rows=args.max_rows)
            print('Output files:', paths)
        else:
            # Извлекаем характеристики для фильтров
            specs = extract_specs(args.query)
            logging.info(f"Extracted specs: {specs}")
            
            proxy = random.choice(PROXIES) if PROXIES else None
            candidates = fetch_search_results(args.query, proxy=proxy, specs=specs)
            
            if candidates:
                logging.info(f"Found {len(candidates)} products")
                scored = choose_best_candidate(args.query, candidates, topn=5)
                if scored:
                    for idx, result in enumerate(scored[:5], 1):
                        print(f"\nMatch #{idx}:")
                        print(f"Title: {result.get('title')}")
                        print(f"Score: {result.get('_score')}")
                        print(f"Price: {result.get('price')}")
                        print(f"URL: {result.get('url')}")
                else:
                    print("No matches found")
            else:
                print("No products found")
                
    except Exception as e:
        print('Error:', e)
        import sys
        sys.exit(1)