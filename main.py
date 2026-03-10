from src.views import generate_main_page_response
import os


def main():
    """
    Основная функция для демонстрации работы
    """
    input_date = "15.12.2021"
    excel_file = "data/operations.xlsx"

    # Генерация ответа для главной страницы
    response = generate_main_page_response(input_date, excel_file)

    # Вывод результата
    print("=" * 50)
    print("JSON-ответ для главной страницы:")
    print("=" * 50)
    print(response)

    # Сохраняем результат в файл для проверки
    with open("src/response.json", "w", encoding="utf-8") as f:
        f.write(response)

    print("\nРезультат также сохранен в файл response.json")


if __name__ == "__main__":
    main()