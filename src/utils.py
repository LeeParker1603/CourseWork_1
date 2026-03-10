import pandas as pd
from datetime import datetime
from typing import Optional, Tuple
import json
import requests
from requests.exceptions import RequestException


def read_transactions_from_excel(file_path: str) -> pd.DataFrame:
    """
    Чтение транзакций из Excel-файла
    """
    try:
        df = pd.read_excel(file_path)
        # Преобразуем даты в правильный формат
        df['Дата операции'] = pd.to_datetime(df['Дата операции'],
                                             format='%d.%m.%Y %H:%M:%S',
                                             dayfirst=True)
        df['Дата платежа'] = pd.to_datetime(df['Дата платежа'],
                                            format='%d.%m.%Y', dayfirst=True)
        return df
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")
        return pd.DataFrame()


def filter_transactions_by_date(df: pd.DataFrame,
                                input_date: str) -> pd.DataFrame:
    """
    Фильтрация транзакций с начала месяца по указанную дату
    """
    input_datetime = datetime.strptime(input_date, '%d.%m.%Y')

    # Начало месяца
    start_of_month = input_datetime.replace(day=1, hour=0, minute=0, second=0)

    # Фильтруем по дате операции
    mask = (df['Дата операции'] >= start_of_month) & (
                df['Дата операции'] <= input_datetime)
    return df.loc[mask].copy()


def load_user_settings() -> dict:
    """
    Загрузка пользовательских настроек
    """
    try:
        with open('user_settings.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"user_currencies": ["USD", "EUR"], "user_stocks": []}


def get_currency_rates(currencies: list) -> list:
    """
    Получение курсов валют через API
    Используем бесплатное API exchangerate-api.com
    """
    currency_rates = []

    for currency in currencies:
        try:
            # Бесплатное API для демонстрации
            response = requests.get(
                f"https://api.exchangerate-api.com/v4/latest/RUB",
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                if currency in data.get('rates', {}):
                    rate = 1 / data['rates'][
                        currency]  # Конвертируем в RUB за 1 единицу валюты
                    currency_rates.append({
                        "currency": currency,
                        "rate": round(rate, 2)
                    })
                else:
                    currency_rates.append({
                        "currency": currency,
                        "rate": None,
                        "error": "Валюта не найдена"
                    })
            else:
                currency_rates.append({
                    "currency": currency,
                    "rate": None,
                    "error": "Ошибка API"
                })

        except RequestException as e:
            currency_rates.append({
                "currency": currency,
                "rate": None,
                "error": f"Ошибка подключения: {str(e)}"
            })

    return currency_rates


def get_stock_prices(stocks: list) -> list:
    """
    Получение цен акций через API
    Используем бесплатное API yahoofinance (альтернатива - mock данные для демо)
    """
    stock_prices = []

    # Для демонстрации используем заглушку, так как многие биржевые API платные
    mock_prices = {
        "AAPL": 175.50,
        "AMZN": 145.30,
        "GOOGL": 138.20,
        "MSFT": 380.40,
        "TSLA": 240.15
    }

    for stock in stocks:
        if stock in mock_prices:
            stock_prices.append({
                "stock": stock,
                "price": mock_prices[stock]
            })
        else:
            stock_prices.append({
                "stock": stock,
                "price": None,
                "error": "Данные не доступны"
            })

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
    cards = df['Номер карты'].dropna().unique()

    for card in cards:
        card_transactions = df[df['Номер карты'] == card]

        # Сумма расходов (отрицательные транзакции)
        expenses = card_transactions[card_transactions['Сумма операции'] < 0][
            'Сумма операции'].sum()

        # Кешбэк (если есть столбец)
        cashback = 0
        if 'Кешбэк' in card_transactions.columns:
            cashback = card_transactions['Кешбэк'].sum()

        # Получаем последние 4 цифры карты (простой способ)
        card_str = str(card)
        # Оставляем только цифры
        digits_only = ''.join([c for c in card_str if c.isdigit()])

        # Берем последние 4 цифры или всю строку, если меньше
        if len(digits_only) >= 4:
            last_digits = digits_only[-4:]
        else:
            last_digits = digits_only if digits_only else card_str[
                                                          -4:] if len(
                card_str) >= 4 else card_str

        card_data.append({
            "last_digits": last_digits,
            "total_spent": abs(round(expenses, 2)),
            "cashback": round(cashback, 2)
        })

    return card_data


def calculate_top_transactions(df: pd.DataFrame) -> list:
    """
    Получение топ-5 транзакций по сумме
    """
    if df.empty:
        return []

    # Берем только расходные операции (отрицательные)
    expenses = df[df['Сумма операции'] < 0].copy()
    expenses['abs_sum'] = abs(expenses['Сумма операции'])

    # Сортируем и берем топ-5
    top_5 = expenses.nlargest(5, 'abs_sum')

    result = []
    for _, row in top_5.iterrows():
        result.append({
            "date": row['Дата операции'].strftime('%d.%m.%Y'),
            "amount": abs(round(row['Сумма операции'], 2)),
            "category": row['Категория'] if pd.notna(
                row['Категория']) else "Не указано",
            "description": row['Описание'][:50] + "..." if len(
                str(row['Описание'])) > 50 else row['Описание']
        })

    return result