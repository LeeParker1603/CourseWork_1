from datetime import datetime, timedelta
from unittest.mock import MagicMock, PropertyMock, mock_open, patch

import pandas as pd
import pytest

from src.reports import (
    detailed_category_analysis,
    filter_last_3_months,
    parse_date,
    save_report,
    spending_by_category,
    spending_by_weekday,
    spending_by_workday,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_dataframe():
    """Фикстура с тестовым DataFrame"""
    dates = [
        datetime(2021, 12, 15),
        datetime(2021, 12, 10),
        datetime(2021, 11, 15),
        datetime(2021, 10, 15),
    ]

    return pd.DataFrame(
        {
            "Дата операции": dates,
            "Сумма операции": [-1500, -800, -500, -200],
            "Категория": ["Супермаркеты", "Супермаркеты", "Фастфуд", "Транспорт"],
            "Описание": ["Пятерочка", "Перекресток", "McDonalds", "Такси"],
        }
    )


@pytest.fixture
def dataframe_with_various_days():
    """Фикстура с транзакциями в разные дни недели"""
    base_date = datetime(2021, 12, 1)  # среда

    dates = [
        base_date,  # среда
        base_date + timedelta(days=1),  # четверг
        base_date + timedelta(days=2),  # пятница
        base_date + timedelta(days=3),  # суббота (выходной)
        base_date + timedelta(days=4),  # воскресенье (выходной)
    ]

    return pd.DataFrame(
        {
            "Дата операции": dates,
            "Сумма операции": [-100, -200, -300, -400, -500],
            "Категория": ["Тест"] * 5,
            "Описание": ["Тест"] * 5,
        }
    )


# ============================================================================
# ТЕСТЫ ВСПОМОГАТЕЛЬНЫХ ФУНКЦИЙ
# ============================================================================


def test_parse_date_with_string() -> None:
    """Тест парсинга даты из строки"""
    date = parse_date("15.12.2021")
    assert date.year == 2021
    assert date.month == 12
    assert date.day == 15


def test_parse_date_with_datetime_string() -> None:
    """Тест парсинга даты с временем"""
    date = parse_date("15.12.2021 14:30:00")
    assert date.year == 2021
    assert date.month == 12
    assert date.day == 15
    assert date.hour == 14
    assert date.minute == 30


def test_parse_date_with_none() -> None:
    """Тест парсинга None (должна вернуться текущая дата)"""
    date = parse_date(None)
    now = datetime.now()
    assert date.year == now.year
    assert date.month == now.month
    assert date.day == now.day


@patch("src.reports.logger")
def test_parse_date_invalid_format(mock_logger) -> None:
    """Тест парсинга неверного формата"""
    date = parse_date("не дата")
    assert isinstance(date, datetime)
    mock_logger.error.assert_called()


def test_filter_last_3_months(sample_dataframe) -> None:
    """Тест фильтрации за последние 3 месяца"""
    end_date = datetime(2021, 12, 15)
    filtered = filter_last_3_months(sample_dataframe, end_date)

    # Должны быть все транзакции за последние 90 дней
    # В sample_dataframe:
    # - 2021-12-15 (0 дней назад)
    # - 2021-12-10 (5 дней назад)
    # - 2021-11-15 (30 дней назад)
    # - 2021-10-15 (61 день назад) - тоже входит в 90 дней!
    assert len(filtered) == 4  # Все транзакции входят в 90-дневный период


# ============================================================================
# ТЕСТЫ ДЕКОРАТОРА
# ============================================================================


@patch("os.makedirs")
@patch("builtins.open", new_callable=mock_open)
def test_save_report_decorator_with_mock_open(mock_file, mock_makedirs) -> None:
    """Тест декоратора с моком open и makedirs"""

    @save_report()
    def test_func():
        return {"test": "data"}

    result = test_func()

    mock_makedirs.assert_called_once()
    mock_file.assert_called_once()
    assert result == {"test": "data"}


@patch("os.makedirs")
@patch("builtins.open", new_callable=mock_open)
def test_save_report_with_custom_filename(mock_file, mock_makedirs) -> None:
    """Тест декоратора с указанным именем файла"""

    @save_report("custom_test.json")
    def test_func():
        return {"custom": "data"}

    result = test_func()

    mock_makedirs.assert_called_once()
    mock_file.assert_called_once()
    assert result == {"custom": "data"}


@patch("src.reports.logger")
@patch("os.makedirs")
@patch("builtins.open")
def test_save_report_error_handling(mock_open, mock_makedirs, mock_logger) -> None:
    """Тест обработки ошибок при сохранении"""
    mock_open.side_effect = PermissionError("Нет прав на запись")

    @save_report()
    def test_func():
        return {"test": "data"}

    result = test_func()

    mock_logger.error.assert_called_once()
    assert result == {"test": "data"}


# ============================================================================
# ТЕСТЫ ОТЧЕТА ПО КАТЕГОРИЯМ
# ============================================================================


@patch("src.reports.parse_date")
def test_spending_by_category_with_mocked_date(mock_parse_date, sample_dataframe) -> None:
    """Тест с моком функции parse_date"""
    mock_parse_date.return_value = datetime(2021, 12, 15)

    result = spending_by_category(sample_dataframe, "Супермаркеты")

    mock_parse_date.assert_called_once()
    assert not result.empty


@patch("src.reports.filter_last_3_months")
def test_spending_by_category_with_mocked_filter(mock_filter, sample_dataframe) -> None:
    """Тест с моком функции filter_last_3_months"""
    mock_filter.return_value = sample_dataframe.iloc[:2]

    result = spending_by_category(sample_dataframe, "Супермаркеты", "15.12.2021")

    mock_filter.assert_called_once()
    assert len(result) == 1  # одна запись (сумма за месяц)


def test_spending_by_category_basic(sample_dataframe) -> None:
    """Базовый тест отчета по категориям"""
    result = spending_by_category(sample_dataframe, "Супермаркеты", "15.12.2021")

    assert isinstance(result, pd.DataFrame)
    assert not result.empty
    assert "Месяц" in result.columns
    assert "Сумма" in result.columns
    assert "Количество" in result.columns


def test_spending_by_category_correct_amount(sample_dataframe) -> None:
    """Тест правильности расчета сумм"""
    result = spending_by_category(sample_dataframe, "Супермаркеты", "15.12.2021")

    # Должны быть две транзакции: 1500 + 800 = 2300
    total = result["Сумма"].sum()
    assert total == 2300


def test_spending_by_category_not_found(sample_dataframe) -> None:
    """Тест для несуществующей категории"""
    result = spending_by_category(sample_dataframe, "Несуществующая", "15.12.2021")

    assert isinstance(result, pd.DataFrame)
    assert result.empty


@patch("pandas.DataFrame.empty", new_callable=PropertyMock)
def test_spending_by_category_empty_dataframe(mock_empty, sample_dataframe) -> None:
    """Тест с пустым DataFrame"""
    mock_empty.return_value = True

    result = spending_by_category(sample_dataframe, "Супермаркеты", "15.12.2021")

    assert result.empty
    mock_empty.assert_called()


# ============================================================================
# ТЕСТЫ ОТЧЕТА ПО ДНЯМ НЕДЕЛИ
# ============================================================================


def test_spending_by_weekday_basic(dataframe_with_various_days) -> None:
    """Базовый тест отчета по дням недели"""
    result = spending_by_weekday(dataframe_with_various_days, "15.12.2021")

    assert isinstance(result, pd.DataFrame)
    assert not result.empty
    assert "День недели" in result.columns
    assert "Средние траты" in result.columns
    assert "Всего трат" in result.columns
    assert "Количество" in result.columns


def test_spending_by_weekday_names(dataframe_with_various_days) -> None:
    """Тест названий дней недели"""
    result = spending_by_weekday(dataframe_with_various_days, "15.12.2021")

    expected_days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    for day in result["День недели"]:
        assert day in expected_days


def test_spending_by_weekday_calculation(dataframe_with_various_days) -> None:
    """Тест расчета средних значений"""
    result = spending_by_weekday(dataframe_with_various_days, "15.12.2021")

    for _, row in result.iterrows():
        if row["Количество"] > 0:
            expected_avg = row["Всего трат"] / row["Количество"]
            assert abs(row["Средние траты"] - expected_avg) < 0.01


@patch("src.reports.filter_last_3_months")
def test_spending_by_weekday_with_mocked_filter(mock_filter, dataframe_with_various_days) -> None:
    """Тест с моком фильтрации"""
    mock_filter.return_value = dataframe_with_various_days

    result = spending_by_weekday(dataframe_with_various_days, "20.12.2021")

    mock_filter.assert_called_once()
    assert len(result) == 5  # количество уникальных дней в тестовых данных


@patch("pandas.DataFrame.groupby")
def test_spending_by_weekday_groupby_mocked(mock_groupby, dataframe_with_various_days) -> None:
    """Тест с моком groupby"""
    mock_group = MagicMock()
    mock_group.agg.return_value = mock_group.agg.return_value = pd.DataFrame(
        {"Всего трат": [100, 200, 300, 400, 500], "Средние траты": [10, 20, 30, 40, 50], "Количество": [1, 1, 1, 1, 1]}
    )

    mock_groupby.return_value = mock_group

    result = spending_by_weekday(dataframe_with_various_days, "15.12.2021")

    mock_groupby.assert_called()
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 5  # количество строк в нашем моке


# ============================================================================
# ТЕСТЫ ОТЧЕТА ПО РАБОЧИМ/ВЫХОДНЫМ ДНЯМ
# ============================================================================


def test_spending_by_workday_basic(dataframe_with_various_days) -> None:
    """Базовый тест отчета по рабочим/выходным дням"""
    result = spending_by_workday(dataframe_with_various_days, "15.12.2021")

    assert isinstance(result, pd.DataFrame)
    assert not result.empty
    assert "Тип дня" in result.columns
    assert "Средние траты" in result.columns
    assert "Всего трат" in result.columns
    assert "Количество" in result.columns


def test_spending_by_workday_types(dataframe_with_various_days) -> None:
    """Тест типов дней"""
    result = spending_by_workday(dataframe_with_various_days, "15.12.2021")

    day_types = result["Тип дня"].values
    assert "Рабочий" in day_types
    assert "Выходной" in day_types


@patch("src.reports.filter_last_3_months")
def test_spending_by_workday_with_mocked_filter(mock_filter, dataframe_with_various_days) -> None:
    """Тест с моком фильтрации"""
    mock_filter.return_value = dataframe_with_various_days

    result = spending_by_workday(dataframe_with_various_days, "20.12.2021")

    mock_filter.assert_called_once()
    assert len(result) == 2  # рабочие и выходные


# ============================================================================
# ТЕСТЫ ДЕТАЛЬНОГО АНАЛИЗА
# ============================================================================


def test_detailed_analysis_structure(sample_dataframe) -> None:
    """Тест структуры детального анализа"""
    result = detailed_category_analysis(sample_dataframe, "Супермаркеты", "15.12.2021")

    assert isinstance(result, dict)
    assert "category" in result
    assert "period" in result
    assert "total_spent" in result
    assert "transactions_count" in result
    assert "average_transaction" in result
    assert "max_transaction" in result
    assert "min_transaction" in result
    assert "by_month" in result


def test_detailed_analysis_values(sample_dataframe) -> None:
    """Тест значений детального анализа"""
    result = detailed_category_analysis(sample_dataframe, "Супермаркеты", "15.12.2021")

    assert result["category"] == "Супермаркеты"
    assert result["total_spent"] == 2300
    assert result["transactions_count"] == 2
    assert result["average_transaction"] == 1150
    assert result["max_transaction"] == 1500
    assert result["min_transaction"] == 800


# ============================================================================
# ТЕСТЫ С ПРОДВИНУТЫМИ МОКАМИ
# ============================================================================


@patch.multiple(
    "src.reports",
    parse_date=MagicMock(return_value=datetime.now()),
    filter_last_3_months=MagicMock(return_value=pd.DataFrame()),
)
def test_multiple_mocks_for_reports(sample_dataframe) -> None:
    """Тест с несколькими моками для отчетов"""
    result = spending_by_category(sample_dataframe, "Супермаркеты", "15.12.2021")

    assert isinstance(result, pd.DataFrame)


@patch("builtins.open", new_callable=mock_open)
@patch("json.dump")
def test_json_serialization_with_mocks(mock_json_dump) -> None:
    """Тест сериализации в JSON с моками"""

    @save_report("test.json")
    def test_func():
        return {"test": "data"}

    test_func()

    mock_json_dump.assert_called_once()


# ============================================================================
# ТЕСТЫ С ИСПОЛЬЗОВАНИЕМ wraps
# ============================================================================


def test_parse_date_with_wraps() -> None:
    """Тест с wraps для функции parse_date"""
    with patch("src.reports.parse_date", wraps=parse_date) as mock_parse:
        result = mock_parse("15.12.2021")

        assert result.year == 2021
        assert result.month == 12
        assert result.day == 15
        mock_parse.assert_called_once_with("15.12.2021")


def test_filter_last_3_months_with_wraps(sample_dataframe) -> None:
    """Тест с wraps для filter_last_3_months"""
    with patch("src.reports.filter_last_3_months", wraps=filter_last_3_months) as mock_filter:
        result = mock_filter(sample_dataframe, datetime(2021, 12, 15))

        assert not result.empty

        # Проверяем, что все даты в пределах 90 дней
        end_date = datetime(2021, 12, 15)
        start_date = end_date - timedelta(days=90)

        for date in result["Дата операции"]:
            assert date >= start_date
            assert date <= end_date

        mock_filter.assert_called_once_with(sample_dataframe, datetime(2021, 12, 15))


# ============================================================================
# ПАРАМЕТРИЗОВАННЫЕ ТЕСТЫ
# ============================================================================


@pytest.mark.parametrize(
    "category,expected_count,expected_sum",
    [
        ("Супермаркеты", 2, 2300),
        ("Фастфуд", 1, 500),
        ("Транспорт", 1, 200),
    ],
)
def test_spending_by_category_param(sample_dataframe, category, expected_count, expected_sum) -> None:
    """Параметризованный тест трат по категориям"""
    result = spending_by_category(sample_dataframe, category, "15.12.2021")

    assert not result.empty
    assert result["Количество"].sum() == expected_count
    assert result["Сумма"].sum() == expected_sum


# ============================================================================
# ТЕСТЫ ОБРАБОТКИ ОШИБОК
# ============================================================================


@patch("src.reports.filter_last_3_months")
def test_filter_error_handling(mock_filter, sample_dataframe) -> None:
    """Тест обработки ошибки в фильтре"""
    mock_filter.side_effect = Exception("Ошибка фильтрации")

    result = spending_by_category(sample_dataframe, "Супермаркеты", "15.12.2021")

    assert result.empty


@patch("src.reports.logger")
@patch("src.reports.filter_last_3_months")
def test_error_logging(mock_filter, mock_logger, sample_dataframe) -> None:
    """Тест логирования ошибок"""
    mock_filter.side_effect = Exception("Тестовая ошибка")

    spending_by_category(sample_dataframe, "Супермаркеты", "15.12.2021")

    mock_logger.error.assert_called()


def test_parse_date_with_various_formats() -> None:
    """Тест парсинга разных форматов дат"""
    date1 = parse_date("15.12.2021")
    date2 = parse_date("2021-12-15")
    date3 = parse_date("15.12.2021 14:30:00")

    assert date1.year == 2021
    assert date2.year == 2021
    assert date3.hour == 14


def test_filter_last_3_months_with_no_date_column() -> None:
    """Тест фильтрации без колонки даты"""
    df = pd.DataFrame({"test": [1, 2, 3]})
    result = filter_last_3_months(df, datetime.now())
    assert result.empty


def test_spending_by_category_with_all_categories() -> None:
    """Тест отчета по категориям со всеми категориями"""
    df = pd.DataFrame(
        {
            "Дата операции": [datetime.now()] * 10,
            "Сумма операции": [-100] * 10,
            "Категория": [f"Категория {i}" for i in range(10)],
            "Описание": ["test"] * 10,
        }
    )
    result = spending_by_category(df, "Категория 1")
    assert not result.empty


def test_spending_by_weekday_with_single_transaction() -> None:
    """Тест отчета по дням недели с одной транзакцией"""
    df = pd.DataFrame(
        {
            "Дата операции": [datetime(2021, 12, 15)],
            "Сумма операции": [-100],
            "Категория": ["test"],
            "Описание": ["test"],
        }
    )
    result = spending_by_weekday(df, "15.12.2021")
    assert len(result) == 1
    assert result.iloc[0]["Количество"] == 1


def test_detailed_category_analysis_with_no_expenses() -> None:
    """Тест детального анализа без расходов"""
    df = pd.DataFrame(
        {
            "Дата операции": [datetime(2021, 12, 15)],
            "Сумма операции": [1000],  # поступление
            "Категория": ["Супермаркеты"],
            "Описание": ["test"],
        }
    )
    result = detailed_category_analysis(df, "Супермаркеты", "15.12.2021")
    assert result["total_spent"] == 0
    assert result["transactions_count"] == 0


@patch("src.reports.logger")
def test_spending_by_category_error_handling(mock_logger) -> None:
    """Тест обработки ошибок в отчете по категориям"""
    df = pd.DataFrame({"wrong_column": [1, 2, 3]})
    result = spending_by_category(df, "test", "15.12.2021")
    assert result.empty
    mock_logger.error.assert_called()
