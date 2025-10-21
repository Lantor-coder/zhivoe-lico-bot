# Используем стабильный Python 3.11
FROM python:3.11-slim

# Устанавливаем зависимости системы
RUN apt-get update && apt-get install -y build-essential

# Копируем файлы проекта
WORKDIR /app
COPY . .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Указываем порт, который слушает Render
ENV PORT=10000
EXPOSE 10000

# Запуск бота
CMD ["python", "bot.py"]
