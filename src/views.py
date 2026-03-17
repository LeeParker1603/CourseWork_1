import json
import logging
from datetime import datetime, timedelta

import pandas as pd

from src.utils import (
    calculate_card_data,
    calculate_expenses_data,
    calculate_income_data,
    calculate_top_transactions,
    convert_numpy_types,
    filter_transactions_by_date,
    get_currency_rates,
    get_stock_prices,
    load_user_settings,
    read_transactions_from_excel,
)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


def generate_main_page_response(input_date: str, excel_file_path: str) -> str:
    """
    Генерация JSON-ответа для главной страницы
    """
    logger.info(f"Генерация главной страницы для даты: {input_date}")

    # Чтение транзакций
    try:
        df = read_transactions_from_excel(excel_file_path)
    except Exception as e:
        logger.error(f"Ошибка при чтении файла: {e}")
        return json.dumps({"error": f"Ошибка при чтении файла: {str(e)}"}, ensure_ascii=False, indent=2)

    if df.empty:
        return json.dumps({"error": "Не удалось загрузить данные"}, ensure_ascii=False, indent=2)

    # Конвертируем числовые колонки в обычные Python типы
    for col in df.select_dtypes(include=["int64", "int32", "float64"]).columns:
        df[col] = df[col].astype(float)

    # Фильтрация по дате
    try:
        filtered_df = filter_transactions_by_date(df, input_date)
    except Exception as e:
        logger.error(f"Ошибка при фильтрации по дате: {e}")
        filtered_df = df  # используем все данные в случае ошибки

    # Загрузка пользовательских настроек
    try:
        settings = load_user_settings()
    except Exception as e:
        logger.error(f"Ошибка при загрузке настроек: {e}")
        settings = {"user_currencies": [], "user_stocks": []}

    # Получение курсов валют
    try:
        currency_rates = get_currency_rates(settings.get("user_currencies", []))
    except Exception as e:
        logger.error(f"Ошибка при получении курсов валют: {e}")
        currency_rates = []

    # Получение цен акций
    try:
        stock_prices = get_stock_prices(settings.get("user_stocks", []))
    except Exception as e:
        logger.error(f"Ошибка при получении цен акций: {e}")
        stock_prices = []

    # Расчет данных по картам
    try:
        card_data = calculate_card_data(filtered_df)
    except Exception as e:
        logger.error(f"Ошибка при расчете данных по картам: {e}")
        card_data = []

    # Топ-5 транзакций
    try:
        top_transactions = calculate_top_transactions(filtered_df)
    except Exception as e:
        logger.error(f"Ошибка при расчете топ транзакций: {e}")
        top_transactions = []

    # Формирование ответа
    response = {
        "greeting": f"Привет, {get_greeting(input_date)}!",
        "date": input_date,
        "cards": card_data,
        "top_transactions": top_transactions,
        "currency_rates": currency_rates,
        "stock_prices": stock_prices,
    }

    # Конвертируем numpy типы перед сериализацией
    try:
        response_converted = convert_numpy_types(response)
    except Exception as e:
        logger.error(f"Ошибка при конвертации типов: {e}")
        response_converted = response

    logger.info("Главная страница сгенерирована успешно")
    return json.dumps(response_converted, ensure_ascii=False, indent=2)


def get_greeting(date_str: str) -> str:
    """
    Определение приветствия по времени суток
    """
    try:
        # Пробуем распарсить с временем
        if " " in date_str:
            hour = datetime.strptime(date_str, "%d.%m.%Y %H:%M:%S").hour
        else:
            hour = datetime.strptime(date_str, "%d.%m.%Y").hour
    except Exception as e:
        logger.error(f"Ошибка при определении времени: {e}")
        # Если не получается, берем текущий час
        hour = datetime.now().hour

    if 6 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 18:
        return "Добрый день"
    elif 18 <= hour < 23:
        return "Добрый вечер"
    else:
        return "Доброй ночи"


def get_date_range(input_date: str, period: str = "M") -> tuple:
    """
    Определение диапазона дат в зависимости от периода

    Периоды:
    - W: неделя
    - M: месяц (по умолчанию)
    - Y: год
    - ALL: все данные
    """
    date = datetime.strptime(input_date, "%d.%m.%Y")

    if period == "W":
        # Начало недели (понедельник)
        start_date = date - timedelta(days=date.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0)
        end_date = date.replace(hour=23, minute=59, second=59)

    elif period == "M":
        # Начало месяца
        start_date = date.replace(day=1, hour=0, minute=0, second=0)
        end_date = date.replace(hour=23, minute=59, second=59)

    elif period == "Y":
        # Начало года
        start_date = date.replace(month=1, day=1, hour=0, minute=0, second=0)
        end_date = date.replace(hour=23, minute=59, second=59)

    elif period == "ALL":
        # Все данные до указанной даты
        start_date = datetime(1900, 1, 1)  # Очень ранняя дата
        end_date = date.replace(hour=23, minute=59, second=59)

    else:
        # По умолчанию - месяц
        start_date = date.replace(day=1, hour=0, minute=0, second=0)
        end_date = date.replace(hour=23, minute=59, second=59)

    return start_date, end_date


def generate_events_page_response(
    input_date: str, period: str = "M", excel_file_path: str = "data/operations.xls"
) -> str:
    """
    Генерация JSON-ответа для страницы событий
    """
    logger.info(f"Генерация страницы событий для даты: {input_date}, период: {period}")

    # Чтение транзакций с обработкой ошибок
    try:
        df = read_transactions_from_excel(excel_file_path)
    except Exception as e:
        logger.error(f"Ошибка при чтении файла: {e}")
        return json.dumps({"error": f"Ошибка при чтении файла: {str(e)}"}, ensure_ascii=False, indent=2)

    if df.empty:
        return json.dumps({"error": "Не удалось загрузить данные"}, ensure_ascii=False, indent=2)

    # Конвертируем числовые колонки
    for col in df.select_dtypes(include=["int64", "int32", "float64"]).columns:
        df[col] = df[col].astype(float)

    # Определяем диапазон дат
    try:
        start_date, end_date = get_date_range(input_date, period)
        logger.info(f"Диапазон дат: с {start_date} по {end_date}")
    except Exception as e:
        logger.error(f"Ошибка при определении диапазона дат: {e}")
        return json.dumps({"error": f"Ошибка при определении диапазона дат: {str(e)}"}, ensure_ascii=False, indent=2)

    # Фильтрация по диапазону
    try:
        # Убеждаемся, что даты в правильном формате
        if not pd.api.types.is_datetime64_any_dtype(df["Дата операции"]):
            df["Дата операции"] = pd.to_datetime(df["Дата операции"], errors="coerce")

        mask = (df["Дата операции"] >= start_date) & (df["Дата операции"] <= end_date)
        filtered_df = df.loc[mask].copy()
        logger.info(f"Найдено транзакций за период: {len(filtered_df)}")
    except Exception as e:
        logger.error(f"Ошибка при фильтрации по дате: {e}")
        filtered_df = df  # используем все данные в случае ошибки

    # Загрузка пользовательских настроек
    try:
        settings = load_user_settings()
    except Exception as e:
        logger.error(f"Ошибка при загрузке настроек: {e}")
        settings = {"user_currencies": ["USD", "EUR"], "user_stocks": ["AAPL", "GOOGL"]}

    # Получение курсов валют
    try:
        currency_rates = get_currency_rates(settings.get("user_currencies", []))
    except Exception as e:
        logger.error(f"Ошибка при получении курсов валют: {e}")
        currency_rates = []

    # Получение цен акций S&P 500
    try:
        stock_prices = get_stock_prices(settings.get("user_stocks", []))
    except Exception as e:
        logger.error(f"Ошибка при получении цен акций: {e}")
        stock_prices = []

    # Расчет расходов и поступлений
    try:
        expenses_data = calculate_expenses_data(filtered_df)
        income_data = calculate_income_data(filtered_df)
    except Exception as e:
        logger.error(f"Ошибка при расчете данных: {e}")
        expenses_data = {"total_amount": 0, "main": [], "transfers_and_cash": []}
        income_data = {"total_amount": 0, "main": []}

    # Формирование ответа
    response = {
        "expenses": expenses_data,
        "income": income_data,
        "currency_rates": currency_rates,
        "stock_prices": stock_prices,
    }

    # Конвертируем numpy типы
    try:
        response_converted = convert_numpy_types(response)
    except Exception as e:
        logger.error(f"Ошибка при конвертации типов: {e}")
        response_converted = response

    logger.info("Страница событий сгенерирована успешно")
    return json.dumps(response_converted, ensure_ascii=False, indent=2)
