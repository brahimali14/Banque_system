from datetime import datetime


def maintenant() -> datetime:
    return datetime.now().replace(microsecond=0)
