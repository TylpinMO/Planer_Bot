"""Утилиты для работы с датой и временем"""
from datetime import datetime, timezone, timedelta


def utc_now() -> datetime:
    """
    Получить текущее время UTC с timezone info.
    Замена для deprecated datetime.utcnow().
    """
    return datetime.now(timezone.utc)


def get_user_local_time_str(tz_offset: int) -> str:
    """
    Вычислить текущее локальное время пользователя в формате HH:MM
    
    Args:
        tz_offset: Смещение часового пояса пользователя от UTC (в часах)
        
    Returns:
        Строка времени в формате HH:MM (например, "15:30")
    """
    user_tz = timezone(timedelta(hours=tz_offset))
    return datetime.now(user_tz).strftime('%H:%M')
