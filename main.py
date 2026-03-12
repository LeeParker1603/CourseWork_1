import json
import os
import logging
import sys

# Добавляем корневую папку в путь поиска модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.views import (generate_main_page_response,
                       generate_events_page_response)

from src.services import (
    analyze_cashback_categories,
    investment_bank,
    simple_search,
    search_by_phone,
    search_transfers_to_individuals
)
from src.utils import read_transactions_from_excel

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """
    Основная функция для демонстрации работы
    """

    input_date = "15.12.2021"
    excel_file = "data/operations.xlsx"
    logger.info(
        f"Запуск программы для: {input_date}, по файлу: {excel_file}")

    print("\n" + "=" * 60)
    print("1️⃣ ГЛАВНАЯ СТРАНИЦА")
    print("=" * 60)

    # Генерация ответа для главной страницы
    response_main = generate_main_page_response(input_date, excel_file)

    # Вывод результата
    print("=" * 50)
    print("JSON-ответ для главной страницы:")
    print("=" * 50)
    #print(response_main)

    # Сохраняем результат в файл для проверки
    with open("src/response.json", "w", encoding="utf-8") as f:
        f.write(response_main)

    print("\nРезультат также сохранен в файл response.json")

    print("\n" + "=" * 60)
    print("2️⃣ СТРАНИЦА СОБЫТИЙ")
    print("=" * 60)

    # Генерация ответа для страницы событий (период M - месяц)
    response_events = generate_events_page_response(input_date, 'M', excel_file)

    print("📊 JSON-ответ для страницы событий (период M - месяц):")
    #print(response_events)

    # Сохраняем результат
    with open("src/response_events.json", "w", encoding="utf-8") as f:
        f.write(response_events)

    print("\n✅ Результат сохранен в файл: src/response_events.json")

    print("\n" + "=" * 60)
    print("🎉 ГЕНЕРАЦИЯ ЗАВЕРШЕНА")
    print("=" * 60)

    # Запускаем сервисы

    print("\n" + "★" * 70)
    print("🛠️  ЗАПУСК СЕРВИСОВ")
    print("★" * 70)

    # Загружаем транзакции
    transactions_df = read_transactions_from_excel(excel_file)

    if transactions_df.empty:
        print("❌ Не удалось загрузить транзакции для сервисов")
        return

    # Преобразуем DataFrame в список словарей
    transactions = transactions_df.to_dict('records')

    # Сервис 1: Анализ кешбэка
    print("\n" + "-" * 70)
    print("📊 СЕРВИС 1: Анализ выгодных категорий кешбэка")
    print("-" * 70)
    cashback_result = analyze_cashback_categories(transactions, 2021, 12)
    print(cashback_result)

    # Сохраняем результат
    with open("service_cashback.json", "w", encoding="utf-8") as f:
        f.write(cashback_result)
    print("✅ Результат сохранен в service_cashback.json")

    # Сервис 2: Инвесткопилка
    print("\n" + "-" * 70)
    print("💰 СЕРВИС 2: Инвесткопилка (лимит 50 ₽)")
    print("-" * 70)
    investment_result = investment_bank('2021-12', transactions, 50)
    print(f"Сумма в Инвесткопилке: {investment_result} ₽")

    # Сохраняем результат
    with open("service_investment.txt", "w", encoding="utf-8") as f:
        f.write(f"Инвесткопилка за 2021-12: {investment_result} ₽")
    print("✅ Результат сохранен в service_investment.txt")

    # Сервис 3: Простой поиск
    print("\n" + "-" * 70)
    print("🔍 СЕРВИС 3: Простой поиск")
    print("-" * 70)

    search_terms = ['Перевод', 'Супермаркет', 'Ресторан']
    for term in search_terms:
        print(f"\n   Поиск по строке: '{term}'")
        search_result = simple_search(transactions, term)
        print(f"   Найдено транзакций: {len(json.loads(search_result))}")

        # Сохраняем результат
        with open(f"service_search_{term}.json", "w", encoding="utf-8") as f:
            f.write(search_result)

    # Сервис 4: Поиск по телефону
    print("\n" + "-" * 70)
    print("📱 СЕРВИС 4: Поиск транзакций с номерами телефонов")
    print("-" * 70)
    phone_result = search_by_phone(transactions)
    print(phone_result)

    # Сохраняем результат
    with open("service_phone_search.json", "w", encoding="utf-8") as f:
        f.write(phone_result)
    print("✅ Результат сохранен в service_phone_search.json")

    # Сервис 5: Поиск переводов физлицам
    print("\n" + "-" * 70)
    print("👤 СЕРВИС 5: Поиск переводов физическим лицам")
    print("-" * 70)
    transfers_result = search_transfers_to_individuals(transactions)
    print(transfers_result)

    # Сохраняем результат
    with open("service_transfers.json", "w", encoding="utf-8") as f:
        f.write(transfers_result)
    print("✅ Результат сохранен в service_transfers.json")

    print("\n" + "✅" * 35)
    print("🎉 ВСЕ СЕРВИСЫ УСПЕШНО ВЫПОЛНЕНЫ!")
    print("✅" * 35)




if __name__ == "__main__":
    main()
