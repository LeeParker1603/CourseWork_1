import json
import logging
import os
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Optional

import pandas as pd

from src.utils import convert_numpy_types

# Настройка логирования

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# ============================================================================
# ДЕКОРАТОР ДЛЯ СОХРАНЕНИЯ ОТЧЕТОВ
# ============================================================================


def save_report(filename: Optional[str] = None, pattern: Optional[str] = None) -> Callable:
    """
    Декоратор для сохранения результатов отчета в файл
    - Если filename указан без даты: файл перезаписывается при каждом вызове.
    - Если filename содержит дату: удаляются все файлы с таким паттерном,
      создается новый с текущей датой и временем.
    - Если filename не указан: генерируется имя с датой,
      удаляются все файлы с паттерном имени функции.

    Параметры:
        filename: имя файла для сохранения (может содержать {date} для подстановки)
        pattern: паттерн для удаления старых файлов (если не указан, определяется автоматически)

    Примеры использования:
        @save_report()  # авто-имя с датой, удаляет старые файлы этой функции
        @save_report("my_report.json")  # всегда перезаписывает один файл
        @save_report("report_{date}.json")  # создает файлы с датой, удаляет старые
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Выполняем функцию
            result = func(*args, **kwargs)

            # Создаем папку reports, если её нет
            reports_dir = "data/reports"
            os.makedirs(reports_dir, exist_ok=True)

            # Определяем имя файла и паттерн для удаления
            current_time = datetime.now()
            timestamp = current_time.strftime("%Y%m%d_%H%M%S")
            date_str = current_time.strftime("%Y%m%d")

            # Определяем имя файла и паттерн для удаления
            if filename:
                # Если в имени есть {date}, подставляем текущую дату
                if "{date}" in filename:
                    base_filename = filename.replace("{date}", date_str)
                    output_file = base_filename
                    # Паттерн для удаления: часть до даты
                    pattern_to_use = pattern or filename.split("{date}")[0]
                else:
                    # Простое имя файла - перезаписываем
                    output_file = filename
                    pattern_to_use = None
            else:
                # Авто-имя: имя функции + timestamp
                output_file = f"{func.__name__}_{timestamp}.json"
                # Паттерн для удаления: имя функции
                pattern_to_use = pattern or func.__name__

            filepath = os.path.join(reports_dir, output_file)

            # Удаляем старые файлы по паттерну
            if pattern_to_use:
                deleted_count = 0
                for old_file in os.listdir(reports_dir):
                    if not old_file.endswith(".json"):
                        continue

                    # Проверяем, соответствует ли файл паттерну
                    if pattern_to_use in old_file:
                        old_path = os.path.join(reports_dir, old_file)
                        try:
                            # Не удаляем текущий файл (если он уже существует)
                            if old_file != output_file:
                                os.remove(old_path)
                                logger.info(f"🗑️ Удален старый файл по паттерну '{pattern_to_use}': {old_file}")
                                deleted_count += 1
                        except Exception as e:
                            logger.warning(f"Не удалось удалить {old_file}: {e}")

                if deleted_count > 0:
                    logger.info(f"Всего удалено файлов по паттерну '{pattern_to_use}': {deleted_count}")
            else:
                # Если нет паттерна, просто удаляем существующий файл (перезапись)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.info(f"🗑️ Удален старый файл: {output_file}")

            # Сохраняем результат
            try:
                if isinstance(result, pd.DataFrame):
                    result_to_save = result.to_dict(orient="records")
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(result_to_save, f, ensure_ascii=False, indent=2, default=str)
                else:
                    with open(filepath, "w", encoding="utf-8") as f:
                        if isinstance(result, str):
                            f.write(result)
                        else:
                            json.dump(result, f, ensure_ascii=False, indent=2, default=str)

                logger.info(f"✅ Отчет сохранен в файл: {filepath}")

            except Exception as e:
                logger.error(f"❌ Ошибка при сохранении отчета: {e}")

            return result

        return wrapper

    return decorator


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================


def parse_date(date_str: Optional[str] = None) -> datetime:
    """
    Преобразует строку с датой в объект datetime.
    Если дата не передана, возвращает текущую дату.
    """
    if date_str is None:
        return datetime.now()

    try:
        # Пробуем разные форматы даты
        if " " in date_str:
            return datetime.strptime(date_str, "%d.%m.%Y %H:%M:%S")
        else:
            return datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            logger.error(f"Не удалось распарсить дату: {date_str}")
            return datetime.now()


def filter_last_3_months(transactions: pd.DataFrame, end_date: datetime) -> pd.DataFrame:
    """
    Фильтрует транзакции за последние 3 месяца от указанной даты
    """
    start_date = end_date - timedelta(days=90)  # примерно 3 месяца

    # Убеждаемся, что колонка с датой существует
    if "Дата операции" not in transactions.columns:
        logger.error("Колонка 'Дата операции' не найдена")
        return pd.DataFrame()

    # Фильтруем по дате
    mask = (transactions["Дата операции"] >= start_date) & (transactions["Дата операции"] <= end_date)
    filtered = transactions.loc[mask].copy()

    logger.info(f"Отфильтровано транзакций за последние 3 месяца: {len(filtered)}")
    return filtered


# ============================================================================
# ОСНОВНЫЕ ФУНКЦИИ ОТЧЕТОВ
# ============================================================================


@save_report("spending_by_category.json")
def spending_by_category(transactions: pd.DataFrame, category: str, date: Optional[str] = None) -> pd.DataFrame:
    """
    Отчет 1: Траты по заданной категории за последние 3 месяца

    Параметры:
        transactions: DataFrame с транзакциями
        category: название категории
        date: опциональная дата (формат: ДД.ММ.ГГГГ)

    Возвращает:
        DataFrame с тратами по категории за каждый месяц
    """
    logger.info(f"📊 Отчет по категории '{category}'")

    try:
        # Определяем дату
        end_date = parse_date(date)
        logger.info(f"Дата отсчета: {end_date.strftime('%d.%m.%Y')}")

        # Фильтруем за последние 3 месяца
        try:
            filtered = filter_last_3_months(transactions, end_date)
        except Exception as e:
            logger.error(f"Ошибка при фильтрации данных: {e}")
            return pd.DataFrame(columns=["Месяц", "Сумма", "Количество"])

        if filtered.empty:
            logger.warning("Нет данных за указанный период")
            return pd.DataFrame(columns=["Месяц", "Сумма", "Количество"])

        # Фильтруем по категории и расходам (отрицательные суммы)
        category_mask = filtered["Категория"].str.lower() == category.lower()
        expenses_mask = filtered["Сумма операции"] < 0

        category_transactions = filtered[category_mask & expenses_mask].copy()

        if category_transactions.empty:
            logger.info(f"Нет трат по категории '{category}' за последние 3 месяца")
            return pd.DataFrame(columns=["Месяц", "Сумма", "Количество"])

        # Добавляем колонку с месяцем
        category_transactions["Месяц"] = category_transactions["Дата операции"].dt.to_period("M")

        # Группируем по месяцам
        monthly_stats = (
            category_transactions.groupby("Месяц")
            .agg({"Сумма операции": lambda x: abs(x.sum()), "Дата операции": "count"})
            .rename(columns={"Сумма операции": "Сумма", "Дата операции": "Количество"})
            .round(2)
        )

        # Преобразуем период в строку для JSON
        monthly_stats.index = monthly_stats.index.astype(str)

        logger.info(f"Найдено транзакций по категории: {len(category_transactions)}")

        return monthly_stats.reset_index()

    except Exception as e:
        logger.error(f"Неожиданная ошибка в отчете по категориям: {e}")
        return pd.DataFrame(columns=["Месяц", "Сумма", "Количество"])


@save_report()
def spending_by_weekday(transactions: pd.DataFrame, date: Optional[str] = None) -> pd.DataFrame:
    """
    Отчет 2: Средние траты по дням недели за последние 3 месяца

    Параметры:
        transactions: DataFrame с транзакциями
        date: опциональная дата (формат: ДД.ММ.ГГГГ)

    Возвращает:
        DataFrame со средними тратами по дням недели
    """
    logger.info("📊 Отчет по тратам в разрезе дней недели")

    try:
        # Определяем дату
        end_date = parse_date(date)

        # Фильтруем за последние 3 месяца
        try:
            filtered = filter_last_3_months(transactions, end_date)
        except Exception as e:
            logger.error(f"Ошибка при фильтрации данных: {e}")
            return pd.DataFrame(columns=["День недели", "Средние траты", "Всего трат", "Количество"])

        # Только расходы
        expenses = filtered[filtered["Сумма операции"] < 0].copy()

        if expenses.empty:
            logger.info("Нет расходов за указанный период")
            return pd.DataFrame(columns=["День недели", "Средние траты", "Всего трат", "Количество"])

        # Добавляем колонку с днем недели (0 - понедельник, 6 - воскресенье)
        expenses["День_недели"] = expenses["Дата операции"].dt.dayofweek
        expenses["Сумма_расхода"] = abs(expenses["Сумма операции"])

        # Словарь для названий дней недели
        weekdays = {
            0: "Понедельник",
            1: "Вторник",
            2: "Среда",
            3: "Четверг",
            4: "Пятница",
            5: "Суббота",
            6: "Воскресенье",
        }

        # Группируем по дням недели
        weekday_stats = expenses.groupby("День_недели").agg({"Сумма_расхода": ["sum", "mean", "count"]}).round(2)

        # Переименовываем колонки
        weekday_stats.columns = ["Всего трат", "Средние траты", "Количество"]

        # Добавляем названия дней
        weekday_stats["День недели"] = weekday_stats.index.map(weekdays)

        # Сортируем по дню недели
        weekday_stats = weekday_stats.sort_index().reset_index(drop=True)

        # Переставляем колонки
        weekday_stats = weekday_stats[["День недели", "Средние траты", "Всего трат", "Количество"]]

        logger.info(f"Рассчитаны средние траты для {len(weekday_stats)} дней недели")

        return weekday_stats

    except Exception as e:
        logger.error(f"Неожиданная ошибка в отчете по дням недели: {e}")
        return pd.DataFrame(columns=["День недели", "Средние траты", "Всего трат", "Количество"])


@save_report()
def spending_by_workday(transactions: pd.DataFrame, date: Optional[str] = None) -> pd.DataFrame:
    """
    Отчет 3: Сравнение трат в рабочие и выходные дни за последние 3 месяца

    Параметры:
        transactions: DataFrame с транзакциями
        date: опциональная дата (формат: ДД.ММ.ГГГГ)

    Возвращает:
        DataFrame со средними тратами в рабочие и выходные дни
    """
    logger.info("📊 Отчет по тратам в рабочие/выходные дни")

    try:
        # Определяем дату
        end_date = parse_date(date)

        # Фильтруем за последние 3 месяца
        try:
            filtered = filter_last_3_months(transactions, end_date)
        except Exception as e:
            logger.error(f"Ошибка при фильтрации данных: {e}")
            return pd.DataFrame(columns=["Тип дня", "Средние траты", "Всего трат", "Количество"])

        # Только расходы
        expenses = filtered[filtered["Сумма операции"] < 0].copy()

        if expenses.empty:
            logger.info("Нет расходов за указанный период")
            return pd.DataFrame(columns=["Тип дня", "Средние траты", "Всего трат", "Количество"])

        # Определяем рабочие и выходные дни
        expenses["День_недели"] = expenses["Дата операции"].dt.dayofweek
        expenses["Тип_дня"] = expenses["День_недели"].apply(lambda x: "Выходной" if x >= 5 else "Рабочий")
        expenses["Сумма_расхода"] = abs(expenses["Сумма операции"])

        # Группируем по типу дня
        workday_stats = expenses.groupby("Тип_дня").agg({"Сумма_расхода": ["sum", "mean", "count"]}).round(2)

        # Переименовываем колонки
        workday_stats.columns = ["Всего трат", "Средние траты", "Количество"]

        # Создаем результат в нужном формате
        result = workday_stats.reset_index()
        result = result.rename(columns={"Тип_дня": "Тип дня"})
        result = result[["Тип дня", "Средние траты", "Всего трат", "Количество"]]

        # Добавляем процентное соотношение
        total_expenses = result["Всего трат"].sum()
        if total_expenses > 0:
            result["Процент от общих трат"] = (result["Всего трат"] / total_expenses * 100).round(1)

        logger.info(
            f"Рассчитаны траты: рабочие дни - {result.iloc[0]['Всего трат']:.2f}, "
            f"выходные - {result.iloc[1]['Всего трат']:.2f}"
        )

        return result

    except Exception as e:
        logger.error(f"Неожиданная ошибка в отчете по рабочим/выходным дням: {e}")
        return pd.DataFrame(columns=["Тип дня", "Средние траты", "Всего трат", "Количество"])


# ============================================================================
# ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ ДЛЯ ОТЧЕТОВ
# ============================================================================


@save_report("detailed_category_analysis.json")
def detailed_category_analysis(transactions: pd.DataFrame, category: str, date: Optional[str] = None) -> dict:
    """
    Детальный анализ по категории (дополнительная функция)
    """
    end_date = parse_date(date)
    filtered = filter_last_3_months(transactions, end_date)

    if filtered.empty:
        return {"error": "Нет данных"}

    category_data = filtered[filtered["Категория"].str.lower() == category.lower()]

    result = {
        "category": category,
        "period": {"from": (end_date - timedelta(days=90)).strftime("%d.%m.%Y"), "to": end_date.strftime("%d.%m.%Y")},
        "total_spent": 0,
        "transactions_count": 0,
        "average_transaction": 0,
        "max_transaction": 0,
        "min_transaction": 0,
        "by_month": {},
    }

    if category_data.empty:
        return result

    # Только расходы (отрицательные суммы)
    expenses = category_data[category_data["Сумма операции"] < 0]

    if not expenses.empty:
        # Берем абсолютные значения для расчетов
        expenses_abs = abs(expenses["Сумма операции"])
        result["total_spent"] = float(expenses_abs.sum())
        result["transactions_count"] = int(len(expenses))
        result["average_transaction"] = float(expenses_abs.mean())
        result["max_transaction"] = float(expenses_abs.max())
        result["min_transaction"] = float(expenses_abs.min())

    # Детализация по месяцам
    expenses["month"] = expenses["Дата операции"].dt.to_period("M")
    for month, group in expenses.groupby("month"):
        result["by_month"][str(month)] = {"spent": abs(group["Сумма операции"].sum()), "count": len(group)}

    return convert_numpy_types(result)
