#!/bin/bash
# Скрипт первоначального развертывания PlanerBot на сервере

set -e  # Остановка при ошибке

echo "🚀 Развертывание PlanerBot..."
echo ""

# Проверка наличия Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не установлен. Установите: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

echo "✅ Python 3 найден: $(python3 --version)"

# Проверка наличия Git
if ! command -v git &> /dev/null; then
    echo "❌ Git не установлен. Установите: sudo apt install git"
    exit 1
fi

echo "✅ Git найден: $(git --version)"
echo ""

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
    echo "✅ Виртуальное окружение создано"
else
    echo "ℹ️  Виртуальное окружение уже существует"
fi

# Активация виртуального окружения
echo "🔧 Активация виртуального окружения..."
source venv/bin/activate

# Установка зависимостей
echo "📦 Установка зависимостей..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "✅ Зависимости установлены"

# Проверка наличия .env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo ""
        echo "⚙️  Настройка конфигурации..."
        cp .env.example .env
        echo "✅ Создан файл .env из .env.example"
        echo ""
        echo "⚠️  ВАЖНО! Отредактируйте файл .env:"
        echo "   nano .env"
        echo ""
        echo "   Укажите:"
        echo "   - BOT_TOKEN=ваш_токен_от_@BotFather"
        echo "   - ADMIN_IDS=ваш_telegram_id"
        echo ""
        echo "   Узнать свой Telegram ID: @userinfobot"
        echo ""
        read -p "Нажмите Enter после редактирования .env..."
    else
        echo "❌ Файл .env.example не найден!"
        exit 1
    fi
else
    echo "ℹ️  Файл .env уже существует"
fi

# Инициализация базы данных
echo ""
echo "🗄️  Инициализация базы данных..."
python -c "
import asyncio
from database.models import init_db
asyncio.run(init_db())
print('✅ База данных инициализирована')
"

# Применение миграций для существующих БД
if [ -f "migrate_existing_db.py" ]; then
    echo "🔄 Проверка и применение миграций..."
    python migrate_existing_db.py
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Развертывание завершено успешно!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Следующие шаги:"
echo ""
echo "1️⃣  Тестовый запуск:"
echo "   python main.py"
echo "   (Нажмите Ctrl+C для остановки)"
echo ""
echo "2️⃣  Настройка автозапуска (systemd):"
echo "   Смотрите инструкцию в DEPLOY.md"
echo ""
echo "3️⃣  После запуска бота:"
echo "   - Напишите боту /start"
echo "   - Узнайте свой ID через @userinfobot"
echo "   - Выдайте себе премиум: /give_premium_forever YOUR_ID"
echo ""
echo "📚 Полная документация: DEPLOY.md"
echo "🔄 Обновление бота: ./update.sh"
echo ""
