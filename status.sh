#!/bin/bash

# Скрипт для проверки статуса Planer_Bot

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

if [ ! -f bot.pid ]; then
    echo "❌ Бот не запущен (файл bot.pid не найден)"
    exit 1
fi

PID=$(cat bot.pid)

if ps -p $PID > /dev/null 2>&1; then
    echo "✅ Бот работает (PID: $PID)"
    echo ""
    ps -fp $PID
    echo ""
    echo "📋 Последние 10 строк лога:"
    tail -n 10 logs/bot.log
else
    echo "❌ Бот не запущен (PID $PID не существует)"
    rm bot.pid
    exit 1
fi
