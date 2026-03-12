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


def categorize_transaction(row) -> str:
    """
    Определение категории для группировки
    """
    category = str(row.get('Категория', '')).strip()
    description = str(row.get('Описание', '')).lower()

    # Определяем переводы и наличные
    if 'перевод' in description.lower() or category == 'Переводы':
        return 'Переводы'
    elif 'наличные' in description.lower() or category == 'Наличные':
        return 'Наличные'
    elif category and category != 'nan':
        return category
    else:
        return 'Прочее'


def calculate_expenses_data(df: pd.DataFrame) -> dict:
    """
    Расчет данных по расходам
    """
    # Только расходы (отрицательные суммы)
    expenses_df = df[df['Сумма операции'] < 0].copy()

    if expenses_df.empty:
        return {
            "total_amount": 0,
            "main": [],
            "transfers_and_cash": []
        }

    # Общая сумма расходов
    total_expenses = abs(expenses_df['Сумма операции'].sum())

    # Группировка по категориям
    expenses_df['category_group'] = expenses_df.apply(categorize_transaction,
                                                      axis=1)

    # Расходы по категориям
    category_expenses = expenses_df.groupby('category_group')[
        'Сумма операции'].sum().abs()
    category_expenses = category_expenses.sort_values(ascending=False)

    # Основные категории (топ-7)
    main_categories = []
    other_sum = 0

    for i, (category, amount) in enumerate(category_expenses.items()):
        if category in ['Переводы', 'Наличные']:
            continue  # Эти категории пойдут в отдельный раздел
        elif i < 7:  # Первые 7 категорий
            main_categories.append({
                "category": category,
                "amount": int(round(amount))
            })
        else:
            other_sum += amount

    # Добавляем "Остальное", если есть
    if other_sum > 0:
        main_categories.append({
            "category": "Остальное",
            "amount": int(round(other_sum))
        })

    # Переводы и наличные
    transfers_and_cash = []
    for category in ['Наличные', 'Переводы']:
        if category in category_expenses.index:
            transfers_and_cash.append({
                "category": category,
                "amount": int(round(category_expenses[category]))
            })

    # Сортируем переводы и наличные по убыванию
    transfers_and_cash.sort(key=lambda x: x['amount'], reverse=True)

    return {
        "total_amount": int(round(total_expenses)),
        "main": main_categories,
        "transfers_and_cash": transfers_and_cash
    }


def calculate_income_data(df: pd.DataFrame) -> dict:
    """
    Расчет данных по поступлениям
    """
    # Только поступления (положительные суммы)
    income_df = df[df['Сумма операции'] > 0].copy()

    if income_df.empty:
        return {
            "total_amount": 0,
            "main": []
        }

    # Общая сумма поступлений
    total_income = income_df['Сумма операции'].sum()

    # Группировка по категориям
    income_df['category_group'] = income_df.apply(categorize_transaction,
                                                  axis=1)

    # Поступления по категориям
    category_income = income_df.groupby('category_group')[
        'Сумма операции'].sum()
    category_income = category_income.sort_values(ascending=False)

    # Основные категории поступлений
    main_categories = []
    for category, amount in category_income.items():
        main_categories.append({
            "category": category,
            "amount": int(round(amount))
        })

    return {
        "total_amount": int(round(total_income)),
        "main": main_categories
    }
