#!/bin/bash

# Скрипт для запуска Planer_Bot в фоновом режиме

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Проверка, не запущен ли уже бот
if [ -f bot.pid ]; then
    PID=$(cat bot.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "❌ Бот уже запущен (PID: $PID)"
        exit 1
    fi
fi

# Активация виртуального окружения
source venv/bin/activate

# Запуск бота в фоне
nohup python3 main.py > /dev/null 2>&1 &
PID=$!

# Сохранение PID
echo $PID > bot.pid

echo "✅ Бот запущен (PID: $PID)"
echo "📋 Смотреть логи: tail -f logs/bot.log"
echo "🛑 Остановить: kill $PID"
