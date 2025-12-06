# 📝 Шпаргалка по развертыванию

## 🚀 На сервере (первый раз)

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/YOUR_USERNAME/PlanerBot.git
cd PlanerBot

# 2. Создайте venv и установите зависимости
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Настройте .env
cp .env.example .env
nano .env
# Укажите: BOT_TOKEN и ADMIN_IDS

# 4. Создайте systemd сервис
sudo nano /etc/systemd/system/planerbot.service
```

**Содержимое сервиса (замените пути):**

```ini
[Unit]
Description=PlanerBot
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

```bash
# 5. Запустите сервис
sudo systemctl daemon-reload
sudo systemctl enable planerbot.service
sudo systemctl start planerbot.service

# 6. Проверьте
sudo systemctl status planerbot.service
```

## 🔄 Обновление (каждый раз)

```bash
cd PlanerBot
./update.sh
```

Готово! Скрипт сам:

- Создаст backup БД
- Скачает обновления
- Обновит зависимости
- Применит миграции
- Перезапустит бота

## 📊 Полезные команды

```bash
# Статус
sudo systemctl status planerbot.service

# Логи в реальном времени
sudo journalctl -u planerbot.service -f

# Перезапуск
sudo systemctl restart planerbot.service

# Остановка
sudo systemctl stop planerbot.service
```

## 🎯 После развертывания

1. Напишите боту `/start`
2. Узнайте свой ID через @userinfobot
3. Выдайте себе админку: `/give_premium_forever YOUR_ID`
4. Готово! 🎉
