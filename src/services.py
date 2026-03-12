import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Callable, Union
from functools import reduce
import pandas as pd
from collections import defaultdict

# Настройка логирования
logger = logging.getLogger(__name__)


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (функциональный стиль)
# ============================================================================

def filter_by_month_year(month: str, year: int) -> Callable:
    """
    Функция для фильтрации транзакций по месяцу и году

    Пример: filter_by_month_year('12', 2021)(transaction)
    """

    def filter_func(transaction: Dict[str, Any]) -> bool:
        try:
            date_str = transaction.get('Дата операции', '')
            if pd.isna(date_str):
                return False

            # Пробуем разные форматы даты
            if isinstance(date_str, str):
                if ' ' in date_str:
                    date_obj = datetime.strptime(date_str, '%d.%m.%Y %H:%M:%S')
                else:
                    date_obj = datetime.strptime(date_str, '%d.%m.%Y')
            else:
                date_obj = date_str

            return date_obj.month == int(month) and date_obj.year == year
        except (ValueError, TypeError) as e:
            logger.warning(f"Ошибка при парсинге даты {date_str}: {e}")
            return False

    return filter_func


def filter_by_search_string(search_string: str) -> Callable:
    """
    Функция для фильтрации по поисковой строке
    """
    search_lower = search_string.lower()

    def filter_func(transaction: Dict[str, Any]) -> bool:
        description = str(transaction.get('Описание', '')).lower()
        category = str(transaction.get('Категория', '')).lower()
        return search_lower in description or search_lower in category

    return filter_func


def filter_by_regex(pattern: str) -> Callable:
    """
    Функция для фильтрации по регулярному выражению
    """
    compiled = re.compile(pattern, re.IGNORECASE)

    def filter_func(transaction: Dict[str, Any]) -> bool:
        description = str(transaction.get('Описание', ''))
        return bool(compiled.search(description))

    return filter_func


def filter_by_category(categories: List[str]) -> Callable:
    """
    Каррированная функция для фильтрации по категориям
    """
    categories_lower = [c.lower() for c in categories]

    def filter_func(transaction: Dict[str, Any]) -> bool:
        category = str(transaction.get('Категория', '')).lower()
        return category in categories_lower

    return filter_func


def map_to_cashback(rate: float = 0.01) -> Callable:
    """
    Функция для маппинга транзакции в сумму кешбэка
    """

    def map_func(transaction: Dict[str, Any]) -> float:
        amount = abs(float(transaction.get('Сумма операции', 0)))
        return amount * rate

    return map_func


def reduce_sum(acc: float, value: float) -> float:
    """Функция свёртки для суммирования"""
    return acc + value


def compose(*functions: Callable) -> Callable:
    """
    Композиция функций: применяет функции справа налево
    """

    def compose_func(x):
        result = x
        for f in reversed(functions):
            result = f(result)
        return result

    return compose_func


def pipe(data: Any, *functions: Callable) -> Any:
    """
    Конвейер функций: последовательно применяет функции к данным
    """
    result = data
    for func in functions:
        result = func(result)
    return result


# ============================================================================
# ОСНОВНЫЕ ФУНКЦИИ СЕРВИСОВ
# ============================================================================

def analyze_cashback_categories(transactions: List[Dict[str, Any]], year: int,
                                month: int) -> str:
    """
    Сервис 1: Анализ выгодных категорий повышенного кешбэка

    Анализирует, сколько кешбэка можно получить в каждой категории
    """
    logger.info(f"Анализ кешбэка за {month}.{year}")

    # Функциональный конвейер обработки
    result = pipe(
        transactions,
        lambda data: filter(filter_by_month_year(str(month), year), data),
        # Фильтр по дате
        list,
        lambda data: filter(lambda t: float(t.get('Сумма операции', 0)) < 0,
                            data),  # Только расходы
        list,
        lambda data: calculate_cashback_by_category(data)
        # Расчет кешбэка по категориям
    )

    # Преобразуем в JSON
    json_result = json.dumps(result, ensure_ascii=False, indent=2)
    logger.info(f"Анализ завершен. Найдено категорий: {len(result)}")

    return json_result


def calculate_cashback_by_category(transactions: List[Dict[str, Any]],
                                     rate: float = 0.01) -> Dict[str, float]:
    """
    Вспомогательная функция для расчета кешбэка по категориям
    """

    # Группировка по категориям с использованием reduce
    def group_by_category(acc, transaction):
        category = transaction.get('Категория', 'Не указано')
        if pd.isna(category) or not category:
            category = 'Не указано'

        amount = abs(float(transaction.get('Сумма операции', 0)))
        cashback = amount * rate

        acc[category] = acc.get(category, 0) + cashback
        return acc

    cashback_by_category = reduce(group_by_category, transactions, {})

    # Сортируем по убыванию
    return dict(
        sorted(cashback_by_category.items(), key=lambda x: x[1], reverse=True))


def investment_bank(month: str, transactions: List[Dict[str, Any]],
                    limit: int = 50) -> float:
    """
    Сервис 2: Инвесткопилка

    Рассчитывает сумму, которая отложится в Инвесткопилку при округлении трат
    """
    logger.info(f"Расчет Инвесткопилки за {month} с лимитом округления {limit}")

    try:
        # Парсим месяц
        year, month_num = map(int, month.split('-'))

        # Функциональный конвейер
        total_saved = pipe(
            transactions,
            lambda data: filter(filter_by_month_year(str(month_num), year),
                                data),  # Фильтр по дате
            list,
            lambda data: filter(lambda t: float(t.get('Сумма операции', 0)) < 0,
                                data),  # Только расходы
            list,
            lambda data: map(
                lambda t: calculate_rounding_difference(t, limit), data),
            # Разница от округления
            list,
            lambda values: reduce(reduce_sum, values, 0)  # Суммируем
        )

        logger.info(f"Инвесткопилка: отложено {total_saved:.2f} ₽")
        return round(total_saved, 2)

    except Exception as e:
        logger.error(f"Ошибка при расчете Инвесткопилки: {e}")
        return 0.0


def calculate_rounding_difference(transaction: Dict[str, Any],
                                    limit: int) -> float:
    """
    Вычисляет разницу между округленной суммой и фактической
    """
    amount = abs(float(transaction.get('Сумма операции', 0)))

    # Округление вверх до ближайшего кратного limit
    rounded = ((amount + limit - 1) // limit) * limit

    difference = rounded - amount
    return difference if difference > 0 else 0


def simple_search(transactions: List[Dict[str, Any]],
                  search_string: str) -> str:
    """
    Сервис 3: Простой поиск по описанию или категории
    """
    logger.info(f"Простой поиск по строке: '{search_string}'")

    # Функциональный конвейер
    found = pipe(
        transactions,
        lambda data: filter(filter_by_search_string(search_string), data),
        # Фильтр по строке
        list,
        lambda data: __format_transactions_for_json(data)
        # Форматирование для JSON
    )

    json_result = json.dumps(found, ensure_ascii=False, indent=2, default=str)
    logger.info(f"Поиск завершен. Найдено транзакций: {len(found)}")

    return json_result


def search_by_phone(transactions: List[Dict[str, Any]]) -> str:
    """
    Сервис 4: Поиск транзакций с номерами телефонов в описании
    """
    logger.info("Поиск транзакций с номерами телефонов")

    # Паттерн для поиска российских номеров телефонов
    phone_pattern = r'(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'

    # Функциональный конвейер
    found = pipe(
        transactions,
        lambda data: filter(filter_by_regex(phone_pattern), data),
        # Фильтр по телефону
        list,
        lambda data: __format_transactions_for_json(data)
        # Форматирование для JSON
    )

    json_result = json.dumps(found, ensure_ascii=False, indent=2, default=str)
    logger.info(f"Поиск телефонов завершен. Найдено транзакций: {len(found)}")

    return json_result


def search_transfers_to_individuals(transactions: List[Dict[str, Any]]) -> str:
    """
    Сервис 5: Поиск переводов физическим лицам
    """
    logger.info("Поиск переводов физическим лицам")

    # Паттерн для поиска: имя и первая буква фамилии с точкой
    name_pattern = r'\b[А-Я][а-я]+\s+[А-Я]\.'

    # Фильтр по категории "Переводы" и паттерну в описании
    def is_transfer_to_individual(transaction):
        category = str(transaction.get('Категория', '')).lower()
        description = str(transaction.get('Описание', ''))

        # Проверяем категорию
        if category != 'переводы':
            return False

        # Проверяем паттерн в описании
        return bool(re.search(name_pattern, description))

    # Функциональный конвейер
    found = pipe(
        transactions,
        lambda data: filter(is_transfer_to_individual, data),
        # Фильтр по переводам физлицам
        list,
        lambda data: __format_transactions_for_json(data)
        # Форматирование для JSON
    )

    json_result = json.dumps(found, ensure_ascii=False, indent=2, default=str)
    logger.info(
        f"Поиск переводов физлицам завершен. Найдено транзакций: {len(found)}")

    return json_result


def __format_transactions_for_json(transactions: List[Dict[str, Any]]) -> List[
    Dict[str, Any]]:
    """
    Форматирует транзакции для JSON-вывода
    """
    formatted = []
    for t in transactions:
        # Создаем копию и преобразуем специальные типы
        t_copy = {}
        for key, value in t.items():
            if hasattr(value, 'strftime'):  # Для datetime
                t_copy[key] = value.strftime('%d.%m.%Y %H:%M:%S')
            elif pd.isna(value):  # Для NaN
                t_copy[key] = None
            else:
                t_copy[key] = value
        formatted.append(t_copy)
    return formatted


# ============================================================================
# ДЕМОНСТРАЦИЯ ИСПОЛЬЗОВАНИЯ ФУНКЦИОНАЛЬНОГО ПРОГРАММИРОВАНИЯ
# ============================================================================

def demonstrate_functional_programming():
    """
    Демонстрирует использование элементов функционального программирования
    """
    print("\n" + "=" * 60)
    print("🧩 ДЕМОНСТРАЦИЯ ФУНКЦИОНАЛЬНОГО ПРОГРАММИРОВАНИЯ")
    print("=" * 60)

    # 1. Каррирование
    print("\n1️⃣ Каррирование:")
    filter_dec_2021 = filter_by_month_year('12', 2021)
    print("   filter_dec_2021 = filter_by_month_year('12', 2021)")

    # 2. Композиция функций
    print("\n2️⃣ Композиция функций:")
    process_transaction = compose(
        lambda x: x * 1.1,  # +10%
        abs,  # модуль
        float  # в число
    )
    print(f"   process_transaction(-100) = {process_transaction('-100'):.2f}")

    # 3. Конвейер (pipe)
    print("\n3️⃣ Конвейер обработки:")
    data = [-10, 20, -30, 40, -50]
    result = pipe(
        data,
        lambda lst: filter(lambda x: x < 0, lst),  # только отрицательные
        list,
        lambda lst: map(abs, lst),  # модуль
        list,
        lambda lst: reduce(lambda a, b: a + b, lst, 0)  # сумма
    )
    print(f"   data = {data}")
    print(f"   result = {result}")

    # 4. Функции высшего порядка
    print("\n4️⃣ Функции высшего порядка:")
    numbers = [1, 2, 3, 4, 5]
    doubled = list(map(lambda x: x * 2, numbers))
    evens = list(filter(lambda x: x % 2 == 0, numbers))
    print(f"   numbers = {numbers}")
    print(f"   map(x*2) = {doubled}")
    print(f"   filter(even) = {evens}")