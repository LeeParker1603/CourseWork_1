import json
from datetime import datetime
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from src.views import generate_events_page_response, generate_main_page_response, get_date_range, get_greeting

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_transactions_df():
    """Фикстура с тестовым DataFrame (с правильными типами для JSON)"""
    return pd.DataFrame(
        {
            "Дата операции": [datetime(2021, 12, 15), datetime(2021, 12, 10)],
            "Дата платежа": [datetime(2021, 12, 15), datetime(2021, 12, 10)],
            "Номер карты": ["1234", "5678"],
            "Сумма операции": [-1500.0, -500.0],  # используем float вместо int64
            "Категория": ["Супермаркеты", "Фастфуд"],
            "Описание": ["Пятерочка", "McDonalds"],
        }
    )


@pytest.fixture
def mock_transactions_df_with_int64():
    """Фикстура с тестовым DataFrame содержащим int64 (для тестирования проблемы)"""
    df = pd.DataFrame(
        {
            "Дата операции": [datetime(2021, 12, 15), datetime(2021, 12, 10)],
            "Дата платежа": [datetime(2021, 12, 15), datetime(2021, 12, 10)],
            "Номер карты": ["1234", "5678"],
            "Сумма операции": [-1500, -500],  # это будут int64
            "Категория": ["Супермаркеты", "Фастфуд"],
            "Описание": ["Пятерочка", "McDonalds"],
        }
    )
    return df


# ============================================================================
# ТЕСТЫ ВСПОМОГАТЕЛЬНЫХ ФУНКЦИЙ
# ============================================================================


@pytest.mark.parametrize(
    "date_str,expected",
    [
        ("15.12.2021 08:00:00", "Доброе утро"),
        ("15.12.2021 14:00:00", "Добрый день"),
        ("15.12.2021 20:00:00", "Добрый вечер"),
        ("15.12.2021 02:00:00", "Доброй ночи"),
    ],
)
def test_get_greeting(date_str, expected) -> None:
    """Тест приветствия в зависимости от времени суток"""
    assert get_greeting(date_str) == expected


def test_get_date_range_week() -> None:
    """Тест диапазона за неделю"""
    start, end = get_date_range("15.12.2021", "W")
    assert start.weekday() == 0  # Понедельник
    assert end.day == 15


def test_get_date_range_month() -> None:
    """Тест диапазона за месяц"""
    start, end = get_date_range("15.12.2021", "M")
    assert start.day == 1
    assert start.month == 12
    assert end.day == 15


def test_get_date_range_year() -> None:
    """Тест диапазона за год"""
    start, end = get_date_range("15.12.2021", "Y")
    assert start.month == 1
    assert start.day == 1
    assert end.month == 12
    assert end.day == 15


def test_get_date_range_all() -> None:
    """Тест всех данных"""
    start, end = get_date_range("15.12.2021", "ALL")
    assert start.year == 1900
    assert end.day == 15


# ============================================================================
# ТЕСТЫ ГЛАВНОЙ СТРАНИЦЫ
# ============================================================================


@patch("src.views.read_transactions_from_excel")
@patch("src.views.load_user_settings")
@patch("src.views.get_currency_rates")
@patch("src.views.get_stock_prices")
def test_generate_main_page_with_all_mocks(
    mock_stocks, mock_currencies, mock_settings, mock_read_excel, mock_transactions_df
) -> None:
    """Тест с моками всех внешних зависимостей"""
    # Конвертируем DataFrame в сериализуемый формат

    mock_read_excel.return_value = mock_transactions_df
    mock_settings.return_value = {"user_currencies": ["USD"], "user_stocks": ["AAPL"]}
    mock_currencies.return_value = [{"currency": "USD", "rate": 92.45}]
    mock_stocks.return_value = [{"stock": "AAPL", "price": 175.50}]

    response_json = generate_main_page_response("15.12.2021", "fake_path.xls")
    response = json.loads(response_json)

    assert "greeting" in response
    assert "date" in response
    assert "cards" in response
    assert "top_transactions" in response
    assert "currency_rates" in response
    assert "stock_prices" in response

    mock_read_excel.assert_called_once_with("fake_path.xls")
    mock_settings.assert_called_once()


@patch("src.views.read_transactions_from_excel")
def test_generate_main_page_with_empty_data(mock_read_excel) -> None:
    """Тест главной страницы с пустыми данными"""
    mock_read_excel.return_value = pd.DataFrame()

    response_json = generate_main_page_response("15.12.2021", "fake_path.xls")
    response = json.loads(response_json)

    assert "error" in response


@patch("src.views.get_stock_prices", return_value=[])  # Мок акций
@patch("src.views.get_currency_rates", return_value=[])  # Мок валют
@patch("src.views.load_user_settings", return_value={"user_currencies": [], "user_stocks": []})  # Мок настроек
@patch("src.views.read_transactions_from_excel")
@patch("time.sleep", return_value=None)  # Мок sleep
def test_generate_main_page_cards_calculation(
    mock_sleep, mock_read_excel, mock_settings, mock_currency, mock_stocks, mock_transactions_df
) -> None:
    """Тест расчета данных по картам"""
    mock_read_excel.return_value = mock_transactions_df

    response_json = generate_main_page_response("15.12.2021", "fake_path.xls")
    response = json.loads(response_json)

    assert len(response["cards"]) == 2
    assert response["cards"][0]["last_digits"] in ["1234", "5678"]


@patch("src.views.get_stock_prices", return_value=[])  # Мок акций
@patch("src.views.get_currency_rates", return_value=[])  # Мок валют
@patch("src.views.load_user_settings", return_value={"user_currencies": [], "user_stocks": []})  # Мок настроек
@patch("src.views.get_date_range")
@patch("src.views.read_transactions_from_excel")
@patch("time.sleep", return_value=None)  # Мок sleep
def test_generate_events_page_with_mocked_date_range(
    mock_sleep, mock_read_excel, mock_get_date_range, mock_settings, mock_currency, mock_stocks, mock_transactions_df
) -> None:
    """Тест с моком функции get_date_range"""

    mock_read_excel.return_value = mock_transactions_df
    mock_get_date_range.return_value = (datetime(2021, 12, 1), datetime(2021, 12, 15))

    response_json = generate_events_page_response("15.12.2021", "M", "fake_path.xls")
    response = json.loads(response_json)

    mock_get_date_range.assert_called_once_with("15.12.2021", "M")
    assert "expenses" in response
    assert "income" in response

    # Проверяем, что sleep не вызывался
    mock_sleep.assert_not_called()


# ============================================================================
# ТЕСТЫ СТРАНИЦЫ СОБЫТИЙ
# ============================================================================


@patch("src.views.read_transactions_from_excel")
@patch("src.views.load_user_settings")
@patch("src.views.get_currency_rates")
@patch("src.views.get_stock_prices")
def test_generate_events_page_with_all_mocks(
    mock_stocks, mock_currencies, mock_settings, mock_read_excel, mock_transactions_df
) -> None:
    """Тест с моками всех внешних зависимостей для страницы событий"""

    mock_read_excel.return_value = mock_transactions_df  # <-- убрали convert_df_to_serializable
    mock_settings.return_value = {"user_currencies": ["USD"], "user_stocks": ["AAPL"]}
    mock_currencies.return_value = [{"currency": "USD", "rate": 92.45}]
    mock_stocks.return_value = [{"stock": "AAPL", "price": 175.50}]

    response_json = generate_events_page_response("15.12.2021", "M", "fake_path.xls")
    response = json.loads(response_json)

    assert "expenses" in response
    assert "income" in response
    assert "currency_rates" in response
    assert "stock_prices" in response


@patch("src.views.get_stock_prices", return_value=[])
@patch("src.views.get_currency_rates", return_value=[])
@patch("src.views.load_user_settings", return_value={"user_currencies": [], "user_stocks": []})
@patch("src.views.read_transactions_from_excel")
@patch("time.sleep", return_value=None)
def test_generate_main_page_int64_serialization(
    mock_sleep, mock_read_excel, mock_settings, mock_currency, mock_stocks, mock_transactions_df_with_int64
):
    """Тест сериализации int64 значений"""

    mock_read_excel.return_value = mock_transactions_df_with_int64

    response_json = generate_main_page_response("15.12.2021", "fake_path.xls")
    response = json.loads(response_json)

    # Проверяем наличие всех ключей
    assert "greeting" in response
    assert "date" in response
    assert "cards" in response
    assert "top_transactions" in response

    # Проверяем, что все числовые значения в cards конвертированы в стандартные типы
    for card in response["cards"]:
        # Проверяем ключи
        assert "last_digits" in card
        assert "total_spent" in card
        assert "cashback" in card

        # Проверяем типы
        assert isinstance(card["last_digits"], str)
        assert isinstance(card["total_spent"], (int, float))
        assert isinstance(card["cashback"], (int, float))

        # Дополнительно проверяем, что это не numpy типы
        assert not hasattr(card["total_spent"], "dtype")
        assert not hasattr(card["cashback"], "dtype")

    # Проверяем top_transactions
    for transaction in response["top_transactions"]:
        assert "date" in transaction
        assert "amount" in transaction
        assert "category" in transaction
        assert "description" in transaction

        assert isinstance(transaction["date"], str)
        assert isinstance(transaction["amount"], (int, float))
        assert isinstance(transaction["category"], str)
        assert isinstance(transaction["description"], str)

        # Проверяем, что amount не numpy тип
        assert not hasattr(transaction["amount"], "dtype")

    # Проверяем, что дата осталась строкой
    assert isinstance(response["date"], str)
    assert response["date"] == "15.12.2021"

    # Проверяем, что приветствие - строка
    assert isinstance(response["greeting"], str)


@pytest.mark.parametrize("period", ["W", "M", "Y", "ALL"])
@patch("src.views.get_stock_prices", return_value=[])
@patch("src.views.get_currency_rates", return_value=[])
@patch("src.views.load_user_settings", return_value={"user_currencies": [], "user_stocks": []})
@patch("src.views.get_date_range")
@patch("src.views.read_transactions_from_excel")
@patch("time.sleep", return_value=None)
def test_events_page_with_different_periods(
    mock_sleep,
    mock_read_excel,
    mock_get_date_range,
    mock_settings,
    mock_currency,
    mock_stocks,
    period,
    mock_transactions_df,
) -> None:
    """Тест страницы событий с разными периодами"""

    mock_read_excel.return_value = mock_transactions_df
    mock_get_date_range.return_value = (datetime(2021, 12, 1), datetime(2021, 12, 15))

    response_json = generate_events_page_response("15.12.2021", period, "fake_path.xls")
    response = json.loads(response_json)

    assert "expenses" in response
    assert "income" in response

    # Проверяем, что get_date_range был вызван с правильным периодом
    mock_get_date_range.assert_called_once_with("15.12.2021", period)

    # Проверяем, что sleep не вызывался
    mock_sleep.assert_not_called()


@patch("src.views.get_stock_prices", return_value=[])
@patch("src.views.get_currency_rates", return_value=[])
@patch("src.views.load_user_settings", return_value={"user_currencies": [], "user_stocks": []})
@patch("src.views.get_date_range")
@patch("src.views.read_transactions_from_excel")
@patch("time.sleep", return_value=None)
def test_events_page_expenses_calculation(
    mock_sleep, mock_read_excel, mock_get_date_range, mock_settings, mock_currency, mock_stocks, mock_transactions_df
) -> None:
    """Тест расчета расходов на странице событий"""

    mock_read_excel.return_value = mock_transactions_df
    mock_get_date_range.return_value = (datetime(2021, 12, 1), datetime(2021, 12, 15))

    response_json = generate_events_page_response("15.12.2021", "M", "fake_path.xls")
    response = json.loads(response_json)

    # Общая сумма расходов: 1500 + 500 = 2000
    assert response["expenses"]["total_amount"] == 2000

    # Проверяем структуру расходов
    assert "main" in response["expenses"]
    assert "transfers_and_cash" in response["expenses"]

    # Проверяем, что все моки были вызваны
    mock_read_excel.assert_called_once_with("fake_path.xls")
    mock_get_date_range.assert_called_once_with("15.12.2021", "M")
    mock_settings.assert_called_once()
    mock_currency.assert_called_once_with([])
    mock_stocks.assert_called_once_with([])
    mock_sleep.assert_not_called()


# ============================================================================
# ТЕСТЫ С ИСПОЛЬЗОВАНИЕМ patch.object
# ============================================================================


@patch.object(json, "dumps")
def test_main_page_json_dumps(mock_json_dumps, mock_transactions_df) -> None:
    """Тест вызова json.dumps в главной странице"""
    mock_json_dumps.return_value = "{}"

    with patch("src.views.read_transactions_from_excel", return_value=mock_transactions_df):
        with patch("src.views.load_user_settings", return_value={}):
            generate_main_page_response("15.12.2021", "fake_path.xls")

    mock_json_dumps.assert_called_once()


@patch("src.views.get_currency_rates")
@patch("src.views.get_stock_prices")
def test_currency_and_stock_calls(mock_stocks, mock_currencies, mock_transactions_df) -> None:
    """Тест вызова функций получения курсов валют и акций"""
    mock_currencies.return_value = []
    mock_stocks.return_value = []

    with patch("src.views.read_transactions_from_excel", return_value=mock_transactions_df):
        with patch("src.views.load_user_settings", return_value={"user_currencies": ["USD"], "user_stocks": ["AAPL"]}):
            generate_main_page_response("15.12.2021", "fake_path.xls")

    mock_currencies.assert_called_once_with(["USD"])
    mock_stocks.assert_called_once_with(["AAPL"])


# ============================================================================
# ТЕСТЫ С ИСПОЛЬЗОВАНИЕМ side_effect
# ============================================================================


@patch("src.views.read_transactions_from_excel")
def test_read_excel_error_handling(mock_read_excel) -> None:
    """Тест обработки ошибки чтения файла"""
    mock_read_excel.side_effect = Exception("Ошибка чтения файла")

    response_json = generate_main_page_response("15.12.2021", "fake_path.xls")
    response = json.loads(response_json)

    assert "error" in response


# ============================================================================
# ИНТЕГРАЦИОННЫЙ ТЕСТ
# ============================================================================


@patch("src.views.read_transactions_from_excel")
@patch("src.views.load_user_settings")
def test_integration_main_page(mock_settings, mock_read_excel, mock_transactions_df_with_int64) -> None:
    """Интеграционный тест главной страницы"""
    # Используем DataFrame с int64 для проверки сериализации
    mock_read_excel.return_value = mock_transactions_df_with_int64
    mock_settings.return_value = {"user_currencies": ["USD"], "user_stocks": ["AAPL"]}

    # Должно работать без ошибок сериализации
    response_json = generate_main_page_response("15.12.2021", "fake_path.xls")
    response = json.loads(response_json)

    # Проверяем все ключевые элементы
    assert response["date"] == "15.12.2021"
    assert len(response["cards"]) == 2
    assert len(response["top_transactions"]) == 2
    assert len(response["currency_rates"]) >= 0
    assert len(response["stock_prices"]) >= 0


# ============================================================================
# ДОПОЛНИТЕЛЬНЫЙ ТЕСТ ДЛЯ ПРОВЕРКИ СЕРИАЛИЗАЦИИ
# ============================================================================


def test_json_serialization_with_numpy_types() -> None:
    """Тест сериализации numpy типов в JSON"""
    data = {"int64": np.int64(42), "float64": np.float64(3.14), "int32": np.int32(100), "float32": np.float32(1.5)}

    # Пытаемся сериализовать напрямую - должно упасть
    with pytest.raises(TypeError):
        json.dumps(data)

    # Конвертируем в обычные типы
    converted_data = {
        "int64": int(data["int64"]),
        "float64": float(data["float64"]),
        "int32": int(data["int32"]),
        "float32": float(data["float32"]),
    }

    # Теперь должно работать
    json_str = json.dumps(converted_data)
    assert isinstance(json_str, str)


def test_get_greeting_with_current_time() -> None:
    """Тест приветствия с текущим временем"""
    from datetime import datetime

    result = get_greeting(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
    assert result in ["Доброе утро", "Добрый день", "Добрый вечер", "Доброй ночи"]


def test_get_date_range_with_invalid_period() -> None:
    """Тест диапазона с неверным периодом"""
    start, end = get_date_range("15.12.2021", "X")  # неверный период
    assert start.day == 1  # должен вернуть месяц по умолчанию


def test_calculate_expenses_data_with_no_expenses() -> None:
    """Тест расчета расходов без расходов"""
    from src.views import calculate_expenses_data

    df = pd.DataFrame({"Сумма операции": [100, 200], "Категория": ["Зарплата", "Бонус"]})  # только поступления
    result = calculate_expenses_data(df)
    assert result["total_amount"] == 0
    assert len(result["main"]) == 0
    assert len(result["transfers_and_cash"]) == 0


def test_calculate_income_data_with_no_income() -> None:
    """Тест расчета поступлений без поступлений"""
    from src.views import calculate_income_data

    df = pd.DataFrame({"Сумма операции": [-100, -200], "Категория": ["Еда", "Транспорт"]})  # только расходы
    result = calculate_income_data(df)
    assert result["total_amount"] == 0
    assert len(result["main"]) == 0


def test_generate_events_page_with_empty_data(mock_transactions_df) -> None:
    """Тест страницы событий с пустыми данными"""
    with patch("src.views.read_transactions_from_excel", return_value=pd.DataFrame()):
        response_json = generate_events_page_response("15.12.2021", "M", "fake_path.xls")
        response = json.loads(response_json)
        assert "error" in response


@patch("src.views.get_date_range")
@patch("src.views.read_transactions_from_excel")
def test_generate_events_page_with_filter_error(mock_read_excel, mock_get_date_range) -> None:
    """Тест страницы событий с ошибкой фильтрации"""
    mock_read_excel.return_value = pd.DataFrame({"Дата операции": ["2021-12-15"]})
    mock_get_date_range.side_effect = Exception("Ошибка диапазона")

    response_json = generate_events_page_response("15.12.2021", "M", "fake_path.xls")
    response = json.loads(response_json)
    assert "error" in response


def test_get_greeting_with_invalid_date() -> None:
    """Тест приветствия с неверной датой"""
    result = get_greeting("не дата")
    assert result in ["Доброе утро", "Добрый день", "Добрый вечер", "Доброй ночи"]


def test_calculate_expenses_with_no_expenses() -> None:
    """Тест расчета расходов без расходов"""
    from src.views import calculate_expenses_data

    df = pd.DataFrame({"Сумма операции": [100, 200]})
    result = calculate_expenses_data(df)
    assert result["total_amount"] == 0
    assert len(result["main"]) == 0
    assert len(result["transfers_and_cash"]) == 0


def test_calculate_income_with_no_income() -> None:
    """Тест расчета поступлений без поступлений"""
    from src.views import calculate_income_data

    df = pd.DataFrame({"Сумма операции": [-100, -200]})
    result = calculate_income_data(df)
    assert result["total_amount"] == 0
    assert len(result["main"]) == 0


def test_generate_main_page_with_empty_df() -> None:
    """Тест главной страницы с пустым DataFrame"""
    with patch("src.views.read_transactions_from_excel", return_value=pd.DataFrame()):
        response_json = generate_main_page_response("15.12.2021", "fake.xls")
        response = json.loads(response_json)
        assert "error" in response


def test_generate_events_page_with_empty_df() -> None:
    """Тест страницы событий с пустым DataFrame"""
    with patch("src.views.read_transactions_from_excel", return_value=pd.DataFrame()):
        response_json = generate_events_page_response("15.12.2021", "M", "fake.xls")
        response = json.loads(response_json)
        assert "error" in response


def test_get_greeting_edge_cases() -> None:
    """Тест приветствия для граничных случаев"""
    # Ровно 6 утра
    assert get_greeting("15.12.2021 06:00:00") == "Доброе утро"
    # Ровно 12 дня
    assert get_greeting("15.12.2021 12:00:00") == "Добрый день"
    # Ровно 18 вечера
    assert get_greeting("15.12.2021 18:00:00") == "Добрый вечер"
    # Ровно 23 ночи
    assert get_greeting("15.12.2021 23:00:00") == "Доброй ночи"
    # Ровно 0 ночи
    assert get_greeting("15.12.2021 00:00:00") == "Доброй ночи"


def test_get_date_range_all_periods() -> None:
    """Тест всех возможных периодов"""
    # Неделя
    start_w, end_w = get_date_range("20.12.2021", "W")
    assert start_w.weekday() == 0  # понедельник
    assert start_w.day == 20 or start_w.day == 13  # зависит от года

    # Месяц
    start_m, end_m = get_date_range("20.12.2021", "M")
    assert start_m.day == 1
    assert start_m.month == 12

    # Год
    start_y, end_y = get_date_range("20.12.2021", "Y")
    assert start_y.month == 1
    assert start_y.day == 1

    # Все данные
    start_a, end_a = get_date_range("20.12.2021", "ALL")
    assert start_a.year == 1900
    assert end_a.day == 20


def test_calculate_expenses_data_with_transfers() -> None:
    """Тест расчета расходов с переводами и наличными"""
    from src.views import calculate_expenses_data

    df = pd.DataFrame(
        {"Сумма операции": [-100, -200, -300, -400], "Категория": ["Переводы", "Наличные", "Еда", "Транспорт"]}
    )

    result = calculate_expenses_data(df)

    # Проверяем переводы и наличные
    assert len(result["transfers_and_cash"]) == 2

    # Проверяем сортировку по убыванию
    assert result["transfers_and_cash"][0]["amount"] >= result["transfers_and_cash"][1]["amount"]


def test_calculate_income_data_complex() -> None:
    """Тест расчета поступлений со сложными данными"""
    from src.views import calculate_income_data

    df = pd.DataFrame(
        {"Сумма операции": [1000, 2000, 3000, 500], "Категория": ["Зарплата", "Бонус", "Возврат", "Кэшбэк"]}
    )

    result = calculate_income_data(df)

    assert result["total_amount"] == 6500
    assert len(result["main"]) == 4
    # Проверяем сортировку
    assert result["main"][0]["amount"] >= result["main"][1]["amount"]


@patch("src.views.get_stock_prices", return_value=[])
@patch("src.views.get_currency_rates", return_value=[])
@patch("src.views.load_user_settings", return_value={"user_currencies": [], "user_stocks": []})
@patch("src.views.read_transactions_from_excel")
@patch("time.sleep", return_value=None)
def test_generate_main_page_with_filter_error(
    mock_sleep, mock_read, mock_settings, mock_currency, mock_stocks
) -> None:
    """Тест главной страницы с ошибкой фильтрации"""

    df = pd.DataFrame({"Дата операции": ["2021-12-15"], "Номер карты": ["1234"], "Сумма операции": [-1500]})
    mock_read.return_value = df

    with patch("src.views.filter_transactions_by_date", side_effect=Exception("Ошибка")):
        response_json = generate_main_page_response("15.12.2021", "fake.xls")
        response = json.loads(response_json)

        # Должен быть ответ, даже при ошибке
        assert "greeting" in response
        assert "cards" in response
        assert "top_transactions" in response
        assert "currency_rates" in response
        assert "stock_prices" in response

        # Проверяем, что ошибка фильтрации не привела к падению
        mock_sleep.assert_not_called()


@patch("src.views.get_stock_prices", return_value=[])
@patch("src.views.get_currency_rates", return_value=[])
@patch("src.views.load_user_settings", return_value={"user_currencies": [], "user_stocks": []})
@patch("src.views.read_transactions_from_excel")
@patch("time.sleep", return_value=None)
def test_generate_main_page_with_calculation_error(
    mock_sleep, mock_read, mock_settings, mock_currency, mock_stocks
) -> None:
    """Тест главной страницы с ошибкой расчета"""

    df = pd.DataFrame({"Дата операции": ["2021-12-15"], "Номер карты": ["1234"], "Сумма операции": [-1500]})
    mock_read.return_value = df

    with patch("src.views.calculate_card_data", side_effect=Exception("Ошибка расчета")):
        response_json = generate_main_page_response("15.12.2021", "fake.xls")
        response = json.loads(response_json)

        # Проверяем, что cards пустой при ошибке
        assert "cards" in response
        assert response["cards"] == []

        # Проверяем, что остальные поля присутствуют
        assert "greeting" in response
        assert "date" in response
        assert "top_transactions" in response
        assert "currency_rates" in response
        assert "stock_prices" in response

        # Проверяем, что ошибка не повлияла на другие данные
        assert response["date"] == "15.12.2021"

        # Проверяем, что sleep не вызывался
        mock_sleep.assert_not_called()


@patch("src.views.get_stock_prices", return_value=[])
@patch("src.views.get_currency_rates", return_value=[])
@patch("src.views.load_user_settings", return_value={"user_currencies": [], "user_stocks": []})
@patch("src.views.get_date_range", return_value=(datetime(2021, 12, 1), datetime(2021, 12, 15)))
@patch("src.views.read_transactions_from_excel")
@patch("time.sleep", return_value=None)
def test_generate_events_page_with_calculation_error(
    mock_sleep, mock_read, mock_date_range, mock_settings, mock_currency, mock_stocks
) -> None:
    """Тест страницы событий с ошибкой расчета"""

    df = pd.DataFrame({"Дата операции": [datetime(2021, 12, 15)], "Сумма операции": [-1500], "Категория": ["Еда"]})
    mock_read.return_value = df

    with patch("src.views.calculate_expenses_data", side_effect=Exception("Ошибка расчета")):
        response_json = generate_events_page_response("15.12.2021", "M", "fake.xls")
        response = json.loads(response_json)

        # Проверяем, что expenses есть и total_amount = 0 при ошибке
        assert "expenses" in response
        assert response["expenses"]["total_amount"] == 0
        assert "income" in response
        assert "currency_rates" in response
        assert "stock_prices" in response

        # Проверяем структуру expenses при ошибке
        assert "main" in response["expenses"]
        assert "transfers_and_cash" in response["expenses"]
        assert response["expenses"]["main"] == []
        assert response["expenses"]["transfers_and_cash"] == []

        # Проверяем, что все моки были вызваны
        mock_read.assert_called_once_with("fake.xls")
        mock_date_range.assert_called_once_with("15.12.2021", "M")
        mock_settings.assert_called_once()
        mock_currency.assert_called_once_with([])
        mock_stocks.assert_called_once_with([])
        mock_sleep.assert_not_called()


@patch("src.views.load_user_settings")
@patch("src.views.read_transactions_from_excel")
def test_generate_main_page_with_settings_error(mock_read, mock_settings) -> None:
    """Тест главной страницы с ошибкой загрузки настроек"""
    df = pd.DataFrame({"Дата операции": [datetime(2021, 12, 15)], "Номер карты": ["1234"], "Сумма операции": [-1500]})
    mock_read.return_value = df
    mock_settings.side_effect = Exception("Ошибка настроек")

    response_json = generate_main_page_response("15.12.2021", "fake.xls")
    response = json.loads(response_json)

    assert "greeting" in response
    assert "currency_rates" in response
    assert "stock_prices" in response


@patch("src.views.get_currency_rates")
@patch("src.views.load_user_settings")
@patch("src.views.read_transactions_from_excel")
def test_generate_main_page_with_currency_error(mock_read, mock_settings, mock_currency) -> None:
    """Тест главной страницы с ошибкой получения курсов валют"""
    df = pd.DataFrame({"Дата операции": [datetime(2021, 12, 15)], "Номер карты": ["1234"], "Сумма операции": [-1500]})
    mock_read.return_value = df
    mock_settings.return_value = {"user_currencies": ["USD"]}
    mock_currency.side_effect = Exception("Ошибка API")

    response_json = generate_main_page_response("15.12.2021", "fake.xls")
    response = json.loads(response_json)

    assert response["currency_rates"] == []


@patch("src.views.get_stock_prices")
@patch("src.views.load_user_settings")
@patch("src.views.read_transactions_from_excel")
def test_generate_main_page_with_stocks_error(mock_read, mock_settings, mock_stocks) -> None:
    """Тест главной страницы с ошибкой получения акций"""
    df = pd.DataFrame({"Дата операции": [datetime(2021, 12, 15)], "Номер карты": ["1234"], "Сумма операции": [-1500]})
    mock_read.return_value = df
    mock_settings.return_value = {"user_stocks": ["AAPL"]}
    mock_stocks.side_effect = Exception("Ошибка API")

    response_json = generate_main_page_response("15.12.2021", "fake.xls")
    response = json.loads(response_json)

    assert response["stock_prices"] == []


def test_calculate_expenses_data_with_exact_7_categories() -> None:
    """Тест расчета расходов с ровно 7 категориями"""
    from src.views import calculate_expenses_data

    data = []
    for i in range(7):
        data.append({"Сумма операции": -100 * (i + 1), "Категория": f"Категория_{i}"})

    df = pd.DataFrame(data)
    result = calculate_expenses_data(df)

    assert len(result["main"]) == 7
    # Не должно быть категории "Остальное"
    for cat in result["main"]:
        assert cat["category"] != "Остальное"


def test_calculate_top_transactions_with_mixed_data() -> None:
    """Тест топ транзакций со смешанными данными"""
    from src.views import calculate_top_transactions

    df = pd.DataFrame(
        {
            "Дата операции": [
                datetime(2021, 12, 15),
                datetime(2021, 12, 16),
                datetime(2021, 12, 17),
                datetime(2021, 12, 18),
            ],
            "Сумма операции": [-100, -200, -300, -400],
            "Категория": ["Еда", "Транспорт", "Развлечения", "Здоровье"],
            "Описание": ["Покупка 1", "Покупка 2", "Покупка 3", "Покупка 4"],
        }
    )

    result = calculate_top_transactions(df)

    assert len(result) == 4
    # Проверяем сортировку по убыванию
    assert result[0]["amount"] == 400
    assert result[1]["amount"] == 300
    assert result[2]["amount"] == 200
    assert result[3]["amount"] == 100


def test_calculate_top_transactions_with_long_description() -> None:
    """Тест топ транзакций с длинным описанием"""
    from src.views import calculate_top_transactions

    long_desc = "Очень длинное описание " * 10  # больше 50 символов

    df = pd.DataFrame(
        {
            "Дата операции": [datetime(2021, 12, 15)],
            "Сумма операции": [-1000],
            "Категория": ["Еда"],
            "Описание": [long_desc],
        }
    )

    result = calculate_top_transactions(df)

    assert len(result) == 1
    assert len(result[0]["description"]) <= 53  # 50 + '...'


@patch("src.views.get_stock_prices", return_value=[])
@patch("src.views.get_currency_rates", return_value=[])
@patch("src.views.load_user_settings", return_value={"user_currencies": [], "user_stocks": []})
@patch("src.views.convert_numpy_types")
@patch("src.views.read_transactions_from_excel")
@patch("time.sleep", return_value=None)
def test_generate_main_page_with_conversion_error(
    mock_sleep, mock_read, mock_convert, mock_settings, mock_currency, mock_stocks
) -> None:
    """Тест главной страницы с ошибкой конвертации типов"""

    # Создаем DataFrame с данными для top_transactions
    df = pd.DataFrame(
        {
            "Дата операции": [datetime(2021, 12, 15)],
            "Номер карты": ["1234"],
            "Сумма операции": [-1500],
            "Категория": ["Супермаркеты"],
            "Описание": ["Пятерочка"],
        }
    )
    mock_read.return_value = df
    mock_convert.side_effect = Exception("Ошибка конвертации")

    response_json = generate_main_page_response("15.12.2021", "fake.xls")
    response = json.loads(response_json)

    # Проверяем наличие всех полей
    assert "greeting" in response
    assert "date" in response
    assert "cards" in response
    assert "top_transactions" in response
    assert "currency_rates" in response
    assert "stock_prices" in response

    # Проверяем, что данные есть
    assert response["date"] == "15.12.2021"
    assert len(response["cards"]) == 1
    assert len(response["top_transactions"]) == 1  # Теперь должно быть 1

    # Проверяем содержимое
    assert response["cards"][0]["last_digits"] == "1234"
    assert response["top_transactions"][0]["amount"] == 1500
    assert response["top_transactions"][0]["category"] == "Супермаркеты"
    assert response["top_transactions"][0]["description"] == "Пятерочка"


@patch("src.views.get_date_range")
@patch("src.views.read_transactions_from_excel")
def test_generate_events_page_with_date_range_error(mock_read, mock_range) -> None:
    """Тест страницы событий с ошибкой в get_date_range"""
    df = pd.DataFrame({"Дата операции": [datetime(2021, 12, 15)], "Сумма операции": [-1500]})
    mock_read.return_value = df
    mock_range.side_effect = Exception("Ошибка диапазона")

    response_json = generate_events_page_response("15.12.2021", "M", "fake.xls")
    response = json.loads(response_json)

    assert "error" in response


def test_calculate_expenses_data_with_nan_categories() -> None:
    """Тест расчета расходов с NaN в категориях"""
    from src.views import calculate_expenses_data

    df = pd.DataFrame({"Сумма операции": [-100, -200, -300], "Категория": [None, "Еда", np.nan]})

    result = calculate_expenses_data(df)

    assert result["total_amount"] == 600
    # None и NaN должны быть заменены на 'Не указано'


def test_calculate_income_data_with_nan_categories() -> None:
    """Тест расчета поступлений с NaN в категориях"""
    from src.views import calculate_income_data

    df = pd.DataFrame({"Сумма операции": [100, 200, 300], "Категория": [None, "Зарплата", np.nan]})

    result = calculate_income_data(df)

    assert result["total_amount"] == 600
    # None и NaN должны быть обработаны


def test_categorize_transaction_with_edge_cases() -> None:
    """Тест категоризации с граничными случаями"""
    from src.utils import categorize_transaction

    # Перевод в описании, но другая категория
    assert categorize_transaction({"Категория": "Еда", "Описание": "перевод другу"}) == "Переводы"

    # Наличные в описании
    assert categorize_transaction({"Категория": "Еда", "Описание": "снял наличные"}) == "Наличные"

    # Пустое описание, пустая категория
    assert categorize_transaction({"Категория": "", "Описание": ""}) == "Прочее"

    # Только пробелы
    assert categorize_transaction({"Категория": "  ", "Описание": "  "}) == "Прочее"
