import pandas as pd

# Читаем первые 10 строк из файла
df = pd.read_excel('doc1000.xlsx', nrows=10)
print("\nПервые 10 товаров:")
for idx, row in df.iterrows():
    print(f"{idx + 1}. {row['Номенклатура поставщика']}")