# 📋 Шпаргалка по работе с логами

## 🔍 Просмотр логов на сервере

### Основные команды:

```bash
# 1. Последние 50 строк
tail -50 logs/bot.log

# 2. Реальное время (live monitoring)
tail -f logs/bot.log

# 3. Поиск ошибок
grep -i error logs/bot.log

# 4. Только последние ошибки
grep -i error logs/bot.log | tail -20

# 5. Скроллинг через less (можно листать)
less logs/bot.log
# / - поиск, n - следующее, q - выход

# 6. Поиск с контекстом (3 строки до и после)
grep -C 3 -i "error" logs/bot.log

# 7. Все критичные проблемы
grep -E "ERROR|CRITICAL|Exception" logs/bot.log

# 8. Статистика по уровням логов
grep -o "INFO\|WARNING\|ERROR\|CRITICAL" logs/bot.log | sort | uniq -c
```

### Ротированные файлы:

```bash
# Посмотреть все лог-файлы
ls -lh logs/

# bot.log - текущий
# bot.log.1 - предыдущий
# bot.log.2 - ещё старше
# и т.д. до bot.log.5

# Поиск во всех ротированных логах
grep -i "error" logs/bot.log*
```

### Через systemd (дополнительно):

```bash
# Логи сервиса (если используется systemd)
journalctl -u planerbot.service -f        # Реальное время
journalctl -u planerbot.service -n 100    # Последние 100 строк
journalctl -u planerbot.service --since "1 hour ago"
journalctl -u planerbot.service --since today
```

## 🚨 Типичные проблемы и их поиск

### 1. Telegram API ошибки

```bash
grep -i "telegram.*error" logs/bot.log | tail -10
```

### 2. Ошибки базы данных

```bash
grep -i "database\|sqlalchemy" logs/bot.log | grep -i error
```

### 3. Ошибки уведомлений

```bash
grep "check_notifications\|NotificationService" logs/bot.log | grep -i error
```

### 4. Последняя критичная ошибка с полным traceback

```bash
# Найти последний ERROR и показать 20 строк после него
grep -A 20 "ERROR" logs/bot.log | tail -25
```

### 5. Активность по времени

```bash
# Все записи за последний час (примерно)
awk '$0 ~ /2024-12-20 [0-9]{2}:[0-9]{2}/' logs/bot.log | tail -50
```

## 📊 Мониторинг

### Проверить, что бот работает:

```bash
# 1. Статус сервиса
sudo systemctl status planerbot.service

# 2. Последняя активность в логах
tail -5 logs/bot.log

# 3. Проверка процесса
ps aux | grep "python.*main.py"

# 4. Использование ресурсов
top -p $(pgrep -f "python.*main.py")
```

### Размер логов:

```bash
# Проверить размер
du -h logs/

# Если логи слишком большие - очистить старые
rm logs/bot.log.[3-5]
```

## 🔧 Полезные алиасы (добавить в ~/.bashrc):

```bash
# Добавьте эти строки в ~/.bashrc на сервере:
alias botlogs='tail -f ~/PlanerBot/logs/bot.log'
alias boterrors='grep -i error ~/PlanerBot/logs/bot.log | tail -20'
alias botstatus='sudo systemctl status planerbot.service'
alias botrestart='sudo systemctl restart planerbot.service'

# После добавления выполните:
source ~/.bashrc

# Теперь можно использовать:
# botlogs     - смотреть логи в реальном времени
# boterrors   - посмотреть последние ошибки
# botstatus   - статус бота
# botrestart  - перезапуск бота
```

## 📱 Уведомления об ошибках (опционально)

### Настроить алерты в Telegram:

```bash
# Скрипт для отправки критичных ошибок в Telegram
# /path/to/alert.sh

#!/bin/bash
BOT_TOKEN="your_bot_token"
CHAT_ID="your_chat_id"
LOG_FILE="/path/to/PlanerBot/logs/bot.log"

tail -f "$LOG_FILE" | while read line
do
    if echo "$line" | grep -qi "critical\|exception"; then
        MESSAGE="🚨 CRITICAL ERROR: $line"
        curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" \
            -d chat_id="$CHAT_ID" \
            -d text="$MESSAGE" > /dev/null
    fi
done
```

## 💡 Tips

1. **Используйте `less`** вместо `cat` для больших файлов
2. **Комбинируйте команды** через pipe (|)
3. **Сохраняйте важные логи**: `grep -i error logs/bot.log > errors.txt`
4. **Регулярно проверяйте размер**: `du -h logs/`
5. **Используйте `screen` или `tmux`** для долгих tail -f сессий

## 🎯 Типичный workflow отладки:

```bash
# 1. Зайти на сервер
ssh user@server

# 2. Проверить статус
sudo systemctl status planerbot.service

# 3. Если есть проблемы - смотрим последние ошибки
grep -i error logs/bot.log | tail -20

# 4. Если нужен контекст - смотрим с контекстом
grep -C 10 -i error logs/bot.log | tail -50

# 5. Полный лог последних действий
tail -100 logs/bot.log

# 6. Если нашли проблему и пофиксили - перезапуск
sudo systemctl restart planerbot.service

# 7. Проверяем, что всё ок
tail -f logs/bot.log
# Ctrl+C для выхода
```

---

Теперь логи доступны для анализа в любое время! 📝
