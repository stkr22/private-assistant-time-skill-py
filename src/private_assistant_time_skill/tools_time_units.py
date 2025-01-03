from datetime import datetime, timedelta


def format_time_difference(time_diff: timedelta) -> str:
    total_seconds = int(time_diff.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    return " and ".join(parts)


def format_time_for_tts(time: datetime, with_date: bool = False) -> str:
    hour = time.hour
    minute = time.minute

    if minute == 0:
        time_str = f"{hour} o'clock"
    elif minute < 10:
        time_str = f"{minute} past {hour}"
    else:
        time_str = f"{minute} past {hour}"

    if with_date:
        date_str = time.strftime("%A, %B %d")
        return f"{date_str} at {time_str}"
    return time_str
