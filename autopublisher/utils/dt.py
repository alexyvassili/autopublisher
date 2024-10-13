from datetime import datetime, timedelta, timezone


MSK = timezone(timedelta(hours=3), name="MSK")


def get_dt_now() -> datetime:
    return datetime.now(tz=MSK)


def get_dt_now_string() -> str:
    return get_dt_now().strftime("%Y-%m-%d-%H-%M-%S")
