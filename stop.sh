#!/bin/bash

# Скрипт для остановки Planer_Bot

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

if [ ! -f bot.pid ]; then
    echo "❌ Файл bot.pid не найден"
    exit 1
fi

PID=$(cat bot.pid)

if ! ps -p $PID > /dev/null 2>&1; then
    echo "❌ Процесс с PID $PID не запущен"
    rm bot.pid
    exit 1
fi

echo "🛑 Останавливаю бот (PID: $PID)..."
kill $PID

# Ожидание завершения
sleep 2

if ps -p $PID > /dev/null 2>&1; then
    echo "⚠️  Процесс не завершился, отправляю SIGKILL..."
    kill -9 $PID
fi

rm bot.pid
echo "✅ Бот остановлен"
