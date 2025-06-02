import re
from datetime import UTC, date, datetime, time, timedelta
from typing import AnyStr, Literal, Optional, Self, Union, override
from zoneinfo import ZoneInfo

from dateutil import parser
from dateutil.relativedelta import relativedelta

from ..conf import constants
from .strings import Strings

Unit = Literal["seconds", "minutes", "hours", "days", "weeks", "months", "years"]


class DateTime(datetime):
    @classmethod
    def from_datetime(cls, dt: datetime) -> Self:
        """
        Creates a DateTime object from a datetime object.

        Args:
            dt (datetime): The datetime object.

        Returns:
            DateTime: The DateTime object.
        """
        return cls(
            dt.year,
            dt.month,
            dt.day,
            dt.hour,
            dt.minute,
            dt.second,
            dt.microsecond,
            dt.tzinfo,
        )

    def is_before(self, other: datetime) -> bool:
        """
        Checks if the current datetime is before another datetime.

        Args:
            other (datetime): The other datetime.

        Returns:
            bool: True if the current datetime is before the other datetime, False otherwise.
        """
        return self < other

    def is_after(self, other: datetime) -> bool:
        """
        Checks if the current datetime is after another datetime.

        Args:
            other (datetime): The other datetime.

        Returns:
            bool: True if the current datetime is after the other datetime, False otherwise.
        """
        return self > other

    def is_between(self, start: datetime, end: datetime) -> bool:
        """
        Checks if the current datetime is between two other datetimes.

        Args:
            start (datetime): The start datetime.
            end (datetime): The end datetime.

        Returns:
            bool: True if the current datetime is between the two other datetimes, False otherwise.
        """
        return start < self < end

    def add(
        self,
        *,
        num: Union[int, float],
        unit: Unit,
    ) -> Self:
        """
        Adds a specified number of units to the datetime.

        Args:
            num (int): The number of units to add.
            unit (str): The unit to add.

        Returns:
            DateTime: The new DateTime object.
        """

        return self._calc(num=num, unit=unit, op="add")

    def subtract(
        self,
        *,
        num: Union[int, float],
        unit: Unit,
    ) -> Self:
        """
        Subtracts a specified number of units from the datetime.

        Args:
            num (int): The number of units to subtract.
            unit (str): The unit to subtract.

        Returns:
            DateTime: The new DateTime object.
        """
        return self._calc(num=num, unit=unit, op="subtract")

    def _calc(
        self,
        *,
        num: Union[int, float],
        unit: Unit,
        op: Literal["add", "subtract"],
    ):
        if op == "subtract":
            num *= -1

        match unit:
            case "seconds":
                return self + timedelta(seconds=num)
            case "minutes":
                return self + timedelta(minutes=num)
            case "hours":
                return self + timedelta(hours=num)
            case "days":
                return self + timedelta(days=num)
            case "weeks":
                return self + timedelta(weeks=num)
            case "months":
                return self + relativedelta(months=num)
            case "years":
                return self + relativedelta(years=num)

    def weekday_name(self):
        return self.strftime("%A")

    def month_name(self):
        return self.strftime("%B")

    def day_name(self):
        return self.strftime("%d")

    @staticmethod
    def number_to_time_format(number: Union[int, float]) -> str:
        """
        Converts a number to a time format string (HH:MM:SS).

        Args:
            number (Union[int, float]): The number to convert.

        Returns:
            str: The formatted time string.
        """
        hours = int(number)
        minutes = int((number - hours) * 60)
        seconds = int((((number - hours) * 60) - minutes) * 60)

        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def to_str(self, _format: Optional[str] = None) -> str:
        """
        Converts the datetime object to a string.

        Args:
            _format (str, optional): The format string. Defaults to None.

        Returns:
            str: The datetime string.
        """
        return self.strftime(_format) if _format else self.isoformat()

    @classmethod
    def to_format_str(
        cls, dt: Union[datetime, AnyStr, int | float], _format: Optional[str] = None
    ) -> str:
        """
        Converts a datetime object to a string.

        Args:
            dt (Union[datetime, str, int | float]): The datetime object to convert.
            _format (str, optional): The format string. Defaults to None.

        Returns:
            str: The datetime string.
        """
        res = dt
        if isinstance(res, (str, bytes, bytearray, memoryview)):
            res = cls.from_str(res)
        if isinstance(res, (int, float)):
            res = datetime.fromtimestamp(res)

        if not res:
            raise ValueError(
                "Invalid input, must be a datetime object, string, or timestamp"
            )
        return res.strftime(_format) if _format else res.isoformat()

    @classmethod
    def from_str(cls, datetime_str: str) -> Optional["DateTime"]:
        """
        Parses a datetime string into a datetime object.

        Args:
            datetime_str (str): The datetime string to parse.

        Returns:
            Optional[datetime]: The parsed datetime object or None if parsing fails.
        """
        try:
            return DateTime.from_datetime(parser.parse(datetime_str))
        except Exception:  # noqa
            pass

        for p, f in constants.DATETIME_REGEX_PATTERNS.items():
            if re.match(p, datetime_str):
                try:
                    return DateTime.strptime(datetime_str, f)
                except Exception:  # noqa
                    pass

        raise ValueError("Invalid datetime string")

    @classmethod
    @override
    def now(cls, tz=None) -> Self:
        """
        Gets the current datetime in the configured timezone.

        Returns:
            datetime: The current datetime.
        """
        from ..conf import settings

        return cls.from_datetime(datetime.now(tz=tz or settings.timezone))

    @classmethod
    def utc_now(cls) -> Self:
        """
        Gets the current UTC datetime.

        Returns:
            datetime: The current UTC datetime.
        """
        return DateTime.from_datetime(datetime.now(tz=UTC))

    @classmethod
    def iso_now(cls) -> str:
        """
        Gets the current datetime in ISO 8601 format in the configured timezone.

        Returns:
            str: The current datetime in ISO 8601 format.
        """
        return cls.now().isoformat()

    @classmethod
    def epoch_now(cls) -> float:
        """
        Gets the current datetime in epoch format.

        Returns:
            float: The current datetime in epoch format.
        """
        return cls.now().timestamp()

    @classmethod
    def utc_epoch_now(cls) -> float:
        """
        Gets the current UTC datetime in epoch format.

        Returns:
            float: The current UTC datetime in epoch format.
        """
        return cls.utc_now().timestamp()

    @classmethod
    def iso_utc_now(cls) -> str:
        """
        Gets the current UTC datetime in ISO 8601 format.

        Returns:
            str: The current UTC datetime in ISO 8601 format.
        """
        return cls.utc_now().isoformat()

    @classmethod
    def to_datetime(cls, dt: Union[datetime, str, int | float]) -> datetime:
        """
        Converts a datetime object to a datetime object.

        Args:
            dt (Union[datetime, str, int | float]): The datetime object to convert.

        Returns:
            datetime: The datetime object.
        """

        if not dt:
            return dt

        if isinstance(dt, datetime):
            return dt
        if isinstance(dt, str):
            dt = cls.from_str(dt)
            if dt:
                return dt
        if isinstance(dt, (int, float)):
            return datetime.fromtimestamp(dt)

        raise ValueError(
            "Invalid input, must be a datetime object, string, or timestamp"
        )

    @classmethod
    def to_app_timezone(cls, dt: Union[datetime, AnyStr, int | float]) -> Self:
        """
        Converts a datetime object to the configured app timezone.

        Args:
            dt (Union[datetime, str, int | float]): The datetime object to convert.

        Returns:
            datetime: The datetime object in the app timezone.
        """
        from ..conf import settings

        if isinstance(dt, datetime):
            if dt.tzinfo != settings.timezone_name:
                dt = dt.replace(tzinfo=ZoneInfo(settings.timezone_name))
                return cls.from_datetime(dt)
            return DateTime.from_datetime(dt)
        if isinstance(dt, (str, bytes, bytearray, memoryview)):
            return cls.from_str(dt)

        if isinstance(dt, (int, float)):
            return DateTime.from_datetime(
                datetime.fromtimestamp(dt, tz=settings.timezone)
            )

        raise ValueError(
            "Invalid input, must be a datetime object, string, or timestamp"
        )

    @classmethod
    def parse(cls, dt: Union[datetime, str, int | float]) -> Self:
        return cls.to_app_timezone(dt=dt)

    @classmethod
    def to_utc(cls, dt: Union[datetime, AnyStr, int | float]) -> Self:
        """
        Converts a datetime object to UTC.

        Args:
            dt (Union[datetime, str, int | float]): The datetime object to convert.

        Returns:
            datetime: The datetime object in UTC.
        """

        if isinstance(dt, datetime):
            if not time.tzinfo or time.tzinfo != ZoneInfo("UTC"):
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
            return DateTime.from_datetime(dt)
        dt = Strings.to_str(dt) if isinstance(dt, (str, bytes)) else dt
        if isinstance(dt, str):
            dt = cls.from_str(dt)
            if dt:
                return dt.astimezone(UTC)
        if isinstance(dt, (int, float)):
            return DateTime.from_datetime(datetime.fromtimestamp(dt, tz=UTC))

        raise ValueError(
            "Invalid input, must be a datetime object, string, or timestamp"
        )

    @staticmethod
    def is_valid_datetime(dt_str: AnyStr) -> bool:
        res = Strings.to_str(dt_str)
        try:
            parser.parse(res)
            return True
        except Exception:  # noqa
            return any(
                re.match(pattern, res)
                for pattern in constants.DATETIME_REGEX_PATTERNS.keys()
            )

    @staticmethod
    def is_valid_date(date_str: AnyStr) -> bool:
        """
        Check if a date string is valid.

        Args:
            date_str (str): The date string to check.

        Returns:
            bool: True if the date string is valid, False otherwise.
        """
        res = DateTime.to_format_str(date_str)
        try:
            parser.parse(res)
            return True
        except Exception:  # noqa
            return any(
                re.match(pattern, res)
                for pattern in constants.DATE_ONLY_REGEX_PATTERNS.keys()
            )

    @staticmethod
    def is_valid_time(time_str: AnyStr) -> bool:
        """
        Check if a time string is valid.

        Args:
            time_str (str): The time string to check.

        Returns:
            bool: True if the time string is valid, False otherwise.
        """
        res = DateTime.to_format_str(time_str)
        try:
            parser.parse(res)
            return True
        except Exception:  # noqa
            return any(
                re.match(pattern, res)
                for pattern in constants.TIME_ONLY_REGEX_PATTERNS.keys()
            )

    @staticmethod
    def to_date_only(inpt: Union[datetime, AnyStr, int | float]) -> date:
        """
        Converts a datetime object to date only.

        Args:
            inpt (Union[datetime, str, int | float]): The datetime object to convert.

        Returns:
            date: The date object.
        """
        return DateTime.to_app_timezone(inpt).date()

    @staticmethod
    def to_time_only(inpt: Union[datetime, AnyStr, int, float]) -> time:
        """
        Converts a datetime object to time only.

        Args:
            inpt (Union[datetime, str, int | float]): The datetime object to convert.

        Returns:
            time: The time object.
        """
        return DateTime.to_app_timezone(inpt).time()

    @staticmethod
    def duration(
        *,
        start: Union[datetime, AnyStr, int, float],
        end: Union[datetime, AnyStr, int, float],
        unit: Unit = "seconds",
    ) -> float:
        """
        Calculates the duration between two datetime objects.

        Args:
            start (Union[datetime, str, int | float]): The start datetime.
            end (Union[datetime, str, int | float]): The end datetime.
            unit (str): The unit to return the duration in.

        Returns:
            float: The duration in the specified unit.
        """
        start = DateTime.to_app_timezone(start)
        end = DateTime.to_app_timezone(end)
        delta = end - start

        match unit:
            case "seconds":
                result = delta.total_seconds()
            case "minutes":
                result = delta.total_seconds() / 60
            case "hours":
                result = delta.total_seconds() / 3600
            case "days":
                result = delta.days
            case "weeks":
                result = delta.days / 7
            case "months":
                result = delta.days / 30
            case "years":
                result = delta.days / 365
            case _:
                raise ValueError("Invalid unit for duration calculation")

        return round(result, 3) if isinstance(result, float) else result
