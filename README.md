# Сервис объявлений (FastAPI)

REST API для управления пользователями и объявлениями с JWT-аутентификацией и разделением ролей (user/admin)

## Требования

- Python 3.10-3.13
- SQLite

## Установка

~~~
git clone <репозиторий>
cd <папка проекта>
python -m venv venv
# Активируйте окружение:
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
# Запуск
uvicorn main:app --reload