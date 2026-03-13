import json
import logging
import os
import sys

from src.reports import detailed_category_analysis, spending_by_category, spending_by_weekday, spending_by_workday
from src.services import (
    analyze_cashback_categories,
    investment_bank,
    search_by_phone,
    search_transfers_to_individuals,
    simple_search,
)
from src.utils import read_transactions_from_excel
from src.views import generate_events_page_response, generate_main_page_response

# Добавляем корневую папку в путь поиска модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log", encoding="utf-8")],
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


def ensure_directories():
    """
    Создает необходимые директории, если их нет
    """
    directories = ["data/responses", "data/services"]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"✅ Директория создана/проверена: {directory}")


def check_data_file():
    """
    Проверяет наличие файла с данными
    """
    possible_paths = ["data/operations.xlsx", "data/operations.xls", "operations.xlsx", "operations.xls"]

    for path in possible_paths:
        if os.path.exists(path):
            # Если файл не в data/, перемещаем его
            if not path.startswith("data/"):
                import shutil

                os.makedirs("data", exist_ok=True)
                new_path = f"data/{os.path.basename(path)}"
                shutil.copy2(path, new_path)
                print(f"✅ Файл скопирован в: {new_path}")
                return new_path
            else:
                print(f"✅ Найден файл данных: {path}")
                return path

    print("❌ Файл с данными не найден!")
    print("   Убедитесь, что файл 'operations.xlsx' находится в папке 'data/'")
    return None


def save_json_response(data: str, filename: str, subdir: str = "responses"):
    """
    Сохраняет JSON-ответ в папку data
    """
    filepath = f"data/{subdir}/{filename}"

    # Убеждаемся, что директория существует
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(data)

    logger.info(f"✅ Сохранено: {filepath}")
    return filepath


def save_text_response(data: str, filename: str, subdir: str = "services"):
    """
    Сохраняет текстовый ответ в папку data
    """
    filepath = f"data/{subdir}/{filename}"

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(data)

    logger.info(f"✅ Сохранено: {filepath}")
    return filepath


def generate_main_page(input_date: str, excel_file: str):
    """
    Генерация главной страницы
    """
    print("\n" + "=" * 60)
    print("🏠 ГЛАВНАЯ СТРАНИЦА")
    print("=" * 60)

    response = generate_main_page_response(input_date, excel_file)

    # Сохраняем результат
    save_json_response(response, "main_response.json")

    print("📊 Превью (первые 300 символов):")
    print(response[:300] + "...")

    return response


def generate_events_page(input_date: str, excel_file: str):
    """
    Генерация страницы событий
    """
    print("\n" + "=" * 60)
    print("📅 СТРАНИЦА СОБЫТИЙ (период: МЕСЯЦ)")
    print("=" * 60)

    response = generate_events_page_response(input_date, "M", excel_file)

    # Сохраняем результат
    save_json_response(response, "events_response.json")

    print("📊 Превью (первые 300 символов):")
    print(response[:300] + "...")

    return response


def run_services(excel_file: str):
    """
    Запуск всех сервисов
    """
    print("\n" + "★" * 70)
    print("🛠️  ЗАПУСК СЕРВИСОВ")
    print("★" * 70)

    # Загружаем транзакции
    transactions_df = read_transactions_from_excel(excel_file)

    if transactions_df.empty:
        print("❌ Не удалось загрузить транзакции для сервисов")
        return

    # Преобразуем DataFrame в список словарей
    transactions = transactions_df.to_dict("records")

    # Сервис 1: Анализ кешбэка
    print("\n" + "-" * 70)
    print("📊 СЕРВИС 1: Анализ выгодных категорий кешбэка")
    print("-" * 70)
    cashback_result = analyze_cashback_categories(transactions, 2021, 12)
    print(cashback_result[:300] + "..." if len(cashback_result) > 300 else cashback_result)

    # Сохраняем результат
    save_json_response(cashback_result, "cashback.json", "services")

    # Сервис 2: Инвесткопилка
    print("\n" + "-" * 70)
    print("💰 СЕРВИС 2: Инвесткопилка (лимит 50 ₽)")
    print("-" * 70)
    investment_result = investment_bank("2021-12", transactions, 50)
    investment_text = f"Инвесткопилка за 2021-12: {investment_result} ₽"
    print(investment_text)

    # Сохраняем результат
    save_text_response(investment_text, "investment.txt", "services")

    # Сервис 3: Простой поиск
    print("\n" + "-" * 70)
    print("🔍 СЕРВИС 3: Простой поиск")
    print("-" * 70)

    search_terms = ["Перевод", "Супермаркет", "Ресторан"]
    for term in search_terms:
        print(f"\n   Поиск по строке: '{term}'")
        search_result = simple_search(transactions, term)
        found_count = len(json.loads(search_result))
        print(f"   Найдено транзакций: {found_count}")

        # Сохраняем результат
        safe_term = term.replace(" ", "_").lower()
        save_json_response(search_result, f"search_{safe_term}.json", "services")

    # Сервис 4: Поиск по телефону
    print("\n" + "-" * 70)
    print("📱 СЕРВИС 4: Поиск транзакций с номерами телефонов")
    print("-" * 70)
    phone_result = search_by_phone(transactions)
    phone_count = len(json.loads(phone_result))
    print(f"Найдено транзакций с телефонами: {phone_count}")
    print(phone_result[:300] + "..." if len(phone_result) > 300 else phone_result)

    # Сохраняем результат
    save_json_response(phone_result, "phone_search.json", "services")

    # Сервис 5: Поиск переводов физлицам
    print("\n" + "-" * 70)
    print("👤 СЕРВИС 5: Поиск переводов физическим лицам")
    print("-" * 70)
    transfers_result = search_transfers_to_individuals(transactions)
    transfers_count = len(json.loads(transfers_result))
    print(f"Найдено переводов физлицам: {transfers_count}")
    print(transfers_result[:300] + "..." if len(transfers_result) > 300 else transfers_result)

    # Сохраняем результат
    save_json_response(transfers_result, "transfers.json", "services")

    print("\n" + "✅" * 35)
    print("🎉 ВСЕ СЕРВИСЫ УСПЕШНО ВЫПОЛНЕНЫ!")
    print("✅" * 35)


def run_reports(excel_file: str):
    """Запуск отчетов"""
    print("\n" + "★" * 70)
    print("📊 ЗАПУСК ОТЧЕТОВ")
    print("★" * 70)

    transactions_df = read_transactions_from_excel(excel_file)

    if transactions_df.empty:
        print("❌ Не удалось загрузить транзакции для отчетов")
        return

    # Отчет 1: Траты по категории
    print("\n" + "-" * 70)
    print("📊 ОТЧЕТ 1: Траты по категории 'Супермаркеты'")
    result1 = spending_by_category(transactions_df, "Супермаркеты", "15.12.2021")
    print(result1.to_string() if not result1.empty else "Нет данных")

    # Отчет 2: Траты по дням недели
    print("\n" + "-" * 70)
    print("📊 ОТЧЕТ 2: Траты по дням недели")
    result2 = spending_by_weekday(transactions_df, "15.12.2021")
    print(result2.to_string())

    # Отчет 3: Рабочие/выходные
    print("\n" + "-" * 70)
    print("📊 ОТЧЕТ 3: Рабочие и выходные дни")
    result3 = spending_by_workday(transactions_df, "15.12.2021")
    print(result3.to_string())

    # Дополнительный отчет
    print("\n" + "-" * 70)
    print("📊 ОТЧЕТ 4: Детальный анализ категории 'Рестораны'")
    result4 = detailed_category_analysis(transactions_df, "Рестораны", "15.12.2021")
    print(json.dumps(result4, ensure_ascii=False, indent=2)[:500] + "...")

    print("\n✅ Отчеты выполнены")


def print_summary():
    """
    Выводит итоговую информацию о созданных файлах
    """
    print("\n" + "=" * 70)
    print("📋 ИТОГОВЫЙ ОТЧЕТ - СОЗДАННЫЕ ФАЙЛЫ")
    print("=" * 70)

    # Проверяем наличие файлов
    responses_dir = "data/responses"
    services_dir = "data/services"

    if os.path.exists(responses_dir):
        print(f"\n📁 Папка: {responses_dir}/")
        for file in sorted(os.listdir(responses_dir)):
            if file.endswith(".json"):
                filepath = os.path.join(responses_dir, file)
                size = os.path.getsize(filepath)
                print(f"   📄 {file} ({size} bytes)")

    if os.path.exists(services_dir):
        print(f"\n📁 Папка: {services_dir}/")
        for file in sorted(os.listdir(services_dir)):
            filepath = os.path.join(services_dir, file)
            size = os.path.getsize(filepath)
            print(f"   📄 {file} ({size} bytes)")

    print("\n" + "★" * 70)
    print("🎉 ВСЕ ФАЙЛЫ УСПЕШНО СОХРАНЕНЫ В ПАПКУ data/")
    print("★" * 70)


def main():
    """
    Основная функция для демонстрации работы
    """
    print("\n" + "★" * 70)
    print("          КУРСОВАЯ РАБОТА: АНАЛИЗ БАНКОВСКИХ ТРАНЗАКЦИЙ")
    print("★" * 70)

    # Создаем необходимые директории
    ensure_directories()

    # Находим файл с данными
    excel_file = check_data_file()
    if not excel_file:
        print("\n💡 Совет: загрузите файл с данными data/operations.xlsx")
        return

    input_date = "15.12.2021"

    # 1. Генерация главной страницы
    generate_main_page(input_date, excel_file)

    # 2. Генерация страницы событий
    generate_events_page(input_date, excel_file)

    # 3. Запуск сервисов
    run_services(excel_file)

    # 4. Отчеты
    run_reports(excel_file)

    # 5. Выводим итоговую информацию
    print_summary()


if __name__ == "__main__":
    main()
