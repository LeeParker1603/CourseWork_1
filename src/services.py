import json
import logging
import re
from datetime import datetime
from functools import reduce
from typing import Any, Callable, Dict, List

import pandas as pd

from src.utils import calculate_cashback_by_category

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (функциональный стиль)
# ============================================================================


def filter_by_month_year(month: str, year: int) -> Callable:
    """
    Функция для фильтрации транзакций по месяцу и году

    Пример: filter_by_month_year('12', 2021)(transaction)
    """

    def filter_func(transaction: Dict[str, Any]) -> bool:
        date_str = ""
        try:
            date_str = transaction.get("Дата операции", "")
            if pd.isna(date_str):
                return False

            # Пробуем разные форматы даты
            if isinstance(date_str, str):
                if " " in date_str:
                    date_obj = datetime.strptime(date_str, "%d.%m.%Y %H:%M:%S")
                else:
                    date_obj = datetime.strptime(date_str, "%d.%m.%Y")
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
    search_lower = search_string.lower().strip()

    def filter_func(transaction: Dict[str, Any]) -> bool:
        description = str(transaction.get("Описание", "")).lower().strip()
        category = str(transaction.get("Категория", "")).lower().strip()

        return search_lower in description or search_lower in category

    return filter_func


def filter_by_regex(pattern: str) -> Callable:
    """
    Функция для фильтрации по регулярному выражению
    """
    compiled = re.compile(pattern, re.IGNORECASE)

    def filter_func(transaction: Dict[str, Any]) -> bool:
        description = str(transaction.get("Описание", ""))
        return bool(compiled.search(description))

    return filter_func


def filter_by_category(categories: List[str]) -> Callable:
    """
    Каррированная функция для фильтрации по категориям
    """
    categories_lower = [c.lower() for c in categories]

    def filter_func(transaction: Dict[str, Any]) -> bool:
        category = str(transaction.get("Категория", "")).lower()
        return category in categories_lower

    return filter_func


def map_to_cashback(rate: float = 0.01) -> Callable:
    """
    Функция для маппинга транзакции в сумму кешбэка
    """

    def map_func(transaction: Dict[str, Any]) -> float:
        try:
            amount = abs(float(transaction.get("Сумма операции", 0)))
            return amount * rate
        except (ValueError, TypeError):
            # В случае ошибки преобразования возвращаем 0
            return 0.0

    return map_func


def reduce_sum(acc: float, value: float) -> float:
    """
    Функция свёртки для суммирования с обработкой None
    """
    # Обработка None значений
    if value is None:
        return acc
    if acc is None:
        return value if value is not None else 0.0

    # Обработка случаев, когда value может быть не числом
    try:
        return acc + float(value)
    except (TypeError, ValueError):
        # Если не удалось преобразовать, возвращаем аккумулятор без изменений
        return acc


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


def analyze_cashback_categories(transactions: List[Dict[str, Any]], year: int, month: int) -> str:
    """
    Сервис 1: Анализ выгодных категорий повышенного кешбэка

    Анализирует, сколько кешбэка можно получить в каждой категории.
    Возвращает JSON с округленными до целых значениями
    """
    logger.info(f"Анализ кешбэка за {month}.{year}")

    try:
        # Функциональный конвейер обработки
        result = pipe(
            transactions,
            lambda data: filter(filter_by_month_year(str(month), year), data),
            # Фильтр по дате
            list,
            lambda data: filter(lambda t: int(t.get("Сумма операции", 0)) < 0, data),  # Только расходы
            list,
            lambda data: calculate_cashback_by_category(data),
            # Расчет кешбэка по категориям
        )

        # Преобразуем в JSON
        json_result = json.dumps(result, ensure_ascii=False, indent=2)
        logger.info(f"Анализ завершен. Найдено категорий: {len(result)}")

        return json_result

    except Exception as e:
        logger.error(f"Ошибка при анализе кешбэка: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)


def investment_bank(month: str, transactions: List[Dict[str, Any]], limit: int = 50) -> float:
    """
    Сервис 2: Инвесткопилка

    Рассчитывает сумму, которая отложится в Инвесткопилку при округлении трат
    """
    logger.info(f"Расчет Инвесткопилки за {month} с лимитом округления {limit}")

    try:
        # Парсим месяц
        year, month_num = map(int, month.split("-"))

        # Функциональный конвейер
        total_saved = pipe(
            transactions,
            lambda data: filter(filter_by_month_year(str(month_num), year), data),  # Фильтр по дате
            list,
            lambda data: filter(lambda t: float(t.get("Сумма операции", 0)) < 0, data),  # Только расходы
            list,
            lambda data: map(lambda t: calculate_rounding_difference(t, limit), data),
            # Разница от округления
            list,
            lambda values: reduce(reduce_sum, values, 0),  # Суммируем
        )

        logger.info(f"Инвесткопилка: отложено {total_saved:.2f} ₽")
        return round(total_saved, 2)

    except Exception as e:
        logger.error(f"Ошибка при расчете Инвесткопилки: {e}")
        return 0.0


def calculate_rounding_difference(transaction: Dict[str, Any], limit: int) -> float:
    """
    Вычисляет разницу между округленной суммой и фактической
    """
    try:
        amount = abs(float(transaction.get("Сумма операции", 0)))

        if amount <= 0:
            return 0.0

        # Вычисляем, сколько целых частей limit помещается в amount
        quotient = amount / limit

        # Получаем целую часть
        integer_part = int(quotient)

        # Проверяем, делится ли сумма на limit без остатка.
        # Используем небольшую погрешность для floating point
        remainder = amount % limit

        # Если остаток очень маленький (из-за погрешностей floating point)
        if abs(remainder) < 1e-10 or abs(remainder - limit) < 1e-10:
            return 0.0

        # Округляем вверх
        rounded = (integer_part + 1) * limit
        difference = rounded - amount

        return round(difference, 2)

    except (ValueError, TypeError, ZeroDivisionError) as e:
        logger.error(f"Ошибка при расчете разницы округления: {e}")
        return 0.0


def simple_search(transactions: List[Dict[str, Any]], search_string: str) -> str:
    """
    Сервис 3: Простой поиск по описанию или категории
    """
    logger.info(f"Простой поиск по строке: '{search_string}'")

    try:
        search_lower = search_string.lower().strip()

        # Фильтруем транзакции
        filtered = []
        seen_keys = set()

        for transaction in transactions:
            description = str(transaction.get("Описание", "")).lower().strip()
            category = str(transaction.get("Категория", "")).lower().strip()

            if search_lower in description or search_lower in category:
                # Создаем уникальный ключ для транзакции
                date_val = transaction.get("Дата операции", "")
                if hasattr(date_val, "strftime") and not pd.isna(date_val):
                    date_key = date_val.strftime("%Y%m%d%H%M%S")
                else:
                    date_key = str(date_val)

                amount = transaction.get("Сумма операции", 0)
                desc = transaction.get("Описание", "")

                unique_key = f"{date_key}_{amount}_{desc}"

                # Добавляем только уникальные транзакции
                if unique_key not in seen_keys:
                    seen_keys.add(unique_key)
                    filtered.append(transaction)

        # Форматируем для JSON
        formatted = format_transactions_for_json(filtered)
        json_result = json.dumps(formatted, ensure_ascii=False, indent=2)

        logger.info(f"Поиск завершен. Найдено транзакций: {len(formatted)}")
        return json_result

    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)


def search_by_phone(transactions: List[Dict[str, Any]]) -> str:
    """
    Сервис 4: Поиск транзакций с номерами телефонов в описании
    """
    logger.info("Поиск транзакций с номерами телефонов")

    # Паттерн для поиска российских номеров телефонов
    phone_pattern = r"(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{2,3}[\s\-]?\d{2,3}"

    # Функциональный конвейер
    found = pipe(
        transactions,
        lambda data: filter(filter_by_regex(phone_pattern), data),
        # Фильтр по телефону
        list,
        lambda data: format_transactions_for_json(data),
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
    name_pattern = r"\b[А-Я][а-я]+\s+[А-Я]\."

    # Фильтр по категории "Переводы" и паттерну в описании
    def is_transfer_to_individual(transaction):
        category = str(transaction.get("Категория", "")).lower()
        description = str(transaction.get("Описание", ""))

        # Проверяем категорию
        if category != "переводы":
            return False

        # Проверяем паттерн в описании
        return bool(re.search(name_pattern, description))

    # Функциональный конвейер
    found = pipe(
        transactions,
        lambda data: filter(is_transfer_to_individual, data),
        # Фильтр по переводам физлицам
        list,
        lambda data: format_transactions_for_json(data),
        # Форматирование для JSON
    )

    json_result = json.dumps(found, ensure_ascii=False, indent=2, default=str)
    logger.info(f"Поиск переводов физлицам завершен. Найдено транзакций: {len(found)}")

    return json_result


def format_transactions_for_json(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Форматирует транзакции для JSON-вывода с обработкой NaT и NaN
    """

    formatted = []
    seen_keys = set()

    for i, t in enumerate(transactions):

        # Создаем уникальный ключ для проверки дубликатов
        key_parts = []
        for key, value in t.items():
            try:
                if hasattr(value, "strftime"):
                    if pd.isna(value):
                        key_parts.append(f"{key}:NaT")
                    else:
                        date_str = value.strftime("%Y%m%d%H%M%S")
                        key_parts.append(f"{key}:{date_str}")
                else:
                    key_parts.append(f"{key}:{value}")
            except Exception as e:
                key_parts.append(f"{key}:ERROR")

        unique_key = "|".join(key_parts)

        if unique_key in seen_keys:
            continue

        seen_keys.add(unique_key)

        # Форматируем транзакцию
        t_copy = {}
        for key, value in t.items():
            try:
                if pd.isna(value):
                    t_copy[key] = None
                elif hasattr(value, "strftime"):
                    date_str = value.strftime("%d.%m.%Y %H:%M:%S")
                    t_copy[key] = date_str
                else:
                    t_copy[key] = value
            except Exception as e:
                t_copy[key] = None

        formatted.append(t_copy)

    return formatted
