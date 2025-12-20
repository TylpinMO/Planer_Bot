"""Утилиты для работы с датой и временем"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """
    Получить текущее время UTC с timezone info.
    Замена для deprecated datetime.utcnow().
    """
    return datetime.now(timezone.utc)
