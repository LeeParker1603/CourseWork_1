import os
import random
from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd
import pytest


@pytest.fixture(scope="session")
def test_data_dir():
    """Фикстура для пути к тестовым данным"""
    return os.path.join(os.path.dirname(__file__), "test_data")


@pytest.fixture
def sample_dataframe_100_rows():
    """Фикстура с 100 строками тестовых данных"""
    data = []
    base_date = datetime(2021, 12, 1)
    categories = ["Супермаркеты", "Рестораны", "Транспорт", "Развлечения"]

    for i in range(100):
        data.append(
            {
                "Дата операции": base_date + timedelta(days=random.randint(0, 30)),
                "Сумма операции": -random.randint(100, 10000),
                "Категория": random.choice(categories),
                "Описание": f"Тестовая транзакция {i}",
            }
        )

    return pd.DataFrame(data)


@pytest.fixture
def mock_environment():
    """Фикстура для настройки тестового окружения"""
    # Создаем необходимые директории
    os.makedirs("data/reports", exist_ok=True)
    os.makedirs("data/services", exist_ok=True)
    os.makedirs("data/responses", exist_ok=True)

    yield

    # Очистка после тестов (можно закомментировать при необходимости)
    # import shutil
    # shutil.rmtree("data/reports", ignore_errors=True)
    # shutil.rmtree("data/services", ignore_errors=True)
    # shutil.rmtree("data/responses", ignore_errors=True)


@pytest.fixture
def mock_logger():
    """Фикстура для мока логгера"""
    with patch("logging.Logger") as mock:
        yield mock
