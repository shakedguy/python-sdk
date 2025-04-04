import base64
import re
import unicodedata
from abc import ABC
from os import PathLike
from typing import Any, Iterable, Optional, TypeVar, Union
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import inflect
import phonenumbers
from email_validator import EmailNotValidError, validate_email
from phonenumbers import NumberParseException

from ..chain import Chain
from ..collections import flatten_deep
from ..decorators import memoize
from .regex import (
    DEBURRED_LETTERS,
    JS_RE_ASCII_WORDS,
    JS_RE_LATIN1,
    JS_RE_UNICODE_WORDS,
    RE_APOS,
    RE_CRON,
    RE_DIGITS,
    RE_FALSELY,
    RE_HAS_UNICODE_WORD,
    RE_HEBREW,
    RE_TRUTHY,
    JSRegExp,
)

AnyStr = TypeVar("AnyStr", bytes, str, bytearray, memoryview)
T = TypeVar("T")
T2 = TypeVar("T2")


class Strings(ABC):  # noqa
    """
    A utility class for string manipulation, including conversion between
    different cases such as camelCase, snake_case, kebab-case, PascalCase, and CONSTANT_CASE.
    """

    inflect_engine = inflect.engine()

    @classmethod
    def _raise_for_invalid(cls, text: AnyStr):
        """
        Raises a ValueError if the input is not a string.

        Args:
            text: The input text to validate.

        Raises:
            ValueError: If the input is not a string.
        """

        if not isinstance(text, (str, bytes, bytearray, memoryview)):
            raise ValueError(
                "Input must be a string, not bytes, bytearray, or memoryview"
            )

    @classmethod
    def to_str(cls, text: AnyStr) -> str:
        """
        Converts the input to a string.

        Args:
            text (AnyStr): The input text to convert.

        Returns:
            str: The converted string.
        """

        cls._raise_for_invalid(text)
        return str(text) if isinstance(text, str) else text.decode()

    @classmethod
    def is_falsely(cls, text: AnyStr) -> bool:
        """
        Checks if the input string is a falsely value.

        Args:
            text (AnyStr): The input text to check.

        Returns:
            bool: True if the input is a falsely value, False otherwise.
        """
        return bool(RE_FALSELY.match(cls.to_str(text)))

    @classmethod
    def is_truthy(cls, text: AnyStr) -> bool:
        """
        Checks if the input string is a truthy value.

        Args:
            text (AnyStr): The input text to check.

        Returns:
            bool: True if the input is a truthy value, False otherwise.
        """
        return bool(RE_TRUTHY.match(cls.to_str(text)))

    @classmethod
    def to_title_case(cls, text: AnyStr) -> str:
        """
        Converts a string to Title Case.

        Args:
            text (AnyStr): The input text to convert.

        Returns:
            str: The converted camelCase string.
        """

        def to_title(_word: str) -> str:
            return " ".join(_word.capitalize() for _word in re.split(" ", text))

        return " ".join(map(to_title, cls.to_snake_case(text).split("_")))

    @classmethod
    def to_camel_case(cls, text: AnyStr) -> str:
        """
        Converts `text` to camel case.

        Args:
            text: String to convert.

        Returns:
            String converted to camel case.

        Example:

            >>> Strings.to_camel_case("FOO BAR_bAz")
            'fooBarBAz'
        """
        text = "".join(word.title() for word in cls.compounder(text))
        return text[:1].lower() + text[1:]

    @classmethod
    def to_snake_case(cls, text: AnyStr) -> str:
        """
        Converts a string to snake_case.

        Args:
            text (AnyStr): The input text to convert.

        Returns:
            str: The converted snake_case string.
        """

        return "_".join(
            word.lower()
            for word in cls.compounder(cls.to_str(text).lstrip("_"))
            if word
        )

    @classmethod
    def to_kebab_case(cls, text: AnyStr) -> str:
        """
        Converts a string to kebab-case.

        Args:
            text (AnyStr): The input text to convert.

        Returns:
            str: The converted kebab-case string.
        """

        return "-".join(
            word.lower() for word in cls.compounder(cls.to_str(text)) if word
        )

    @classmethod
    def to_upper_first(cls, text: AnyStr) -> str:
        """
        Converts the first character of a string to uppercase.

        Args:
            text (AnyStr): The input text to convert.

        Returns:
            str: The converted string with the first character in uppercase.
        """
        text = cls.to_str(text)
        return text[:1].upper() + text[1:] if len(text) > 1 else text.upper()

    @classmethod
    def to_pascale_case(cls, text: AnyStr) -> str:
        """
        Converts a string to PascalCase.

        Args:
            text (AnyStr): The input text to convert.

        Returns:
            str: The converted PascalCase string.
        """
        return cls.to_upper_first(cls.to_camel_case(text))

    @classmethod
    def to_constant_case(cls, text: AnyStr) -> str:
        """
        Converts a string to CONSTANT_CASE.

        Args:
            text (AnyStr): The input text to convert.

        Returns:
            str: The converted CONSTANT_CASE string.
        """
        return cls.to_snake_case(cls.to_str(text)).upper()

    @classmethod
    def to_plural(cls, text: AnyStr) -> str:
        """
        Converts a string to its plural form.

        Args:
            text (AnyStr): The input text to convert.

        Returns:
            str: The plural form of the input text.
        """
        text = cls.to_str(text)
        if not len(text):
            return text

        return cls.inflect_engine.plural(text) or text  # noqa

    @classmethod
    def to_singular(cls, text: AnyStr) -> str:
        """
        Converts a string to its singular form.

        Args:
            text (AnyStr): The input text to convert.

        Returns:
            str: The singular form of the input text.
        """
        text = cls.to_str(text)
        if not len(text):
            return text
        return cls.inflect_engine.singular_noun(text) or text  # noqa

    @classmethod
    def extract_digits(cls, text: AnyStr) -> str:
        """
        Extracts all digits from the input string.

        Args:
            text (AnyStr): The input string to extract digits from.

        Returns:
            str: The extracted digits.

        """

        text = cls.to_str(text)
        return "".join(RE_DIGITS.findall(text))

    @classmethod
    def is_base64(cls, text: AnyStr) -> bool:
        """
        Checks if the given string is a valid Base64 encoded string.

        Args:
            text (AnyStr): The string to check.

        Returns:
            bool: True if the string is a valid Base64 encoded string, False otherwise
        """

        text = cls.to_str(text)
        try:
            return bool(base64.b64decode(text))
        except Exception:  # noqa
            return False

    @classmethod
    def format_phone_number(
        cls, text: AnyStr, region: Optional[str] = None
    ) -> Optional[str]:
        """
        Formats a phone number to an international format.

        Args:
            text (AnyStr): The phone number to format.
            region (str): The region code to use for formatting.

        Returns:
            str: The formatted phone number.
        """
        if not isinstance(text, str) or not text.strip():
            return None
        text = cls.to_str(text)

        try:
            parsed_number = phonenumbers.parse(number=text, region=region)
            if phonenumbers.is_valid_number(parsed_number):
                return phonenumbers.format_number(
                    parsed_number, phonenumbers.PhoneNumberFormat.E164
                )
            else:
                return None
        except phonenumbers.NumberParseException:
            if not len(region or ""):
                return cls.format_phone_number(text, region="IL")
            return None

    @staticmethod
    @memoize
    def find_folder_path(prefix: PathLike) -> Optional[str]:
        """
        Finds the path of a folder or the parent directory of a file that matches the given prefix.

        Args:
            prefix (PathLike): The prefix to search for.

        Returns:
            Optional[str]: The path of the folder or the parent directory of the file that matches the prefix.
        """
        from ...conf import settings

        for p in settings.base_dir.rglob(prefix):
            if p.is_file():
                return str(p.parent)
            elif p.is_dir():
                return str(p)
        return None

    @staticmethod
    def is_valid_email(email: AnyStr) -> tuple[bool, Optional[EmailNotValidError]]:
        """
        Checks if the given string is a valid email address.

        Args:
            email (AnyStr): The email address to check.

        Returns:
            bool: True if the email address is valid, False otherwise.
        """
        try:
            validate_email(email)
            return True, None
        except EmailNotValidError as e:
            return False, e

    @staticmethod
    def is_valid_phone_number(
        phone_number: AnyStr, region: Optional[str] = None
    ) -> tuple[bool, Optional[NumberParseException]]:
        """
        Checks if the given string is a valid phone number.

        Args:
            phone_number (AnyStr): The phone number to check.
            region (Optional[str]): The region code to use for validation.

        Returns:
            bool: True if the phone number is valid, False otherwise.
        """

        try:
            parsed_number = phonenumbers.parse(phone_number, region=region)
            return phonenumbers.is_valid_number(parsed_number), None
        except NumberParseException as e:
            return False, e

    @classmethod
    def is_cron_expression(cls, cron_expression: str) -> bool:
        """
        Validate a cron expression pattern.

        Args:
            cron_expression (str): The cron expression to validate

        Returns:
            bool: True if the expression is valid, False otherwise
        """

        return bool(isinstance(cron_expression, str) and RE_CRON.match(cron_expression))

    @classmethod
    def compounder(cls, text: AnyStr) -> list[str]:
        """
        Remove single quote before passing into words() to match Lodash-style outputs.

        Required by certain functions such as kebab_case, camel_case, start_case etc.
        """
        return cls.words(cls.deburr(RE_APOS.sub("", cls.to_str(text))))

    @classmethod
    def words(cls, text: AnyStr, pattern: Optional[str] = None) -> list[str]:
        """
        Return list of words contained in `text`.

        References:
            https://github.com/lodash/lodash/blob/master/words.js#L30

        Args:
            text: String to split.
            pattern: Custom pattern to split words on. Defaults to ``None``.

        Returns:
            List of words.

        Example:

            >>> Strings.words("a b, c; d-e")
            ['a', 'b', 'c', 'd', 'e']
            >>> Strings.words("fred, barney, & pebbles", "/[^, ]+/g")
            ['fred', 'barney', '&', 'pebbles']

        """
        text = cls.to_str(text)
        if pattern is None:
            if cls.has_unicode_word(text):
                reg_exp = JS_RE_UNICODE_WORDS
            else:
                reg_exp = JS_RE_ASCII_WORDS
        else:
            reg_exp = JSRegExp(pattern)
        return reg_exp.find(text)

    @classmethod
    def slugify(cls, text: AnyStr, separator: str = "-") -> str:
        """
        Convert `text` into an ASCII slug which can be used safely in URLs. Incoming `text` is converted
        to unicode and noramlzied using the ``NFKD`` form. This results in some accented characters
        being converted to their ASCII "equivalent" (e.g. ``é`` is converted to ``e``). Leading and
        trailing whitespace is trimmed and any remaining whitespace or other special characters without
        an ASCII equivalent are replaced with ``-``.

        Args:
            text: String to slugify.
            separator: Separator to use. Defaults to ``'-'``.

        Returns:
            Slugified string.

        Example:

            >>> Strings.slugify("This is a slug.") == "this-is-a-slug"
            True
            >>> Strings.slugify("This is a slug.", "+") == "this+is+a+slug"
            True
        """
        normalized = (
            unicodedata.normalize("NFKD", cls.to_str(text))
            .encode("ascii", "ignore")
            .decode("utf8")
            .replace("'", "")
        )

        return cls.separator_case(text=normalized, separator=separator)

    @classmethod
    def separator_case(cls, text: AnyStr, separator: str) -> str:
        """
        Splits `text` on words and joins with `separator`.

        Args:
            text: String to convert.
            separator: Separator to join words with.

        Returns:
            Converted string.

        Example:

            >>> Strings.separator_case("a!!b___c.d", "-")
            'a-b-c-d'

        """
        return separator.join(word.lower() for word in cls.words(text=text) if word)

    @classmethod
    def to_url(cls, *args: Any, **kwargs: Any) -> str:
        """
        Combines a series of URL paths into a single URL. Optionally, pass in keyword arguments to
        append query parameters.

        Args:
            args: URL paths to combine.

        Keyword Args:
            kwargs: Query parameters.

        Returns:
            URL string.

        Example:

            >>> link = Strings.to_url("a", "b", ["c", "d"], "/", q="X", y="Z")
            >>> url_path, params = link.split("?")
            >>> assert url_path == "a/b/c/d/"
            >>> assert set(params.split("&")) == {"q=X", "y=Z"}
        """
        # allow reassignment different type
        paths = Chain(args).flatten_deep().map(cls.to_str).value()  # type: ignore
        paths_list = []
        params_list = cls.flatten_url_params(kwargs)

        for path in paths:
            scheme, netloc, path, query, fragment = urlsplit(path)
            query = parse_qsl(query)
            params_list += query
            paths_list.append(urlunsplit((scheme, netloc, path, "", fragment)))

        path = cls.delimited_path_join("/", *paths_list)
        scheme, netloc, path, query, fragment = urlsplit(path)
        query = urlencode(params_list)

        return urlunsplit((scheme, netloc, path, query, fragment))  # noqa

    @classmethod
    def flatten_url_params(
        cls,
        params: Union[
            dict[T, Union[T2, Iterable[T2]]],
            list[tuple[T, Union[T2, Iterable[T2]]]],
        ],
    ) -> list[tuple[T, T2]]:
        """
        Flatten URL params into list of tuples. If any param value is a list or tuple, then map each
        value to the param key.


        Args:
            params: URL parameters to flatten.
        Returns:
            Flattened URL parameters as list of tuples.
        Example:
            >>> assert Strings.flatten_url_params({"a": 1, "b": 2}) == [("a", 1), ("b", 2)]
            >>> assert Strings.flatten_url_params([("a", 1), ("b", 2)]) == [("a", 1), ("b", 2)]
            >>> assert Strings.flatten_url_params([("a", 1), ("a", 2)]) == [("a", 1), ("a", 2)]

        """
        if isinstance(params, dict):
            params = list(params.items())

        flattened: list[Any] = []
        for param, value in params:
            if isinstance(value, (list, tuple)):
                flattened += zip([param] * len(value), value, strict=False)
            else:
                flattened.append((param, value))

        return flattened

    @classmethod
    def delimited_path_join(cls, delimiter: str, *args: Any) -> str:
        """
        Join delimited path using specified delimiter.

        >>> assert Strings.delimited_path_join(".", "") == ""
        >>> assert Strings.delimited_path_join(".", ".") == "."
        >>> assert Strings.delimited_path_join(".", ["", ".a"]) == ".a"
        >>> assert Strings.delimited_path_join(".", ["a", "."]) == "a."
        >>> assert Strings.delimited_path_join(".", ["", ".a", "", "", "b"]) == ".a.b"
        >>> ret = ".a.b.c.d.e."
        >>> assert Strings.delimited_path_join(".", [".a.", "b.", ".c", "d", "e."]) == ret
        >>> assert Strings.delimited_path_join(".", ["a", "b", "c"]) == "a.b.c"
        >>> ret = "a.b.c.d.e.f"
        >>> assert Strings.delimited_path_join(".", ["a.b", ".c.d.", ".e.f"]) == ret
        >>> ret = ".a.b.c.1."
        >>> assert Strings.delimited_path_join(".", ".", "a", "b", "c", 1, ".") == ret
        >>> assert Strings.delimited_path_join(".", []) == ""
        """
        paths = [cls.to_str(path) for path in flatten_deep(args) if path]

        if len(paths) == 1:
            path = paths[0]
        else:
            leading = delimiter if paths and paths[0].startswith(delimiter) else ""
            trailing = delimiter if paths and paths[-1].endswith(delimiter) else ""
            middle = delimiter.join(
                [path.strip(delimiter) for path in paths if path.strip(delimiter)]
            )
            path = "".join([leading, middle, trailing])

        return path

    @classmethod
    def has_unicode_word(cls, text: AnyStr) -> bool:
        """
        Check if the text contains unicode or requires more complex regex to handle.

        Args:
            text (AnyStr): The input text to check.
        Returns:
            bool: True if the text contains unicode or requires complex regex, False otherwise.

        Example:
            >>> Strings.has_unicode_word("Hello World")
            False
            >>> Strings.has_unicode_word("Hello Wörld")
            True
        """
        return bool(RE_HAS_UNICODE_WORD.search(cls.to_str(text)))

    @classmethod
    def deburr(cls, text: AnyStr) -> str:
        """
        Deburrs `text` by converting latin-1 supplementary letters to basic latin letters.

        Args:
            text: String to deburr.

        Returns:
            Deburred string.

        Example:
            >>> Strings.deburr("déjà vu")
            'deja vu'

        """
        return JS_RE_LATIN1.replace(
            cls.to_str(text),
            lambda match: DEBURRED_LETTERS.get(match.group(), match.group()),
        )

    @classmethod
    def is_hebrew(cls, text: AnyStr) -> bool:
        """
        Check if the text contains Hebrew characters.

        Args:
            text (AnyStr): The input text to check.

        Returns:
            bool: True if the text contains Hebrew characters, False otherwise.
        """
        return bool(RE_HEBREW.search(cls.to_str(text)))

    @classmethod
    def is_valid_israeli_id(cls, text: AnyStr) -> bool:
        text = cls.to_str(text)

        if len(text) > 9 or not text.isdigit():
            return False
        text = text.zfill(9)
        total = 0
        for i, digit_char in enumerate(text):
            digit = int(digit_char)
            step = digit * ((i % 2) + 1)
            total += step - 9 if step > 9 else step
        return total % 10 == 0
