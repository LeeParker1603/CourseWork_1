# Анализ банковских транзакций

## Описание проекта

Приложение для анализа банковских транзакций из Excel-файла. Генерирует JSON-данные для веб-страниц, формирует отчеты по категориям, дням недели и рабочим/выходным дням, а также предоставляет сервисы для анализа кешбэка, инвестиционной копилки и поиска транзакций.

## 1. Функциональность

### Веб-страницы
- **Главная страница** - приветствие, данные по картам, топ-5 транзакций, курсы валют и акций
- **Страница событий** - анализ расходов и поступлений с группировкой по категориям

### Сервисы
- **Анализ кешбэка** - расчет потенциального кешбэка по категориям за указанный месяц
- **Инвесткопилка** - расчет накоплений через округление трат
- **Простой поиск** - поиск транзакций по описанию или категории
- **Поиск по телефону** - поиск транзакций с номерами телефонов в описании
- **Поиск переводов физлицам** - поиск переводов с именами получателей

### Отчеты
- **Траты по категории** - анализ трат по выбранной категории за последние 3 месяца
- **Траты по дням недели** - средние траты в разрезе дней недели
- **Траты в рабочие/выходные дни** - сравнение трат в рабочие и выходные дни

## 2. Технологии

- **Python 3.11+** - основной язык программирования
- **Pandas** - обработка данных и Excel-файлов
- **Requests** - запросы к API для курсов валют и акций
- **Pytest** - тестирование
- **Logging** - логирование
- **NumPy** - математические операции
- **OpenPyXL** - работа с Excel файлами

---

## 3. Установка и запуск

### 3.1. Клонирование репозитория
```bash
git clone https://github.com/your-username/CourseWork_1.git
cd CourseWork_1
```

### 3.2. Создание виртуального окружения

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3.3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3.4. Подготовка данных
**Поместите файл ```operations.xls``` в папку ```data/```.**

### 3.5. Настройка пользовательских параметров 

Создайте файл ```user_settings.json в``` корне проекта:

```
{
  "user_currencies": ["USD", "EUR", "GBP"],
  "user_stocks": ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"]
}
```

### 3.6. Запуск приложения

```bash
python main.py
```

Результаты будут сохранены в папке data/:

 - ```data/responses/``` - JSON-ответы для веб-страниц

 - ```data/services/``` - результаты работы сервисов

 - ```data/reports/``` - сгенерированные отчеты


## 4. Структура проекта

```
CourseWork_1/
├── src/
│   ├── __init__.py
│   ├── views.py          # Генерация JSON для веб-страниц
│   ├── services.py       # Сервисы (кешбэк, инвесткопилка, поиск)
│   ├── reports.py        # Отчеты с декоратором сохранения
│   └── utils.py          # Вспомогательные функции
├── tests/
│   ├── test_services.py  # Тесты для сервисов
│   ├── test_reports.py   # Тесты для отчетов
│   ├── test_views.py     # Тесты для веб-страниц
│   ├── test_utils.py     # Тесты для утилит
│   └── conftest.py       # Общие фикстуры для тестов
├── data/                 # Папка для данных
│   ├── operations.xlsx   # Excel-файл с транзакциями
│   ├── responses/        # JSON-ответы от веб-страниц
│   ├── services/         # JSON-ответы от сервисов
│   └── reports/          # JSON-отчеты
├── user_settings.json    # Настройки пользователя
├── main.py               # Точка входа
├── create_test_data.py   # Генерация тестовых данных
├── requirements.txt      # Зависимости
├── pytest.ini            # Настройки pytest
├── .coveragerc           # Настройки покрытия кода
└── README.md             # Документация
```

## 5. Запуск тестов и проверка покрытия

### 5.1. Запуск всех тестов

```bash
pytest tests/ -v
```

### 5.2. Запуск конкретного теста

```bash
pytest tests/test_services.py::test_cashback_rounding -v
```

### 5.3. Проект покрыт модульными (unit) тестами на 87%

```
Name              Stmts   Miss  Cover
-------------------------------------
src\__init__.py       0      0   100%
src\reports.py      194     28    86%
src\services.py     190     27    86%
src\utils.py        235     26    89%
src\views.py        146     19    87%
-------------------------------------
TOTAL               765    100    87%


```

### 5.4. Проверка покрытия кода

```bash
# Базовый отчет
pytest tests/ --cov=src --cov-report=term

# Подробный отчет с пропущенными строками
pytest tests/ --cov=src --cov-report=term-missing

# HTML отчет
pytest tests/ --cov=src --cov-report=html
# Откройте htmlcov/index.html в браузере

# С проверкой минимального покрытия (80%)
```

## 6. Примеры использования
### 6.1. Генерация главной страницы
```python
from src.views import generate_main_page_response

response = generate_main_page_response('15.12.2021')
print(response)
```

### 6.2. Анализ кешбэка

```python
from src.services import analyze_cashback_categories
from src.utils import read_transactions_from_excel

transactions = read_transactions_from_excel('data/operations.xlsx')
result = analyze_cashback_categories(transactions, 2021, 12)
print(result)
```

### 6.3. Отчет по категории
```python
from src.reports import spending_by_category
from src.utils import read_transactions_from_excel

df = read_transactions_from_excel('data/operations.xlsx')
report = spending_by_category(df, 'Супермаркеты', '15.12.2021')
print(report)
```

## 7. Примеры JSON-ответов
### 7.1. Главная страница
```json
{
  "greeting": "Привет, Добрый день!",
  "date": "15.12.2021",
  "cards": [
    {
      "last_digits": "1234",
      "total_spent": 15500.50,
      "cashback": 310.01
    }
  ],
  "top_transactions": [
    {
      "date": "15.12.2021",
      "amount": 5500.00,
      "category": "Переводы",
      "description": "Перевод на карту другого банка"
    }
  ],
  "currency_rates": [
    {
      "currency": "USD",
      "rate": 92.45
    }
  ],
  "stock_prices": [
    {
      "stock": "AAPL",
      "price": 175.50
    }
  ]
}
```

### 7.2. Страница событий
```json
{
  "expenses": {
    "total_amount": 32101,
    "main": [
      {
        "category": "Супермаркеты",
        "amount": 17319
      },
      {
        "category": "Остальное",
        "amount": 2954
      }
    ],
    "transfers_and_cash": [
      {
        "category": "Наличные",
        "amount": 500
      },
      {
        "category": "Переводы",
        "amount": 200
      }
    ]
  },
  "income": {
    "total_amount": 54271,
    "main": [
      {
        "category": "Пополнение",
        "amount": 33000
      }
    ]
  }
}
```

### 7.3. Анализ кешбэка
```json
{
  "Супермаркеты": 15,
  "Фастфуд": 5,
  "Транспорт": 2,
  "Переводы": 50
}
```

## 8. Зависимости (requirements.txt)
```txt
# Основные зависимости
pandas>=3.0.0
numpy>=2.4.1
openpyxl>=3.1.0
requests>=2.32.0
python-dateutil>=2.9.0

# Для тестирования
pytest>=9.0.2
pytest-cov>=7.0.0
pytest-mock>=3.14.0

# Для линтинга (опционально)
pylint>=3.3.0
flake8>=7.1.0
black>=24.10.0
mypy>=1.14.0
12.1. Установка зависимостей
bash
pip install -r requirements.txt
12.2. Обновление библиотек
bash
# Обновить все библиотеки
pip install --upgrade -r requirements.txt

# Обновить конкретную библиотеку
pip install --upgrade pandas==3.0.0
```

## 13. Автор
Студент: Evgenia Gorobets - Beginner Python developer  
Курс: Python-разработчик  
Дата: march 2026  
Контакты: [leeparker1603@gmail.com](mailto:leeparker1603@gmail.com)
