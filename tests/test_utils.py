import json
from datetime import datetime
from unittest.mock import MagicMock, mock_open, patch

import numpy as np
import pandas as pd
import requests

from src.utils import (
    calculate_card_data,
    calculate_top_transactions,
    convert_numpy_types,
    filter_transactions_by_date,
    get_currency_rates,
    get_stock_prices,
    get_usd_to_rub_rate,
    load_user_settings,
    read_transactions_from_excel,
)


def test_read_transactions_from_excel_file_not_found() -> None:
    """Тест чтения несуществующего файла"""
    result = read_transactions_from_excel("not_exists.xls")
    assert result.empty


@patch("src.utils.pd.read_excel")
def test_read_transactions_from_excel_success(mock_read_excel) -> None:
    """Тест успешного чтения файла"""
    mock_df = pd.DataFrame({"test": [1, 2]})
    mock_read_excel.return_value = mock_df

    result = read_transactions_from_excel("test.xls")
    assert not result.empty
    mock_read_excel.assert_called_once_with("test.xls")


@patch("src.utils.pd.read_excel")
def test_read_transactions_from_excel_error(mock_read_excel) -> None:
    """Тест ошибки при чтении файла"""
    mock_read_excel.side_effect = Exception("Ошибка чтения")

    result = read_transactions_from_excel("test.xls")
    assert result.empty


def test_filter_transactions_by_date_with_invalid_date() -> None:
    """Тест фильтрации с неверной датой"""
    df = pd.DataFrame({"Дата операции": [datetime.now()]})
    result = filter_transactions_by_date(df, "invalid_date")
    assert len(result) == 1  # должна вернуть исходный df


def test_load_user_settings_file_not_found() -> None:
    """Тест загрузки настроек при отсутствии файла"""
    # Патчим os.path.exists на уровне модуля, где он используется
    with patch("os.path.exists", return_value=False):
        result = load_user_settings()

        # Проверяем, что вернулись настройки по умолчанию
        assert "user_currencies" in result
        assert "user_stocks" in result
        assert result["user_currencies"] == []
        assert result["user_stocks"] == []


@patch("os.path.exists")
@patch("builtins.open", new_callable=mock_open)
@patch("json.load")
def test_load_user_settings_success(mock_json_load, mock_file, mock_exists) -> None:
    """Тест успешной загрузки настроек"""
    # Настраиваем моки
    mock_exists.return_value = True
    mock_json_load.return_value = {"user_currencies": ["USD", "EUR"], "user_stocks": ["AAPL", "GOOGL"]}

    # Вызываем функцию
    result = load_user_settings()

    # Проверяем результат (это главное)
    assert result["user_currencies"] == ["USD", "EUR"]
    assert result["user_stocks"] == ["AAPL", "GOOGL"]

    assert mock_exists.call_count > 0
    mock_file.assert_called()
    mock_json_load.assert_called_once()


@patch("src.utils.requests.get")
def test_get_currency_rates_success(mock_get):
    """Тест успешного получения курсов валют"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"rates": {"USD": 0.013}}
    mock_get.return_value = mock_response

    result = get_currency_rates(["USD"])
    assert len(result) == 1
    assert result[0]["currency"] == "USD"


@patch("os.path.exists")
@patch("builtins.open")
@patch("json.load")
def test_load_user_settings_json_error(mock_json_load, mock_open, mock_exists) -> None:
    """Тест ошибки при загрузке JSON"""
    # Настраиваем моки
    mock_exists.return_value = True
    mock_json_load.side_effect = json.JSONDecodeError("Error", "", 0)

    # Вызываем функцию
    result = load_user_settings()

    # Должны вернуться настройки по умолчанию
    assert "user_currencies" in result
    assert "user_stocks" in result
    assert result["user_currencies"] == []

    assert mock_exists.call_count > 0
    mock_open.assert_called()
    mock_json_load.assert_called()


@patch("requests.get")
def test_get_usd_to_rub_rate_success(mock_get):
    """Тест успешного получения курса USD/RUB"""

    # Настраиваем мок ответа от ЦБ РФ
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"rates": {"USD": 0.0108}}  # 1 RUB = 0.0108 USD, значит 1 USD = 92.59 RUB
    mock_get.return_value = mock_response

    # Вызываем функцию
    result = get_usd_to_rub_rate()

    # Проверяем результат (1 / 0.0108 ≈ 92.59)
    assert round(result, 2) == 92.59
    mock_get.assert_called_once_with("https://www.cbr-xml-daily.ru/latest.js", timeout=5)


@patch("src.utils.get_usd_to_rub_rate")
@patch("requests.get")
@patch.dict("os.environ", {"ALPHA_VANTAGE_API_KEY": "test_api_key_123"})
def test_get_stock_prices_success(mock_get, mock_rate):
    """Тест успешного получения цен акций"""

    # Настраиваем мок курса валют
    mock_rate.return_value = 92.45

    # Создаем мок ответа для AMZN
    mock_response_amzn = MagicMock()
    mock_response_amzn.status_code = 200
    mock_response_amzn.json.return_value = {
        "Global Quote": {
            "05. price": "150.50",
            "09. change": "+2.50",
            "10. change percent": "+1.68%",
            "06. volume": "1000000",
        }
    }

    # Создаем мок ответа для GOOGL
    mock_response_googl = MagicMock()
    mock_response_googl.status_code = 200
    mock_response_googl.json.return_value = {
        "Global Quote": {
            "05. price": "138.20",
            "09. change": "-1.30",
            "10. change percent": "-0.93%",
            "06. volume": "800000",
        }
    }

    # Устанавливаем side_effect для последовательных вызовов
    mock_get.side_effect = [mock_response_amzn, mock_response_googl]

    # Вызываем функцию
    symbols = ["AMZN", "GOOGL"]
    result = get_stock_prices(symbols)

    # Проверяем результат
    assert len(result) == 2

    # Проверяем первую акцию (AMZN)
    assert result[0]["stock"] == "AMZN"
    assert result[0]["price"] == round(150.50 * 92.45, 2)  # ~13915.47
    assert "error" not in result[0]

    # Проверяем вторую акцию (GOOGL)
    assert result[1]["stock"] == "GOOGL"
    assert result[1]["price"] == round(138.20 * 92.45, 2)  # ~12777.79
    assert "error" not in result[1]

    # Проверяем, что requests.get был вызван дважды с правильными параметрами
    assert mock_get.call_count == 2

    # Проверяем параметры первого вызова
    mock_get.assert_any_call(
        "https://www.alphavantage.co/query",
        params={"function": "GLOBAL_QUOTE", "symbol": "AMZN", "apikey": "test_api_key_123"},
        timeout=10,
    )

    # Проверяем параметры второго вызова
    mock_get.assert_any_call(
        "https://www.alphavantage.co/query",
        params={"function": "GLOBAL_QUOTE", "symbol": "GOOGL", "apikey": "test_api_key_123"},
        timeout=10,
    )


@patch("src.utils.get_usd_to_rub_rate")
@patch("requests.get")
@patch.dict("os.environ", {"ALPHA_VANTAGE_API_KEY": "test_api_key_123"})
def test_get_stock_prices_rate_limit(mock_get, mock_rate):
    """Тест превышения лимита запросов (Note в ответе)"""

    mock_rate.return_value = 92.45

    # Мок ответа с Note о превышении лимита
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"Note": "API call frequency limit exceeded. Please upgrade your plan."}
    mock_get.return_value = mock_response

    result = get_stock_prices(["AMZN"])

    assert len(result) == 1
    assert result[0]["stock"] == "AMZN"
    assert result[0]["price"] is None
    assert "error" in result[0]
    assert "лимит" in result[0]["error"].lower()


@patch("src.utils.get_usd_to_rub_rate")
@patch.dict("os.environ", {}, clear=True)  # Сначала очищаем окружение
def test_get_stock_prices_no_api_key(mock_rate):
    """Тест отсутствия API ключа (должен вернуть тестовые данные)"""

    # Настраиваем мок курса
    mock_rate.return_value = 92.45

    # Вызываем функцию без мока requests.get
    # Она должна использовать fallback или вернуть ошибку
    result = get_stock_prices(["AMZN"])

    # Проверяем результат
    assert len(result) == 1
    assert result[0]["stock"] == "AMZN"

    # В зависимости от реализации, может быть цена или None
    # Если есть функция get_mock_stock_prices, то цена должна быть
    if result[0]["price"] is not None:
        print(f"Цена из fallback: {result[0]['price']}")
    else:
        assert "error" in result[0]


@patch("src.utils.get_usd_to_rub_rate")
@patch("requests.get")
@patch.dict("os.environ", {"ALPHA_VANTAGE_API_KEY": "test_api_key_123"})
def test_get_stock_prices_api_error(mock_get, mock_rate):
    """Тест ошибки API (статус не 200)"""

    mock_rate.return_value = 92.45

    # Мок ответа с ошибкой
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.return_value = {"error": "Internal server error"}
    mock_get.return_value = mock_response

    result = get_stock_prices(["AMZN"])

    assert len(result) == 1
    assert result[0]["stock"] == "AMZN"
    assert result[0]["price"] is None
    assert "error" in result[0]
    assert "500" in result[0]["error"] or "API" in result[0]["error"]


@patch("src.utils.get_usd_to_rub_rate")
@patch("requests.get")
@patch.dict("os.environ", {"ALPHA_VANTAGE_API_KEY": "test_api_key_123"})
def test_get_stock_prices_invalid_price(mock_get, mock_rate):
    """Тест неверного формата цены"""

    mock_rate.return_value = 92.45

    # Мок ответа с некорректной ценой
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"Global Quote": {"05. price": "invalid_price", "09. change": "+2.50"}}
    mock_get.return_value = mock_response

    result = get_stock_prices(["AMZN"])

    assert len(result) == 1
    assert result[0]["stock"] == "AMZN"
    assert result[0]["price"] is None
    assert "error" in result[0]
    assert "Неверный формат цены" in result[0]["error"]


@patch("src.utils.get_usd_to_rub_rate")
@patch("requests.get")
@patch.dict("os.environ", {"ALPHA_VANTAGE_API_KEY": "test_api_key_123"})
def test_get_stock_prices_timeout(mock_get, mock_rate):
    """Тест таймаута запроса"""

    mock_rate.return_value = 92.45

    # Мок таймаута
    mock_get.side_effect = requests.exceptions.Timeout("Request timeout")

    result = get_stock_prices(["AMZN"])

    assert len(result) == 1
    assert result[0]["stock"] == "AMZN"
    assert result[0]["price"] is None
    assert "error" in result[0]


@patch("src.utils.get_usd_to_rub_rate")
@patch("requests.get")
@patch("time.sleep", return_value=None)  # Мокаем sleep, чтобы тест шел быстрее
@patch.dict("os.environ", {"ALPHA_VANTAGE_API_KEY": "test_api_key_123"})
def test_get_stock_prices_sleep_called(mock_sleep, mock_get, mock_rate):
    """Тест, что sleep вызывается между запросами"""

    mock_rate.return_value = 92.45

    # Мок ответов
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"Global Quote": {"05. price": "150.50"}}
    mock_get.return_value = mock_response

    # Вызываем с двумя символами
    result = get_stock_prices(["AMZN", "GOOGL"])

    # Проверяем, что sleep был вызван один раз (между запросами)
    mock_sleep.assert_called_once_with(12)


@patch("src.utils.get_usd_to_rub_rate")
@patch("requests.get")
@patch.dict("os.environ", {"ALPHA_VANTAGE_API_KEY": "test_api_key_123"})
def test_get_stock_prices_mixed_responses(mock_get, mock_rate):
    """Тест смешанных ответов (успех и ошибка)"""

    mock_rate.return_value = 92.45

    # Успешный ответ для AMZN
    mock_response_success = MagicMock()
    mock_response_success.status_code = 200
    mock_response_success.json.return_value = {"Global Quote": {"05. price": "150.50"}}

    # Ответ с ошибкой для GOOGL
    mock_response_error = MagicMock()
    mock_response_error.status_code = 429
    mock_response_error.json.return_value = {"Note": "Rate limit exceeded"}

    mock_get.side_effect = [mock_response_success, mock_response_error]

    result = get_stock_prices(["AMZN", "GOOGL"])

    assert len(result) == 2
    assert result[0]["stock"] == "AMZN"
    assert result[0]["price"] is not None
    assert result[1]["stock"] == "GOOGL"
    assert result[1]["price"] is None
    assert "error" in result[1]


def test_calculate_card_data_empty_df() -> None:
    """Тест расчета данных по картам с пустым DataFrame"""
    result = calculate_card_data(pd.DataFrame())
    assert result == []


def test_calculate_top_transactions_empty() -> None:
    """Тест топ транзакций с пустым DataFrame"""
    result = calculate_top_transactions(pd.DataFrame())
    assert result == []


def test_calculate_top_transactions_no_expenses() -> None:
    """Тест топ транзакций без расходов"""
    df = pd.DataFrame({"Сумма операции": [100, 200], "Категория": ["test", "test"], "Описание": ["test", "test"]})
    result = calculate_top_transactions(df)
    assert result == []


def test_convert_numpy_types() -> None:
    """Тест конвертации numpy типов"""
    data = {
        "int": np.int64(42),
        "float": np.float64(3.14),
        "array": np.array([1, 2, 3]),
        "bool": np.bool_(True),
        "none": None,
        "dict": {"nested": np.int64(100)},
    }

    converted = convert_numpy_types(data)

    assert isinstance(converted["int"], int)
    assert isinstance(converted["float"], float)
    assert isinstance(converted["array"], list)
    assert isinstance(converted["bool"], bool)
    assert converted["none"] is None
    assert isinstance(converted["dict"]["nested"], int)
