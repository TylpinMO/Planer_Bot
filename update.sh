#!/bin/bash
# Скрипт обновления бота с GitHub без потери данных

set -e  # Остановка при ошибке

echo "🔄 Начало обновления PlanerBot..."

# Получаем обновления из GitHub
echo "📥 Получение обновлений из GitHub..."
git fetch origin
git pull origin main

echo ""
echo "🔧 Применение обновлений..."
echo ""

# Сохраняем текущую базу данных
if [ -f "planner.db" ]; then
    echo "💾 Создание резервной копии базы данных..."
    cp planner.db planner.db.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ Резервная копия создана"
    
    # Удаляем старые бэкапы, оставляя последние 5
    backup_count=$(ls -1 planner.db.backup* 2>/dev/null | wc -l)
    if [ "$backup_count" -gt 5 ]; then
        echo "🧹 Удаление старых бэкапов (оставляем последние 5)..."
        ls -t planner.db.backup* | tail -n +6 | xargs rm -f
        echo "✅ Старые бэкапы удалены"
    fi
fi

# Сохраняем .env
if [ -f ".env" ]; then
    echo "💾 Создание резервной копии .env..."
    cp .env .env.backup
    echo "✅ .env сохранен"
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

echo ""
echo "✅ Обновление завершено успешно!"
echo ""
echo "📋 Для перезапуска бота:"
echo "   1. Остановите бота: tmux attach -t planerbot, затем Ctrl+C"
echo "   2. Запустите заново: python main.py"
echo "   3. Отключитесь: Ctrl+B, затем D"
echo ""
echo "📊 Просмотр логов:"
echo "   tail -f logs/bot.log          # В реальном времени"
echo "   less logs/bot.log              # Скроллинг"
echo "   grep ERROR logs/bot.log        # Только ошибки"
