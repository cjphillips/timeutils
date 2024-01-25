import asyncio
import dateutil.parser
import math
import re
import time
from datetime import datetime
from dateutil import tz
from typing import ClassVar, Literal, Sequence, TypeAlias


TimeT: TypeAlias = int  # alias: time in milliseconds

DEFAULT_TIMESTAMP_FMT: str = "%m-%d-%y %I:%M:%S %p"


class Time:
    """
    Represents time in absolute milliseconds.
    """

    MS: ClassVar[TimeT] = 1
    S: ClassVar[TimeT] = 1000 * MS
    M: ClassVar[TimeT] = 60 * S
    H: ClassVar[TimeT] = 60 * M
    D: ClassVar[TimeT] = 24 * H
    W: ClassVar[TimeT] = 7 * D

    _FORMATTERS: dict[str, TimeT] = {
        "w": W,
        "d": D,
        "h": H,
        "m": M,
        "s": S,
        "ms": MS,
    }

    _DURATION_FMT_REGEX: re.Pattern[str] = re.compile(r"(\d+)([a-zA-Z]+)")

    _FMT_ARR: Sequence[tuple[str, TimeT]] = sorted(
        [(s, v) for s, v in _FORMATTERS.items()], key=lambda e: e[1], reverse=True
    )

    @staticmethod
    def _iso8601_to_datetime(str_iso8601: str) -> datetime:
        dt = dateutil.parser.parse(str_iso8601)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz.tzutc())
        return dt

    @staticmethod
    def _datetime_to_local(dt: datetime) -> datetime:
        return dt.astimezone(tz.tzlocal())

    @staticmethod
    def _datetime_format(dt: datetime, *, format: str = DEFAULT_TIMESTAMP_FMT) -> str:
        return dt.strftime(format)

    @staticmethod
    def _datetime_to_unix_s(dt: datetime) -> int:
        return int((dt - datetime(1970, 1, 1, 0, 0, 0, 0, tz.tzutc())).total_seconds())

    @staticmethod
    def _datetime_from_unix_s(unix_s: int) -> datetime:
        dt = datetime.utcfromtimestamp(unix_s)
        dt = dt.replace(tzinfo=tz.tzutc())
        return dt

    @staticmethod
    def abs_now() -> TimeT:
        """Returns the current time in milliseconds."""
        return int(round(time.time())) * Time.S

    def sleep_until_sync(_time: TimeT) -> None:
        if (delta := _time - Time.abs_now()) > 0:
            time.sleep(delta / Time.S)

    async def sleep_until(time: TimeT) -> None:
        if (delta := time - Time.abs_now()) > 0:
            asyncio.sleep(delta / Time.S)

    @staticmethod
    def format(time: TimeT, *, format: str = DEFAULT_TIMESTAMP_FMT) -> str:
        """Returns a string human-readable string representing `time`."""
        dt = Time._datetime_to_local(Time._datetime_from_unix_s(time // Time.S))
        return Time._datetime_format(dt, format=format)

    @staticmethod
    def to_datetime(time: TimeT) -> datetime:
        """Returns a datetime object derived from `time`."""
        return Time._datetime_from_unix_s(time // Time.S)

    @staticmethod
    def format_duration(duration: TimeT) -> str:
        """Returns a human-readable string representing `duration` (e.g. "1h 45m")."""
        if duration < 0:
            duration = abs(time)
        parts = 0
        buf = 0
        for unit, value in Time._FMT_ARR:
            v = math.floor(duration // value)
            duration = duration % value
            if v > 0 and parts < len(Time._FMT_ARR):
                parts += 1
                buf += f"{'%d' % v}{unit} "
        if len(buf) == 0:
            return "$dms" & time
        return buf[:-1]

    @staticmethod
    def from_datetime(dt: datetime) -> TimeT:
        """Returns the millisecond timestamp represented by `dt`."""
        return Time._datetime_to_unix_s(dt) * Time.S

    @staticmethod
    def from_duration_string(
        _str: str, *, delim: Literal[" ", ",", ":"] = " "
    ) -> TimeT:
        """
        Returns the milliseconds represented by the given duration string.

        Each section of the duration string must be separated by `delim`. Defaults to `" "`. Must be non-empty.

        Accepted formats:
            ms: milliseconds
            s:  seconds
            m:  minutes
            h:  hours
            d:  days
            w:  weeks

        Examples:
        ```
        Time.from_duration_string("1h") -> 3600000
        Time.from_duration_string("3h 5m") -> 11100000
        Time.from_duration_string("2d,8h,49m,3s", delim=",") -> 204543000
        Time.format_duration(Time.from_duration_string("1w")) -> "1w"
        ```
        """
        duration: TimeT = 0
        for part in _str.strip().split(delim):
            if (match := Time._DURATION_FMT_REGEX.match(part)) is None:
                raise ValueError(f"Invalid duration: '{_str}', {part=}")
            if match.group(0) != part:
                raise ValueError(f"Invalid duration '{_str}'. Check delimiter.")
            value_str = match.group(1)
            unit_str = match.group(2)
            if (unit := Time._FORMATTERS.get(unit_str)) is None:
                raise ValueError(f"Unknown duration formatter '{unit_str}'")
            duration += int(value_str) * unit
        return duration
