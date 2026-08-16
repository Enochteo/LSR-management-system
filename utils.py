"""Shared utilities — timezone helpers.

All datetimes stored in the database are UTC-naive. These helpers
convert them to US Central Time (America/Chicago) for display.
zoneinfo is available in Python 3.9+ standard library.
"""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

CENTRAL = ZoneInfo("America/Chicago")


def to_central(dt: datetime) -> datetime:
    """Attach UTC info to a naive datetime and convert to Central Time."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc).astimezone(CENTRAL)


def fmt_central(dt: datetime, fmt: str = "%Y-%m-%d %I:%M %p") -> str | None:
    """Return a Central Time formatted string for a UTC-naive datetime."""
    if dt is None:
        return None
    return to_central(dt).strftime(fmt)


def central_day_bounds(target_date: date) -> tuple[datetime, datetime]:
    """Return UTC-naive start and end of a Central Time calendar day.

    Used for DB queries so that 'today' means the Central Time date,
    not the UTC date.
    """
    day_start_ct = datetime(
        target_date.year, target_date.month, target_date.day,
        tzinfo=CENTRAL,
    )
    day_end_ct = datetime(
        target_date.year, target_date.month, target_date.day,
        23, 59, 59, tzinfo=CENTRAL,
    )
    # Strip tzinfo so the values match the naive UTC columns in SQLite.
    return (
        day_start_ct.astimezone(timezone.utc).replace(tzinfo=None),
        day_end_ct.astimezone(timezone.utc).replace(tzinfo=None),
    )


def today_central() -> date:
    """Return today's date in Central Time."""
    return datetime.now(tz=CENTRAL).date()
