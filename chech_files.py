import os

print("Текущая рабочая директория:", os.getcwd())
print("\nСодержимое текущей папки:")
for item in os.listdir('src'):
    print(f"  - {item}")

print("\nПроверяем наличие Excel файлов:")
excel_files = []
for root, dirs, files in os.walk('src'):
    for file in files:
        if file.endswith(('.xls', '.xlsx')):
            full_path = os.path.join(root, file)
            excel_files.append(full_path)
            print(f"  Найден Excel файл: {full_path}")

if not excel_files:
    print("  Excel файлы не найдены!")

print("\nПроверяем папку data:")
if os.path.exists('data'):
    print("  Папка 'data' существует")
    if os.listdir('data'):
        print("  Содержимое папки 'data':")
        for item in os.listdir('data'):
            print(f"    - {item}")
    else:
        print("  Папка 'data' пуста")
else:
    print("  Папка 'data' не существует")