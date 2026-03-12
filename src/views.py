import json
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

from src.utils import (
    read_transactions_from_excel,
    filter_transactions_by_date,
    load_user_settings,
    get_currency_rates,
    get_stock_prices,
    calculate_card_data,
    calculate_top_transactions, calculate_income_data, calculate_expenses_data
)


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_main_page_response(input_date: str,
                                excel_file_path: str) -> str:
    """
    Генерация JSON-ответа для главной страницы
    """
    logger.info(f"Генерация главной страницы для даты: {input_date}")

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

    logger.info(f"Главная страница сгенерирована успешно")
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


def get_date_range(input_date: str, period: str = 'M') -> tuple:
    """
    Определение диапазона дат в зависимости от периода

    Периоды:
    - W: неделя
    - M: месяц (по умолчанию)
    - Y: год
    - ALL: все данные
    """
    date = datetime.strptime(input_date, '%d.%m.%Y')

    if period == 'W':
        # Начало недели (понедельник)
        start_date = date - timedelta(days=date.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0)
        end_date = date.replace(hour=23, minute=59, second=59)

    elif period == 'M':
        # Начало месяца
        start_date = date.replace(day=1, hour=0, minute=0, second=0)
        end_date = date.replace(hour=23, minute=59, second=59)

    elif period == 'Y':
        # Начало года
        start_date = date.replace(month=1, day=1, hour=0, minute=0, second=0)
        end_date = date.replace(hour=23, minute=59, second=59)

    elif period == 'ALL':
        # Все данные до указанной даты
        start_date = datetime(1900, 1, 1)  # Очень ранняя дата
        end_date = date.replace(hour=23, minute=59, second=59)

    else:
        # По умолчанию - месяц
        start_date = date.replace(day=1, hour=0, minute=0, second=0)
        end_date = date.replace(hour=23, minute=59, second=59)

    return start_date, end_date


def generate_events_page_response(
        input_date: str,
        period: str,
        excel_file_path: str
) -> str:
    """
    Генерация JSON-ответа для страницы событий

    Параметры:
    - input_date: дата в формате 'DD.MM.YYYY'
    - period: период (W - неделя, M - месяц, Y - год, ALL - все данные)
    """
    logger.info(
        f"Генерация страницы событий для даты: {input_date}, период: {period}")

    # Чтение транзакций
    df = read_transactions_from_excel(excel_file_path)

    if df.empty:
        return json.dumps({"error": "Не удалось загрузить данные"},
                          ensure_ascii=False, indent=2)

    # Определяем диапазон дат
    start_date, end_date = get_date_range(input_date, period)
    logger.info(f"Диапазон дат: с {start_date} по {end_date}")

    # Фильтрация по диапазону
    mask = (df['Дата операции'] >= start_date) & (
                df['Дата операции'] <= end_date)
    filtered_df = df.loc[mask].copy()
    logger.info(f"Найдено транзакций за период: {len(filtered_df)}")

    # Загрузка пользовательских настроек
    settings = load_user_settings()

    # Получение курсов валют
    currency_rates = get_currency_rates(settings.get('user_currencies', []))

    # Получение цен акций S&P 500
    stock_prices = get_stock_prices(settings.get('user_stocks', []))

    # Расчет расходов и поступлений
    expenses_data = calculate_expenses_data(filtered_df)
    income_data = calculate_income_data(filtered_df)

    # Формирование ответа
    response = {
        "expenses": expenses_data,
        "income": income_data,
        "currency_rates": currency_rates,
        "stock_prices": stock_prices
    }

    logger.info(f"Страница событий сгенерирована успешно")
    return json.dumps(response, ensure_ascii=False, indent=2)
