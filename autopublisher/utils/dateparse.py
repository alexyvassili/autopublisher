import re
from datetime import date

from dateutil.relativedelta import relativedelta

from autopublisher.utils.dt import get_dt_now


numbers = {
    "один": 1,
    "одна": 1,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
}

simple_intervals = {
    "день": "days",
    "неделя": "weeks",
    "месяц": "months",
    "год": "years",
}

intervals = {
    "день": "days",
    "дня": "days",
    "дней": "days",
    "неделя": "weeks",
    "недели": "weeks",
    "недель": "weeks",
    "месяц": "months",
    "месяца": "months",
    "месяцев": "months",
    "год": "years",
    "года": "years",
    "лет": "years",
}

months = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}

text_interval_regexp = re.compile(
    r"^({})\s+({})$".format(
        "|".join(numbers),
        "|".join(intervals),
    ),
)

num_interval_regexp = re.compile(
    r"^(\d+)\s+({})$".format(
        "|".join(intervals),
    ),
)

date_regexp = re.compile(
    r"^(\d+)\s+({})$".format(
        "|".join(months),
    ),
)

date_with_year_regexp = re.compile(
    r"^(\d+)\s+({})\s+(\d+)$".format(
        "|".join(months),
    ),
)

date_with_year_word_regexp = re.compile(
    r"^(\d+)\s+({})\s+(\d+)\sгода$".format(
        "|".join(months),
    ),
)


interval_regexps= (
    text_interval_regexp,
    num_interval_regexp,
)

date_regexps = (
    date_regexp,
    date_with_year_regexp,
    date_with_year_word_regexp,
)


def add_date(text: str, dt: date | None = None) -> date:
    dt = dt or get_dt_now().date()
    text = text.strip()

    if text in simple_intervals:
        interval = simple_intervals[text]
        delta = relativedelta(**{interval: 1})
        return dt + delta

    for regexp in interval_regexps:
        parsed = regexp.match(text)
        if not parsed:
            continue
        num, interval = parsed.groups()
        num, interval = int(numbers.get(num, num)), intervals[interval]
        delta = relativedelta(**{interval: num})
        return dt + delta

    for regexp in date_regexps:
        parsed = regexp.match(text)
        if not parsed:
            continue
        day, month, *_year = parsed.groups()
        day, month = int(day), months[month]
        year = int(_year[0]) if _year else dt.year
        new_dt = date(year=year, month=month, day=day)
        if not _year and new_dt < dt:
            new_dt = date(year=dt.year + 1, month=month, day=day)
        return new_dt
