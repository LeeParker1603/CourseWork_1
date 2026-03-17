# import logging
import json
import os
import time
from datetime import datetime
from functools import reduce
from typing import Any, Dict, List

import pandas as pd
import requests
from dotenv import load_dotenv
from requests.exceptions import RequestException

load_dotenv()

# # Настройка логирования
# logger = logging.getLogger(__name__)
#
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger(__name__)


def read_transactions_from_excel(file_path: str) -> pd.DataFrame:
    """
    Чтение транзакций из Excel-файла
    """
    try:
        df = pd.read_excel(file_path)
        # Преобразуем даты в правильный формат
        if "Дата операции" in df.columns:
            df["Дата операции"] = pd.to_datetime(
                df["Дата операции"], format="%d.%m.%Y %H:%M:%S", dayfirst=True, errors="coerce"
            )

        if "Дата платежа" in df.columns:
            df["Дата платежа"] = pd.to_datetime(df["Дата платежа"], format="%d.%m.%Y", dayfirst=True, errors="coerce")
        return df
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")
        return pd.DataFrame()


def filter_transactions_by_date(df: pd.DataFrame, input_date: str) -> pd.DataFrame:
    """
    Фильтрация транзакций с начала месяца по указанную дату
    """
    try:
        input_datetime = datetime.strptime(input_date, "%d.%m.%Y")

        # Начало месяца
        start_of_month = input_datetime.replace(day=1, hour=0, minute=0, second=0)

        # ПРОВЕРЯЕМ ТИП ДАННЫХ В КОЛОНКЕ 'Дата операции'
        if "Дата операции" not in df.columns:
            print("Колонка 'Дата операции' не найдена")
            return df

        # Если колонка строкового типа, преобразуем в datetime
        if df["Дата операции"].dtype == "object" or pd.api.types.is_string_dtype(df["Дата операции"]):
            print("Преобразуем строковые даты в datetime")
            df = df.copy()
            df["Дата операции"] = pd.to_datetime(df["Дата операции"], errors="coerce")

        # Фильтруем по дате
        mask = (df["Дата операции"] >= start_of_month) & (df["Дата операции"] <= input_datetime)
        filtered_df = df.loc[mask].copy()

        print(f"После фильтрации по дате {input_date}: {len(filtered_df)} транзакций")
        return filtered_df

    except Exception as e:
        print(f"Ошибка при фильтрации по дате: {e}")
        return df


def load_user_settings() -> dict:
    """
    Загрузка пользовательских настроек
    """
    # Ищем файл настроек в разных местах
    possible_paths = [
        "user_settings.json",
        "../user_settings.json",
        os.path.join(os.path.dirname(__file__), "..", "user_settings.json"),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    return settings
            except Exception:
                pass  # Игнорируем ошибки, переходим к следующему пути

    # Настройки по умолчанию
    return {"user_currencies": [], "user_stocks": []}


def get_currency_rates(currencies: list) -> list:
    """
    Получение курсов валют через API.
    Используем бесплатное API - api.apilayer.com
    """
    currency_rates = []

    api_key = os.getenv("API_KEY_APILAYER")

    base_url = "https://api.apilayer.com/exchangerates_data/latest"

    try:
        # Объединяем валюты в строку через запятую
        symbols = ",".join(currencies)

        # Параметры запроса
        params = {"base": "RUB", "symbols": symbols}

        # Заголовки с API ключом
        headers = {"apikey": api_key}

        # Выполняем GET запрос с параметрами
        response = requests.get(base_url, params=params, headers=headers, timeout=5)

        if response.status_code == 200:
            data = response.json()

            # Проверяем структуру ответа
            if "rates" in data:
                # Проходим по всем запрошенным валютам
                for currency in currencies:
                    if currency in data["rates"]:
                        # API возвращает RUB → currency, нам нужно currency → RUB
                        currency_to_rub = 1 / data["rates"][currency]

                        currency_rates.append(
                            {
                                "currency": currency,
                                "rate": round(currency_to_rub, 2),
                            }
                        )
                    else:
                        currency_rates.append(
                            {"currency": currency, "rate": None, "error": "Валюта не найдена в ответе"}
                        )
            else:
                for currency in currencies:
                    currency_rates.append({"currency": currency, "rate": None, "error": "Нет данных о курсах"})
        else:
            for currency in currencies:
                currency_rates.append(
                    {"currency": currency, "rate": None, "error": f"Ошибка API: {response.status_code}"}
                )

    except RequestException as e:
        for currency in currencies:
            currency_rates.append({"currency": currency, "rate": None, "error": f"Ошибка подключения: {str(e)}"})

    except Exception as e:
        for currency in currencies:
            currency_rates.append({"currency": currency, "rate": None, "error": f"Неизвестная ошибка: {str(e)}"})

    return currency_rates


def get_usd_to_rub_rate() -> float:
    """
    Получение текущего курса USD к RUB с кэшированием на 1 час.
    """
    try:
        # Запрашиваем курс доллара в Центробанке РФ
        url = "https://www.cbr-xml-daily.ru/latest.js"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            usd_rate = data.get("rates", {}).get("USD")
            if usd_rate:
                return round(1 / float(usd_rate), 2)

    except Exception as e:
        print(f"⚠️ Ошибка получения курса USD/RUB: {e}")
        return 1.0


def get_stock_prices(symbols: list) -> list:
    """
    Получение цен акций через Alpha Vantage API (GLOBAL_QUOTE).
    Цены конвертируются в рубли.

    Args:
        symbols: список тикеров (из файла user_settings.json)

    Returns:
        list: список словарей с информацией об акциях в рублях
    """

    stock_prices = []

    # Получаем API ключ
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

    # Получаем курс USD/RUB для конвертации
    usd_to_rub = get_usd_to_rub_rate()

    print(f"📡 Начинаю получение данных для {len(symbols)} акций...")

    # Базовый URL Alpha Vantage API
    base_url = "https://www.alphavantage.co/query"

    for i, symbol in enumerate(symbols):
        try:
            params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": api_key}

            response = requests.get(base_url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Проверяем наличие данных
                if "Global Quote" in data and data["Global Quote"]:
                    quote = data["Global Quote"]

                    # Извлекаем цену в USD
                    price_usd_str = quote.get("05. price", "0")
                    try:
                        price_usd = float(price_usd_str)
                        price_rub = price_usd * usd_to_rub

                        stock_prices.append({"stock": symbol, "price": round(price_rub, 2)})
                        print(f"      ✅ {symbol}: ${price_usd:.2f} = {price_rub:.2f} ₽")
                    except ValueError:
                        stock_prices.append(
                            {"stock": symbol, "price": None, "error": f"Неверный формат цены: {price_usd_str}"}
                        )
                else:
                    # Проверяем на лимит запросов
                    if "Note" in data:
                        error_msg = data["Note"]
                        stock_prices.append({"stock": symbol, "price": None, "error": "Превышен лимит запросов к API"})
                    else:
                        stock_prices.append({"stock": symbol, "price": None, "error": "Нет данных по тикеру"})
            else:
                stock_prices.append({"stock": symbol, "price": None, "error": f"Ошибка API: {response.status_code}"})

                # Задержка между запросами, но не после последнего
            if i < len(symbols) - 1:  # не ждем после последнего символа
                time.sleep(12)  # 60/5 = 12 секунд

        except RequestException as e:
            stock_prices.append({"stock": symbol, "price": None, "error": f"Ошибка подключения: {str(e)}"})
        except Exception as e:
            stock_prices.append({"stock": symbol, "price": None, "error": f"Неизвестная ошибка: {str(e)}"})

    return stock_prices


def calculate_card_data(df: pd.DataFrame) -> list:
    """
    Расчет данных по картам
    """
    if df.empty:
        return []

    # Группируем по последним 4 цифрам карты
    card_data = []

    # Получаем уникальные карты
    cards = df["Номер карты"].dropna().unique()

    for card in cards:
        card_transactions = df[df["Номер карты"] == card]

        # Сумма расходов (отрицательные транзакции)
        expenses = card_transactions[card_transactions["Сумма операции"] < 0]["Сумма операции"].sum()

        # Кешбэк (если есть столбец)
        cashback = 0
        if "Кешбэк" in card_transactions.columns:
            cashback = card_transactions["Кешбэк"].sum()

        # Получаем последние 4 цифры карты (простой способ)
        card_str = str(card)
        # Оставляем только цифры
        digits_only = "".join([c for c in card_str if c.isdigit()])

        # Берем последние 4 цифры или всю строку, если меньше
        if len(digits_only) >= 4:
            last_digits = digits_only[-4:]
        else:
            last_digits = digits_only if digits_only else card_str[-4:] if len(card_str) >= 4 else card_str

        card_data.append(
            {"last_digits": last_digits, "total_spent": abs(round(expenses, 2)), "cashback": round(cashback, 2)}
        )

    return card_data


def calculate_top_transactions(df: pd.DataFrame) -> list:
    """
    Получение топ-5 транзакций по сумме
    """
    if df.empty:
        return []

    # Берем только расходные операции (отрицательные)
    expenses = df[df["Сумма операции"] < 0].copy()
    expenses["abs_sum"] = abs(expenses["Сумма операции"])

    # Сортируем и берем топ-5
    top_5 = expenses.nlargest(5, "abs_sum")

    result = []
    for _, row in top_5.iterrows():
        result.append(
            {
                "date": row["Дата операции"].strftime("%d.%m.%Y"),
                "amount": abs(round(row["Сумма операции"], 2)),
                "category": row["Категория"] if pd.notna(row["Категория"]) else "Не указано",
                "description": row["Описание"][:50] + "..." if len(str(row["Описание"])) > 50 else row["Описание"],
            }
        )

    return result


def categorize_transaction(row) -> str:
    """
    Определение категории для группировки
    """
    category = str(row.get("Категория", "")).strip()
    description = str(row.get("Описание", "")).lower()

    # Определяем переводы и наличные
    if "перевод" in description.lower() or category == "Переводы":
        return "Переводы"
    elif "наличные" in description.lower() or category == "Наличные":
        return "Наличные"
    elif category and category != "nan":
        return category
    else:
        return "Прочее"


def calculate_expenses_data(df: pd.DataFrame) -> dict:
    """
    Расчет данных по расходам
    """
    # Только расходы (отрицательные суммы)
    expenses_df = df[df["Сумма операции"] < 0].copy()

    if expenses_df.empty:
        return {"total_amount": 0, "main": [], "transfers_and_cash": []}

    # Общая сумма расходов
    total_expenses = abs(expenses_df["Сумма операции"].sum())

    # Группировка по категориям
    expenses_df["category_group"] = expenses_df.apply(categorize_transaction, axis=1)

    # Расходы по категориям
    category_expenses = expenses_df.groupby("category_group")["Сумма операции"].sum().abs()
    category_expenses = category_expenses.sort_values(ascending=False)

    # Основные категории (топ-7)
    main_categories = []
    other_sum = 0

    for i, (category, amount) in enumerate(category_expenses.items()):
        if category in ["Переводы", "Наличные"]:
            continue  # Эти категории пойдут в отдельный раздел
        elif i < 7:  # Первые 7 категорий
            main_categories.append({"category": category, "amount": int(round(amount))})
        else:
            other_sum += amount

    # Добавляем "Остальное", если есть
    if other_sum > 0:
        main_categories.append({"category": "Остальное", "amount": int(round(other_sum))})

    # Переводы и наличные
    transfers_and_cash = []
    for category in ["Наличные", "Переводы"]:
        if category in category_expenses.index:
            transfers_and_cash.append({"category": category, "amount": int(round(category_expenses[category]))})

    # Сортируем переводы и наличные по убыванию
    transfers_and_cash.sort(key=lambda x: x["amount"], reverse=True)

    return {
        "total_amount": int(round(total_expenses)),
        "main": main_categories,
        "transfers_and_cash": transfers_and_cash,
    }


def calculate_income_data(df: pd.DataFrame) -> dict:
    """
    Расчет данных по поступлениям
    """
    # Только поступления (положительные суммы)
    income_df = df[df["Сумма операции"] > 0].copy()

    if income_df.empty:
        return {"total_amount": 0, "main": []}

    # Общая сумма поступлений
    total_income = income_df["Сумма операции"].sum()

    # Группировка по категориям
    income_df["category_group"] = income_df.apply(categorize_transaction, axis=1)

    # Поступления по категориям
    category_income = income_df.groupby("category_group")["Сумма операции"].sum()
    category_income = category_income.sort_values(ascending=False)

    # Основные категории поступлений
    main_categories = []
    for category, amount in category_income.items():
        main_categories.append({"category": category, "amount": int(round(amount))})

    return {"total_amount": int(round(total_income)), "main": main_categories}


def convert_numpy_types(obj):
    """
    Конвертирует numpy типы в стандартные Python типы для JSON сериализации
    """
    import numpy as np

    if obj is None:
        return None
    elif isinstance(obj, dict):
        # Рекурсивно обрабатываем словарь
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        # Рекурсивно обрабатываем список/кортеж/множество
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return convert_numpy_types(obj.tolist())  # рекурсивно обрабатываем список
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif pd.isna(obj):
        return None
    elif hasattr(obj, "item"):  # для других numpy типов
        return obj.item()
    else:
        # Если это уже стандартный тип, возвращаем как есть
        return obj


def calculate_cashback_by_category(transactions: List[Dict[str, Any]], rate: float = 0.01) -> Dict[str, float]:
    """
    Вспомогательная функция для расчета кешбэка по категориям
    """

    # Группировка по категориям с использованием reduce
    def group_by_category(acc, transaction):
        category = transaction.get("Категория", "Не указано")
        if pd.isna(category) or not category:
            category = "Не указано"

        try:
            amount = abs(float(transaction.get("Сумма операции", 0)))
            cashback = amount * rate
            # Округляем до двух знаков после запятой
            acc[category] = acc.get(category, 0) + cashback
        except (ValueError, TypeError):
            pass  # Пропускаем транзакции с некорректной суммой

        return acc

    cashback_by_category = reduce(group_by_category, transactions, {})

    # Округляем все значения до двух знаков после запятой
    cashback_by_category = {category: round(amount) for category, amount in cashback_by_category.items()}

    # Сортируем по убыванию
    return dict(sorted(cashback_by_category.items(), key=lambda x: x[1], reverse=True))
