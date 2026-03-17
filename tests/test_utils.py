import json
from datetime import datetime
from unittest.mock import MagicMock, mock_open, patch

import numpy as np
import pandas as pd

from src.utils import (
    calculate_card_data,
    calculate_top_transactions,
    convert_numpy_types,
    filter_transactions_by_date,
    get_currency_rates,
    get_stock_prices,
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
        assert result["user_currencies"] == ["USD", "EUR"]
        assert result["user_stocks"] == ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"]


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
    assert result["user_currencies"] == ["USD", "EUR"]

    assert mock_exists.call_count > 0
    mock_open.assert_called()
    mock_json_load.assert_called()


def test_get_stock_prices() -> None:
    """Тест получения цен акций"""
    result = get_stock_prices(["AAPL", "INVALID"])
    assert len(result) == 2
    assert result[0]["stock"] == "AAPL"
    assert result[0]["price"] > 0


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
