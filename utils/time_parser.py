from datetime import datetime, date, timedelta


def parse_reminder_time(text: str) -> datetime | None:
    """
    Parse user input into a future datetime.
    Accepted formats:
      "14:30"           → today at 14:30 (tomorrow if already passed)
      "07.07 14:30"     → that date, current year
      "07.07.2026 14:30"→ exact date
    """
    text = text.strip()
    now  = datetime.now()
    today = now.date()

    # HH:MM
    try:
        parsed = datetime.strptime(text, "%H:%M")
        result = datetime.combine(today, parsed.time())
        if result <= now:
            result += timedelta(days=1)
        return result
    except ValueError:
        pass

    # DD.MM HH:MM  (assume current year)
    try:
        result = datetime.strptime(f"{text} {now.year}", "%d.%m %H:%M %Y")
        if result > now:
            return result
    except ValueError:
        pass

    # DD.MM.YYYY HH:MM
    try:
        result = datetime.strptime(text, "%d.%m.%Y %H:%M")
        if result > now:
            return result
    except ValueError:
        pass

    return None


def format_remind_at(dt: datetime) -> str:
    today    = date.today()
    tomorrow = today + timedelta(days=1)
    if dt.date() == today:
        return f"сегодня в {dt.strftime('%H:%M')}"
    if dt.date() == tomorrow:
        return f"завтра в {dt.strftime('%H:%M')}"
    return dt.strftime("%d.%m.%Y в %H:%M")
