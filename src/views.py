import json
from datetime import datetime
from typing import Dict, Any

from src.utils import (
    read_transactions_from_excel,
    filter_transactions_by_date,
    load_user_settings,
    get_currency_rates,
    get_stock_prices,
    calculate_card_data,
    calculate_top_transactions
)


def generate_main_page_response(input_date: str,
                                excel_file_path: str) -> str:
    """
    Генерация JSON-ответа для главной страницы
    """
    # Чтение транзакций
    df = read_transactions_from_excel(excel_file_path)

    if df.empty:
        return json.dumps({"error": "Не удалось загрузить данные"},
                          ensure_ascii=False, indent=2)

    # Фильтрация по дате
    filtered_df = filter_transactions_by_date(df, input_date)

    # Загрузка пользовательских настроек
    settings = load_user_settings()

    # Получение курсов валют
    currency_rates = get_currency_rates(settings.get('user_currencies', []))

    # Получение цен акций
    stock_prices = get_stock_prices(settings.get('user_stocks', []))

    # Расчет данных по картам
    card_data = calculate_card_data(filtered_df)

    # Топ-5 транзакций
    top_transactions = calculate_top_transactions(filtered_df)

    # Формирование ответа
    response = {
        "greeting": f"Привет, {get_greeting(input_date)}!",
        "date": input_date,
        "cards": card_data,
        "top_transactions": top_transactions,
        "currency_rates": currency_rates,
        "stock_prices": stock_prices
    }

    return json.dumps(response, ensure_ascii=False, indent=2)


def get_greeting(date_str: str) -> str:
    """
    Определение приветствия по времени суток
    """
    hour = datetime.strptime(date_str, '%d.%m.%Y').hour

    if 6 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 18:
        return "Добрый день"
    elif 18 <= hour < 23:
        return "Добрый вечер"
    else:
        return "Доброй ночи"