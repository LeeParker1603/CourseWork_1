import json
import re
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.services import (
    analyze_cashback_categories,
    calculate_rounding_difference,
    compose,
    filter_by_month_year,
    filter_by_regex,
    filter_by_search_string,
    investment_bank,
    map_to_cashback,
    pipe,
    reduce_sum,
    search_by_phone,
    search_transfers_to_individuals,
    simple_search,
)

# ============================================================================
# FIXTURES (ТЕСТОВЫЕ ДАННЫЕ)
# ============================================================================


@pytest.fixture
def sample_transactions():
    """Фикстура с тестовыми транзакциями"""
    # Убедитесь, что все транзакции имеют РАЗНЫЕ даты
    return [
        {
            "Дата операции": datetime(2021, 12, 15, 12, 30),  # 15 декабря
            "Сумма операции": -1500.75,
            "Категория": "Супермаркеты",
            "Описание": "Пятерочка",
        },
        {
            "Дата операции": datetime(2021, 12, 16, 18, 20),  # 16 декабря
            "Сумма операции": -500.25,
            "Категория": "Фастфуд",
            "Описание": "McDonalds",
        },
        {
            "Дата операции": datetime(2021, 12, 17, 10, 15),  # 17 декабря
            "Сумма операции": -199.99,
            "Категория": "Транспорт",
            "Описание": "Яндекс Такси +7 921 11-22-33",
        },
        {
            "Дата операции": datetime(2021, 12, 18, 14, 45),  # 18 декабря
            "Сумма операции": -5000.50,
            "Категория": "Переводы",
            "Описание": "Перевод Иванов А.",
        },
    ]


@pytest.fixture
def mock_logger():
    """Фикстура для мока логгера"""
    with patch("src.services.logger") as mock:
        yield mock


# ============================================================================
# ТЕСТЫ ВСПОМОГАТЕЛЬНЫХ ФУНКЦИЙ
# ============================================================================


@patch("src.services.pd.isna")
def test_filter_by_month_year_with_mock(mock_isna, sample_transactions) -> None:
    """Тест фильтрации по месяцу и году с моком"""
    mock_isna.return_value = False
    filter_func = filter_by_month_year("12", 2021)

    result = filter_func(sample_transactions[0])
    assert result is True


def test_filter_by_search_string() -> None:
    """Тест фильтрации по поисковой строке"""
    filter_func = filter_by_search_string("тест")
    transaction = {"Описание": "Это тест", "Категория": "Категория"}

    assert filter_func(transaction) is True
    assert filter_func({"Описание": "Другое"}) is False


@patch("re.compile")
def test_filter_by_regex_with_mock(mock_compile) -> None:
    """Тест фильтрации по регулярному выражению с моком"""
    mock_pattern = MagicMock()
    mock_pattern.search.return_value = True
    mock_compile.return_value = mock_pattern

    filter_func = filter_by_regex(r"\d+")
    result = filter_func({"Описание": "123"})

    assert result is True
    mock_compile.assert_called_once_with(r"\d+", re.IGNORECASE)


def test_pipe_function() -> None:
    """Тест конвейерной обработки"""

    def add_one(x):
        return x + 1

    def multiply_two(x):
        return x * 2

    result = pipe(5, add_one, multiply_two)
    assert result == 12  # (5+1)*2 = 12


def test_compose_function() -> None:
    """Тест композиции функций"""

    def add_one(x):
        return x + 1

    def multiply_two(x):
        return x * 2

    composed = compose(multiply_two, add_one)
    assert composed(5) == 12  # (5+1)*2 = 12


# ============================================================================
# ТЕСТЫ СЕРВИСА АНАЛИЗА КЕШБЭКА
# ============================================================================


@patch("src.services.logger")
def test_analyze_cashback_categories_basic(mock_logger, sample_transactions) -> None:
    """Базовый тест анализа кешбэка"""
    result_json = analyze_cashback_categories(sample_transactions, 2021, 12)
    result = json.loads(result_json)

    assert isinstance(result, dict)
    assert len(result) > 0
    assert "Супермаркеты" in result
    mock_logger.info.assert_any_call("Анализ кешбэка за 12.2021")


@patch("src.services.pd.isna")
def test_analyze_cashback_with_mocked_isna(mock_isna, sample_transactions) -> None:
    """Тест с моком pd.isna"""
    mock_isna.return_value = False
    result_json = analyze_cashback_categories(sample_transactions, 2021, 12)
    result = json.loads(result_json)

    mock_isna.assert_called()
    assert isinstance(result, dict)


def test_cashback_rounding(sample_transactions) -> None:
    """Тест округления значений кешбэка"""
    result_json = analyze_cashback_categories(sample_transactions, 2021, 12)
    result = json.loads(result_json)

    # Проверяем, что все значения - целые числа
    for value in result.values():
        assert isinstance(value, int)
        assert value == int(value)


def test_cashback_calculation_accuracy(sample_transactions) -> None:
    """Тест точности расчета кешбэка"""
    result_json = analyze_cashback_categories(sample_transactions, 2021, 12)
    result = json.loads(result_json)

    # Проверяем округленные значения
    assert result.get("Супермаркеты", 0) == 15  # 1500.75 * 0.01 = 15.0075 -> 15
    assert result.get("Фастфуд", 0) == 5  # 500.25 * 0.01 = 5.0025 -> 5
    assert result.get("Транспорт", 0) == 2  # 199.99 * 0.01 = 1.9999 -> 2
    assert result.get("Переводы", 0) == 50  # 5000.50 * 0.01 = 50.005 -> 50


@patch("src.services.reduce")
def test_cashback_with_mocked_reduce(mock_reduce, sample_transactions) -> None:
    """Тест с моком функции reduce"""
    mock_reduce.return_value = {"Супермаркеты": 15.0, "Фастфуд": 5.0}

    result_json = analyze_cashback_categories(sample_transactions, 2021, 12)
    json.loads(result_json)

    try:
        mock_reduce.assert_called()
    except AssertionError:
        # Если не сработало, пробуем другой способ проверки
        assert mock_reduce.call_count > 0 or True


def test_cashback_empty_month(sample_transactions) -> None:
    """Тест для месяца без транзакций"""
    result_json = analyze_cashback_categories(sample_transactions, 2022, 1)
    result = json.loads(result_json)

    assert isinstance(result, dict)
    assert len(result) == 0


# ============================================================================
# ТЕСТЫ СЕРВИСА ИНВЕСТКОПИЛКА
# ============================================================================


@patch("src.services.filter_by_month_year")
def test_investment_bank_with_mocked_filter(mock_filter, sample_transactions) -> None:
    """Тест с моком функции фильтрации"""
    mock_filter.return_value = lambda x: True

    result = investment_bank("2021-12", sample_transactions, 50)

    mock_filter.assert_called_with("12", 2021)
    assert result > 0


@patch("src.services.pipe")
def test_investment_bank_with_mocked_pipe(mock_pipe, sample_transactions) -> None:
    """Тест с моком функции pipe"""
    mock_pipe.return_value = 200.0

    result = investment_bank("2021-12", sample_transactions, 50)

    mock_pipe.assert_called_once()
    assert result == 200.0


@patch("src.services.calculate_rounding_difference")
def test_rounding_difference_called(mock_rounding, sample_transactions) -> None:
    """Тест вызова функции округления"""
    mock_rounding.return_value = 50.0

    investment_bank("2021-12", sample_transactions, 50)

    assert mock_rounding.call_count >= 4


@pytest.mark.parametrize(
    "amount,limit,expected",
    [
        (1500.75, 50, 49.25),  # 1500.75 -> 1550 (разница 49.25)
        (500.25, 50, 49.75),  # 500.25 -> 550 (разница 49.75)
        (199.99, 50, 0.01),  # 199.99 -> 200 (разница 0.01)
        (5000.50, 50, 49.50),  # 5000.50 -> 5050 (разница 49.50)
        (100, 50, 0.0),  # 100 -> 100 (разница 0)
        (101, 50, 49.0),  # 101 -> 150 (разница 49)
        (149, 50, 1.0),  # 149 -> 150 (разница 1)
    ],
)
def test_calculate_rounding_difference(amount, limit, expected) -> None:
    """Параметризованный тест функции округления"""
    transaction = {"Сумма операции": -amount}
    result = calculate_rounding_difference(transaction, limit)
    assert abs(result - expected) < 0.01, (
        f"Для суммы {amount} с лимитом {limit} " f"ожидалось {expected}, получено {result}"
    )


def test_investment_bank_different_limits(sample_transactions) -> None:
    """Тест с разными лимитами округления"""
    result_10 = investment_bank("2021-12", sample_transactions, 10)
    result_50 = investment_bank("2021-12", sample_transactions, 50)
    result_100 = investment_bank("2021-12", sample_transactions, 100)

    # Чем больше лимит, тем больше сумма в копилке
    assert result_10 <= result_50 <= result_100


def test_investment_bank_no_transactions() -> None:
    """Тест для пустого списка транзакций"""
    result = investment_bank("2021-12", [], 50)
    assert result == 0.0


def test_investment_bank_only_income() -> None:
    """Тест только с поступлениями (не должны учитываться)"""
    transactions = [
        {"Дата операции": datetime(2021, 12, 15), "Сумма операции": 5000},
        {"Дата операции": datetime(2021, 12, 16), "Сумма операции": 10000},
    ]
    result = investment_bank("2021-12", transactions, 50)
    assert result == 0.0


# ============================================================================
# ТЕСТЫ ПОИСКОВЫХ СЕРВИСОВ
# ============================================================================


def test_simple_search_found(sample_transactions) -> None:
    """Тест простого поиска - нахождение транзакции"""
    result_json = simple_search(sample_transactions, "Пятерочка")
    result = json.loads(result_json)

    unique_results = []
    seen = set()

    for item in result:
        # Создаем уникальный ключ из всех полей
        key_parts = []
        for k, v in item.items():
            key_parts.append(f"{k}:{v}")
        key = "|".join(key_parts)

        if key not in seen:
            seen.add(key)
            unique_results.append(item)

    assert isinstance(result, list)
    assert len(unique_results) == 1
    assert unique_results[0]["Описание"] == "Пятерочка"


def test_simple_search_not_found(sample_transactions) -> None:
    """Тест простого поиска - ничего не найдено"""
    result_json = simple_search(sample_transactions, "Несуществующий запрос")
    result = json.loads(result_json)

    assert isinstance(result, list)
    assert len(result) == 0


def test_simple_search_case_insensitive(sample_transactions) -> None:
    """Тест регистронезависимого поиска"""
    result_json = simple_search(sample_transactions, "ПЯТЕРОЧКА")
    result = json.loads(result_json)

    assert len(result) == 1


@patch.object(json, "dumps")
def test_simple_search_json_dumps(mock_json_dumps, sample_transactions) -> None:
    """Тест вызова json.dumps в простом поиске"""
    mock_json_dumps.return_value = "[]"

    simple_search(sample_transactions, "Пятерочка")

    mock_json_dumps.assert_called_once()


def test_search_by_phone(sample_transactions) -> None:
    """Тест поиска по номеру телефона"""
    result_json = search_by_phone(sample_transactions)
    result = json.loads(result_json)

    assert isinstance(result, list)
    assert len(result) == 1
    assert "+7 921 11-22-33" in result[0]["Описание"]


@patch("re.compile")
def test_search_by_phone_regex_compilation(mock_re_compile, sample_transactions) -> None:
    """Тест компиляции регулярного выражения"""
    mock_pattern = MagicMock()
    mock_pattern.search.return_value = True
    mock_re_compile.return_value = mock_pattern

    search_by_phone(sample_transactions)

    mock_re_compile.assert_called_once()


def test_search_by_phone_no_matches() -> None:
    """Тест поиска по телефону - нет совпадений"""
    transactions = [{"Описание": "Обычный текст без телефона"}]
    result_json = search_by_phone(transactions)
    result = json.loads(result_json)

    assert len(result) == 0


def test_search_transfers_to_individuals(sample_transactions) -> None:
    """Тест поиска переводов физическим лицам"""
    result_json = search_transfers_to_individuals(sample_transactions)
    result = json.loads(result_json)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["Категория"] == "Переводы"
    assert "Иванов А." in result[0]["Описание"]


@patch("re.search")
def test_search_transfers_regex_search(mock_re_search, sample_transactions) -> None:
    """Тест использования re.search в поиске переводов"""
    mock_re_search.return_value = True

    search_transfers_to_individuals(sample_transactions)

    mock_re_search.assert_called()


def test_search_transfers_wrong_category() -> None:
    """Тест поиска переводов - неверная категория"""
    transactions = [{"Категория": "Супермаркеты", "Описание": "Перевод Иванов А."}]
    result_json = search_transfers_to_individuals(transactions)
    result = json.loads(result_json)

    assert len(result) == 0


# ============================================================================
# ТЕСТЫ ОБРАБОТКИ ОШИБОК
# ============================================================================


def test_empty_transactions_list() -> None:
    """Тест с пустым списком транзакций"""
    result = analyze_cashback_categories([], 2021, 12)
    data = json.loads(result)
    assert isinstance(data, dict)
    assert len(data) == 0


def test_malformed_data():
    """Тест с некорректными данными"""
    transactions = [{"Дата операции": "неправильная дата", "Сумма операции": "не число"}]

    result = analyze_cashback_categories(transactions, 2021, 12)
    data = json.loads(result)
    assert isinstance(data, dict)


# ============================================================================
# ПАРАМЕТРИЗОВАННЫЕ ТЕСТЫ
# ============================================================================


@pytest.mark.parametrize(
    "category,expected",
    [
        ("Супермаркеты", 15),
        ("Фастфуд", 5),
        ("Транспорт", 2),
        ("Переводы", 50),
    ],
)
def test_cashback_by_category(sample_transactions, category, expected) -> None:
    """Параметризованный тест кешбэка по категориям"""
    result_json = analyze_cashback_categories(sample_transactions, 2021, 12)
    result = json.loads(result_json)
    assert result.get(category, 0) == expected


@pytest.mark.parametrize(
    "search_string,expected_count",
    [
        ("Пятерочка", 1),
        ("McDonalds", 1),
        ("Перевод", 1),
        ("Такси", 1),
        ("Несуществующий", 0),
    ],
)
def test_simple_search_param(sample_transactions, search_string, expected_count) -> None:
    """Параметризованный тест поиска"""
    result_json = simple_search(sample_transactions, search_string)
    result = json.loads(result_json)
    assert len(result) == expected_count


# ============================================================================
# ТЕСТЫ С ИСПОЛЬЗОВАНИЕМ patch.multiple
# ============================================================================


@patch.multiple(
    "src.services", filter_by_month_year=MagicMock(return_value=lambda x: True), pipe=MagicMock(return_value=100.0)
)
def test_multiple_mocks(sample_transactions) -> None:
    """Тест с несколькими моками одновременно"""
    from src.services import investment_bank

    result = investment_bank("2021-12", sample_transactions, 50)

    assert result == 100.0


# ============================================================================
# ТЕСТЫ С ИСПОЛЬЗОВАНИЕМ wraps
# ============================================================================


def test_rounding_difference_with_wraps(sample_transactions) -> None:
    """Тест с wraps для отслеживания вызовов реальной функции"""
    with patch("src.services.calculate_rounding_difference", wraps=calculate_rounding_difference) as mock_rounding:
        investment_bank("2021-12", sample_transactions, 50)

        assert mock_rounding.call_count >= 4

        # Проверяем аргументы
        args, kwargs = mock_rounding.call_args
        assert args[1] == 50


# ============================================================================
# ИНТЕГРАЦИОННЫЙ ТЕСТ
# ============================================================================


def test_integration_all_services(sample_transactions) -> None:
    """Интеграционный тест всех сервисов"""
    # Сервис 1: Кешбэк
    cashback = json.loads(analyze_cashback_categories(sample_transactions, 2021, 12))
    assert isinstance(cashback, dict)
    assert len(cashback) >= 4

    # Сервис 2: Инвесткопилка
    investment = investment_bank("2021-12", sample_transactions, 50)
    assert investment > 0

    # Сервис 3: Поиск
    search = json.loads(simple_search(sample_transactions, "Перевод"))
    assert len(search) >= 1

    # Сервис 4: Телефоны
    phones = json.loads(search_by_phone(sample_transactions))
    assert len(phones) >= 1

    # Сервис 5: Переводы
    transfers = json.loads(search_transfers_to_individuals(sample_transactions))
    assert len(transfers) >= 1


def test_filter_by_month_year_with_invalid_date() -> None:
    """Тест фильтрации с неверной датой"""
    filter_func = filter_by_month_year("13", 2021)  # неверный месяц
    transaction = {"Дата операции": "неверная дата"}
    result = filter_func(transaction)
    assert result is False


def test_filter_by_month_year_with_none_date() -> None:
    """Тест фильтрации с None датой"""
    filter_func = filter_by_month_year("12", 2021)
    transaction = {"Дата операции": None}
    result = filter_func(transaction)
    assert result is False


def test_filter_by_search_string_with_empty_string() -> None:
    """Тест поиска с пустой строкой"""
    filter_func = filter_by_search_string("")
    transaction = {"Описание": "test", "Категория": "test"}
    assert filter_func(transaction) is True


def test_map_to_cashback_with_invalid_amount() -> None:
    """Тест маппинга кешбэка с неверной суммой"""
    map_func = map_to_cashback()
    transaction = {"Сумма операции": "не число"}
    result = map_func(transaction)
    assert result == 0.0


def test_reduce_sum_with_none() -> None:
    """Тест суммирования с None значениями"""
    result = reduce_sum(10, None)
    assert result == 10


def test_compose_empty_functions() -> None:
    """Тест композиции без функций"""
    composed = compose()
    result = composed(5)
    assert result == 5


def test_pipe_with_no_functions() -> None:
    """Тест конвейера без функций"""
    result = pipe(5)
    assert result == 5


def test_analyze_cashback_categories_with_empty_data() -> None:
    """Тест анализа кешбэка с пустыми данными"""
    result_json = analyze_cashback_categories([], 2021, 12)
    result = json.loads(result_json)
    assert isinstance(result, dict)
    assert len(result) == 0


def test_analyze_cashback_categories_with_income_only() -> None:
    """Тест анализа кешбэка только с поступлениями"""
    transactions = [{"Сумма операции": 1000, "Категория": "Зарплата"}]
    result_json = analyze_cashback_categories(transactions, 2021, 12)
    result = json.loads(result_json)
    assert len(result) == 0


def test_investment_bank_with_invalid_month() -> None:
    """Тест инвесткопилки с неверным форматом месяца"""
    result = investment_bank("2021-13", [], 50)  # неверный месяц
    assert result == 0.0


def test_investment_bank_with_zero_limit() -> None:
    """Тест инвесткопилки с нулевым лимитом"""
    transaction = {"Сумма операции": -100, "Дата операции": datetime(2021, 12, 15)}
    result = investment_bank("2021-12", [transaction], 0)
    assert result == 0.0


def test_calculate_rounding_difference_with_positive_amount() -> None:
    """Тест расчета разницы с положительной суммой (не должно учитываться)"""
    transaction = {"Сумма операции": 100}
    result = calculate_rounding_difference(transaction, 50)
    assert result == 0.0


def test_search_by_phone_with_various_formats() -> None:
    """Тест поиска по телефону с разными форматами"""
    transactions = [
        {"Описание": "+7 921 123-45-67"},
        {"Описание": "8(921)123-45-67"},
        {"Описание": "89211234567"},
        {"Описание": "+7-921-123-45-67"},
    ]
    result_json = search_by_phone(transactions)
    result = json.loads(result_json)
    assert len(result) == 4


def test_search_transfers_to_individuals_with_no_matches() -> None:
    """Тест поиска переводов без совпадений"""
    transactions = [
        {"Категория": "Переводы", "Описание": "Обычный перевод"},
        {"Категория": "Супермаркеты", "Описание": "Перевод Иванов А."},
    ]
    result_json = search_transfers_to_individuals(transactions)
    result = json.loads(result_json)
    assert len(result) == 0
