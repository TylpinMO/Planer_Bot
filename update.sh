#!/bin/bash
# Скрипт обновления бота с GitHub без потери данных

set -e  # Остановка при ошибке

echo "🔄 Начало обновления PlanerBot..."

# Сохраняем текущую базу данных
if [ -f "planner.db" ]; then
    echo "💾 Создание резервной копии базы данных..."
    cp planner.db planner.db.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ Резервная копия создана"
fi

# Сохраняем .env
if [ -f ".env" ]; then
    echo "💾 Создание резервной копии .env..."
    cp .env .env.backup
    echo "✅ .env сохранен"
fi

# Получаем обновления из GitHub
echo "📥 Получение обновлений из GitHub..."
git fetch origin
git pull origin main

# Восстанавливаем .env
if [ -f ".env.backup" ]; then
    echo "🔧 Восстановление .env..."
    mv .env.backup .env
    echo "✅ .env восстановлен"
fi

# Активируем виртуальное окружение
if [ -d "venv" ]; then
    echo "🔧 Активация виртуального окружения..."
    source venv/bin/activate
else
    echo "⚠️  Виртуальное окружение не найдено. Создание..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Обновляем зависимости
echo "📦 Установка/обновление зависимостей..."
pip install -r requirements.txt --quiet

# Применяем миграции если нужно
if [ -f "migrate_existing_db.py" ]; then
    echo "🔄 Применение миграций к существующей базе данных..."
    python migrate_existing_db.py
    echo "✅ Миграции применены"
fi

# Перезапускаем бота (если используется systemd)
if systemctl is-active --quiet planerbot.service; then
    echo "🔄 Перезапуск сервиса..."
    sudo systemctl restart planerbot.service
    echo "✅ Бот перезапущен"
else
    echo "⚠️  Systemd сервис не найден. Перезапустите бота вручную."
fi

echo ""
echo "✅ Обновление завершено успешно!"
echo "📊 Для проверки статуса: sudo systemctl status planerbot.service"
echo "📋 Для просмотра логов: sudo journalctl -u planerbot.service -f"
