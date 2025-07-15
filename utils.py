from datetime import datetime


def time_ago(iso_time_str):
    try:
        timestamp = datetime.strptime(iso_time_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        delta = now - timestamp

        seconds = int(delta.total_seconds())

        if seconds < 60:
            return f"من {seconds} ثانية"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"من {minutes} دقيقة"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"من {hours} ساعة"
        else:
            days = seconds // 86400
            return f"من {days} يوم"
    except:
        return "—"
