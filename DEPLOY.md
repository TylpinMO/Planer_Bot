# 🚀 Развертывание PlanerBot на сервере

## 📋 Требования

- **OS:** Ubuntu 20.04+ / Debian 11+ / любой Linux с systemd
- **Python:** 3.9+
- **Git:** для получения обновлений
- **Права:** sudo для настройки systemd

## 🔧 Первоначальная установка

### 1. Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка необходимых пакетов
sudo apt install -y python3 python3-pip python3-venv git

# Создание пользователя для бота (опционально)
sudo useradd -m -s /bin/bash planerbot
sudo su - planerbot
```

### 2. Клонирование репозитория

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/PlanerBot.git
cd PlanerBot
```

### 3. Настройка окружения

```bash
# Создание виртуального окружения
python3 -m venv venv

# Активация
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

### 4. Конфигурация

```bash
# Копирование примера конфигурации
cp .env.example .env

# Редактирование конфигурации
nano .env
```

**Обязательно укажите:**

```env
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_IDS=your_telegram_id
DATABASE_URL=sqlite+aiosqlite:///planner.db
```

**Как получить BOT_TOKEN:**

1. Напишите @BotFather в Telegram
2. Команда `/newbot`
3. Следуйте инструкциям
4. Скопируйте токен

**Как узнать свой Telegram ID:**

1. Напишите @userinfobot
2. Скопируйте ID

### 5. Инициализация базы данных

```bash
# База данных создастся автоматически при первом запуске
python main.py
# Нажмите Ctrl+C для остановки после успешного запуска
```

## 🔄 Настройка автозапуска (systemd)

### 1. Создание сервиса

```bash
sudo nano /etc/systemd/system/planerbot.service
```

**Вставьте (замените YOUR_USER и /path/to на реальные):**

```ini
[Unit]
Description=PlanerBot - Telegram Task Manager
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/PlanerBot
Environment="PATH=/path/to/PlanerBot/venv/bin"
ExecStart=/path/to/PlanerBot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Пример для пользователя planerbot:**

```ini
[Unit]
Description=PlanerBot - Telegram Task Manager
After=network.target

[Service]
Type=simple
User=planerbot
WorkingDirectory=/home/planerbot/PlanerBot
Environment="PATH=/home/planerbot/PlanerBot/venv/bin"
ExecStart=/home/planerbot/PlanerBot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. Запуск сервиса

```bash
# Перезагрузка конфигурации systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable planerbot.service

# Запуск бота
sudo systemctl start planerbot.service

# Проверка статуса
sudo systemctl status planerbot.service
```

## 📊 Управление ботом

### Основные команды

```bash
# Статус
sudo systemctl status planerbot.service

# Запуск
sudo systemctl start planerbot.service

# Остановка
sudo systemctl stop planerbot.service

# Перезапуск
sudo systemctl restart planerbot.service

# Логи (в реальном времени)
sudo journalctl -u planerbot.service -f

# Последние 100 строк логов
sudo journalctl -u planerbot.service -n 100

# Логи за сегодня
sudo journalctl -u planerbot.service --since today
```

## 🔄 Обновление бота

### Автоматическое обновление

```bash
cd ~/PlanerBot
./update.sh
```

Скрипт автоматически:

- ✅ Создаст резервную копию базы данных
- ✅ Сохранит .env
- ✅ Скачает обновления с GitHub
- ✅ Обновит зависимости
- ✅ Применит миграции БД
- ✅ Перезапустит бота

### Ручное обновление

```bash
cd ~/PlanerBot

# Резервная копия БД
cp planner.db planner.db.backup

# Получение обновлений
git pull origin main

# Активация venv
source venv/bin/activate

# Обновление зависимостей
pip install -r requirements.txt

# Применение миграций (если есть)
python migrate_existing_db.py

# Перезапуск
sudo systemctl restart planerbot.service
```

## 🛠 Решение проблем

### Бот не запускается

```bash
# Проверка логов
sudo journalctl -u planerbot.service -n 50

# Проверка конфигурации
cat .env

# Ручной запуск для отладки
source venv/bin/activate
python main.py
```

### База данных повреждена

```bash
# Восстановление из резервной копии
cd ~/PlanerBot
cp planner.db.backup.ДАТА planner.db
sudo systemctl restart planerbot.service
```

### Проблемы с правами

```bash
# Проверка владельца файлов
ls -la ~/PlanerBot

# Исправление владельца
sudo chown -R planerbot:planerbot ~/PlanerBot
```

## 📁 Структура проекта

```
PlanerBot/
├── .env                      # Конфигурация (НЕ коммитить!)
├── .env.example              # Пример конфигурации
├── .gitignore               # Git исключения
├── README.md                # Документация
├── main.py                  # Точка входа
├── config.py                # Загрузка конфигурации
├── requirements.txt         # Зависимости Python
├── update.sh                # Скрипт обновления
├── migrate_existing_db.py   # Миграции БД
├── planner.db              # База данных SQLite
├── bot/                    # Модуль бота
│   ├── __init__.py
│   ├── handlers/           # Обработчики команд
│   └── keyboards/          # Клавиатуры
├── database/               # Модуль БД
│   ├── __init__.py
│   ├── models.py          # Модели SQLAlchemy
│   └── crud.py            # Операции с БД
└── services/              # Сервисы
    ├── __init__.py
    ├── notifications.py   # Уведомления
    └── payments.py        # Платежи
```

## 🔒 Безопасность

### Важно!

1. **Никогда не коммитьте .env в Git**
2. **Регулярно делайте резервные копии БД**
3. **Храните резервные копии отдельно от сервера**
4. **Используйте firewall (ufw)**

### Настройка firewall

```bash
# Разрешить SSH
sudo ufw allow 22

# Включить firewall
sudo ufw enable
```

## 📊 Мониторинг

### Автоматическая проверка здоровья

Создайте скрипт проверки:

```bash
nano ~/check_bot.sh
```

```bash
#!/bin/bash
if ! systemctl is-active --quiet planerbot.service; then
    echo "Bot is down! Restarting..."
    systemctl restart planerbot.service
fi
```

Добавьте в crontab (каждые 5 минут):

```bash
crontab -e
# Добавьте строку:
*/5 * * * * /home/planerbot/check_bot.sh
```

## 📞 Поддержка

При проблемах проверьте:

1. Логи: `sudo journalctl -u planerbot.service -f`
2. Статус: `sudo systemctl status planerbot.service`
3. Конфигурацию: `.env`
4. Права доступа: `ls -la ~/PlanerBot`

## ✅ Готово!

Бот развернут и работает! 🎉

Проверьте:

- Напишите боту `/start`
- Выдайте себе админку: `/give_premium_forever YOUR_ID`
- Создайте список задач
- Настройте уведомления
