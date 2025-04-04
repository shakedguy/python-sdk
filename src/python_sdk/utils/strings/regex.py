from __future__ import annotations

import re
import typing as t
from decimal import Decimal


class UnsetValue: ...


UNSET = UnsetValue()
T = t.TypeVar("T")
T2 = t.TypeVar("T2")
NumberT = t.Union[float, int, Decimal]


class JSRegExp:
    """
    Javascript-style regular expression pattern.

    Converts a Javascript-style regular expression to the equivalent Python version.
    """

    def __init__(self, reg_exp: str) -> None:
        pattern, options = reg_exp[1:].rsplit("/", 1)

        self._global = "g" in options
        self._ignore_case = "i" in options

        flags = re.I if self._ignore_case else 0
        self.pattern = re.compile(pattern, flags=flags)

    def find(self, text: str) -> t.List[str]:
        """Return list of regular expression matches."""
        if self._global:
            results = self.pattern.findall(text)
        else:
            res = self.pattern.search(text)
            if res:
                results = [res.group()]
            else:
                results = []
        return results

    def replace(
        self, text: str, repl: t.Union[str, t.Callable[[re.Match[str]], str]]
    ) -> str:
        """Replace parts of text that match the regular expression."""
        count = 0 if self._global else 1
        return self.pattern.sub(repl, text, count=count)


HTML_ESCAPES = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
    "`": "&#96;",
}

DEBURRED_LETTERS = {
    "\xc0": "A",
    "\xc1": "A",
    "\xc2": "A",
    "\xc3": "A",
    "\xc4": "A",
    "\xc5": "A",
    "\xe0": "a",
    "\xe1": "a",
    "\xe2": "a",
    "\xe3": "a",
    "\xe4": "a",
    "\xe5": "a",
    "\xc7": "C",
    "\xe7": "c",
    "\xd0": "D",
    "\xf0": "d",
    "\xc8": "E",
    "\xc9": "E",
    "\xca": "E",
    "\xcb": "E",
    "\xe8": "e",
    "\xe9": "e",
    "\xea": "e",
    "\xeb": "e",
    "\xcc": "I",
    "\xcd": "I",
    "\xce": "I",
    "\xcf": "I",
    "\xec": "i",
    "\xed": "i",
    "\xee": "i",
    "\xef": "i",
    "\xd1": "N",
    "\xf1": "n",
    "\xd2": "O",
    "\xd3": "O",
    "\xd4": "O",
    "\xd5": "O",
    "\xd6": "O",
    "\xd8": "O",
    "\xf2": "o",
    "\xf3": "o",
    "\xf4": "o",
    "\xf5": "o",
    "\xf6": "o",
    "\xf8": "o",
    "\xd9": "U",
    "\xda": "U",
    "\xdb": "U",
    "\xdc": "U",
    "\xf9": "u",
    "\xfa": "u",
    "\xfb": "u",
    "\xfc": "u",
    "\xdd": "Y",
    "\xfd": "y",
    "\xff": "y",
    "\xc6": "Ae",
    "\xe6": "ae",
    "\xde": "Th",
    "\xfe": "th",
    "\xdf": "ss",
    "\xd7": " ",
    "\xf7": " ",
}


RS_ASCII_WORDS = "/[^\x00-\x2f\x3a-\x40\x5b-\x60\x7b-\x7f]+/g"
RS_LATIN1 = "/[\xc0-\xff]/g"

RS_ASTRAL_RANGE = "\\ud800-\\udfff"
RS_COMBO_MARKS_RANGE = "\\u0300-\\u036f"
RE_COMBO_HALF_MARKS_RANGE = "\\ufe20-\\ufe2f"
RS_COMBO_SYMBOLS_RANGE = "\\u20d0-\\u20ff"
RS_COMBO_MARKS_EXTENDED_RANGE = "\\u1ab0-\\u1aff"
RS_COMBO_MARKS_SUPPLEMENT_RANGE = "\\u1dc0-\\u1dff"
RS_COMBO_RANGE = (
    RS_COMBO_MARKS_RANGE
    + RE_COMBO_HALF_MARKS_RANGE
    + RS_COMBO_SYMBOLS_RANGE
    + RS_COMBO_MARKS_EXTENDED_RANGE
    + RS_COMBO_MARKS_SUPPLEMENT_RANGE
)
RS_DINGBAT_RANGE = "\\u2700-\\u27bf"
RS_LOWER_RANGE = "a-z\\xdf-\\xf6\\xf8-\\xff"
RS_MATH_OP_RANGE = "\\xac\\xb1\\xd7\\xf7"
RS_NON_CHAR_RANGE = "\\x00-\\x2f\\x3a-\\x40\\x5b-\\x60\\x7b-\\xbf"
RS_PUNCTUATION_RANGE = "\\u2000-\\u206f"
RS_SPACE_RANGE = (
    " \\t\\x0b\\f\\xa0\\ufeff\\n\\r\\u2028\\u2029\\"
    "u1680\\u180e\\u2000\\u2001\\u2002\\u2003\\u2004\\u2005\\u2006\\"
    "u2007\\u2008\\u2009\\u200a\\u202f\\u205f\\u3000"
)
RS_UPPER_RANGE = "A-Z\\xc0-\\xd6\\xd8-\\xde"
RS_VAR_RANGE = "\\ufe0e\\ufe0f"
RS_BREAK_RANGE = (
    RS_MATH_OP_RANGE + RS_NON_CHAR_RANGE + RS_PUNCTUATION_RANGE + RS_SPACE_RANGE
)

# Used to compose unicode capture groups.
RS_APOS = "['\u2019]"
RS_BREAK = f"[{RS_BREAK_RANGE}]"
RS_COMBO = f"[{RS_COMBO_RANGE}]"
RS_DIGIT = "\\d"
RS_DINGBAT = f"[{RS_DINGBAT_RANGE}]"
RS_LOWER = f"[{RS_LOWER_RANGE}]"
RS_MISC = (
    f"[^{RS_ASTRAL_RANGE}{RS_BREAK_RANGE}{RS_DIGIT}"
    f"{RS_DINGBAT_RANGE}{RS_LOWER_RANGE}{RS_UPPER_RANGE}]"
)
RS_FITZ = "\\ud83c[\\udffb-\\udfff]"
RS_MODIFIER = f"(?:{RS_COMBO}|{RS_FITZ})"
RS_NON_ASTRAL = f"[^{RS_ASTRAL_RANGE}]"
RS_REGIONAL = "(?:\\ud83c[\\udde6-\\uddff]){2}"
RS_SURR_PAIR = "[\\ud800-\\udbff][\\udc00-\\udfff]"
RS_UPPER = f"[{RS_UPPER_RANGE}]"
RS_ZWJ = "\\u200d"

# Used to compose unicode regexes.
RS_MISC_LOWER = f"(?:{RS_LOWER}|{RS_MISC})"
RS_MISC_UPPER = f"(?:{RS_UPPER}|{RS_MISC})"
RS_OPT_CONTR_LOWER = f"(?:{RS_APOS}(?:d|ll|m|re|s|t|ve))?"
RS_OPT_CONTR_UPPER = f"(?:{RS_APOS}(?:D|LL|M|RE|S|T|VE))?"
RE_OPT_MOD = f"{RS_MODIFIER}?"
RS_OPT_VAR = f"[{RS_VAR_RANGE}]?"
RS_OPT_JOIN = f"(?:{RS_ZWJ}(?:{RS_NON_ASTRAL}|{RS_REGIONAL}|{RS_SURR_PAIR}){RS_OPT_VAR}{RE_OPT_MOD})*"
RS_ORD_LOWER = "\\d*(?:1st|2nd|3rd|(?![123])\\dth)(?=\\b|[A-Z_])"
RS_ORD_UPPER = "\\d*(?:1ST|2ND|3RD|(?![123])\\dTH)(?=\\b|[a-z_])"
RS_SEQ = RS_OPT_VAR + RE_OPT_MOD + RS_OPT_JOIN
RS_EMOJI = f"(?:{RS_DINGBAT}|{RS_REGIONAL}|{RS_SURR_PAIR}){RS_SEQ}"

RS_HAS_UNICODE_WORD = (
    "[a-z][A-Z]|[A-Z]{2}[a-z]|[0-9][a-zA-Z]|[a-zA-Z][0-9]|[^a-zA-Z0-9 ]"
)
RS_UNICODE_WORDS = (
    f"/"
    f"{RS_UPPER}?{RS_LOWER}+{RS_OPT_CONTR_LOWER}(?={RS_BREAK}|{RS_UPPER}|$)"
    f"|{RS_MISC_UPPER}+{RS_OPT_CONTR_UPPER}(?={RS_BREAK}|{RS_UPPER}{RS_MISC_LOWER}|$)"
    f"|{RS_UPPER}?{RS_MISC_LOWER}+{RS_OPT_CONTR_LOWER}"
    f"|{RS_UPPER}+{RS_OPT_CONTR_UPPER}"
    f"|{RS_ORD_UPPER}"
    f"|{RS_ORD_LOWER}"
    f"|{RS_DIGIT}+"
    f"|{RS_EMOJI}"
    f"/g"
)

# Compiled regexes for use in functions.
JS_RE_ASCII_WORDS = JSRegExp(RS_ASCII_WORDS)
JS_RE_UNICODE_WORDS = JSRegExp(RS_UNICODE_WORDS)
JS_RE_LATIN1 = JSRegExp(RS_LATIN1)
RE_HAS_UNICODE_WORD = re.compile(RS_HAS_UNICODE_WORD)
RE_APOS = re.compile(RS_APOS)
RE_HTML_TAGS = re.compile(r"</?[^>]+>")
RE_CRON = re.compile(
    r"^(?P<minute>\*(?:/[0-9]+)?|(?:[0-9]|[1-5][0-9])(?:/[0-9]+)?(?:-(?:[0-9]|[1-5][0-9])|,(?:[0-9]|[1-5][0-9]))*)"  # Minute (0-59)
    r"\s+"
    r"(?P<hour>\*(?:/[0-9]+)?|(?:[0-9]|1[0-9]|2[0-3])(?:/[0-9]+)?(?:-(?:[0-9]|1[0-9]|2[0-3])|,(?:[0-9]|1[0-9]|2[0-3]))*)"  # Hour (0-23)
    r"\s+"
    r"(?P<day>\*(?:/[0-9]+)?|(?:[1-9]|[12][0-9]|3[01])(?:/[0-9]+)?(?:-(?:[1-9]|[12][0-9]|3[01])|,(?:[1-9]|[12][0-9]|3[01]))*)"  # Day (1-31)
    r"\s+"
    r"(?P<month>\*(?:/[0-9]+)?|(?:[1-9]|1[0-2]|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(?:/[0-9]+)?(?:-(?:[1-9]|1[0-2]|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)|,(?:[1-9]|1[0-2]|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC))*)"  # Month
    r"\s+"
    r"(?P<weekday>\*(?:/[0-9]+)?|(?:[0-6]|SUN|MON|TUE|WED|THU|FRI|SAT)(?:/[0-9]+)?(?:-(?:[0-6]|SUN|MON|TUE|WED|THU|FRI|SAT)|,(?:[0-6]|SUN|MON|TUE|WED|THU|FRI|SAT))*)"  # Weekday
    r"(?:\s+"
    r"(?P<year>\*(?:/[0-9]+)?|20[2-9][0-9](?:-20[2-9][0-9]|,20[2-9][0-9])*)?)?$",  # Optional Year
    re.IGNORECASE,
)

RE_TRUTHY = re.compile(r"^(?:true|1|yes|on|ok|okay|y|t|כן|אמת)$", re.IGNORECASE)
RE_FALSELY = re.compile(
    r"^(?:false|0|no|none|null|nil|undefined|לא|שקר|אפס|אין|'')$", re.IGNORECASE
)
RE_DIGITS = re.compile(r"\d+")
RE_HEBREW = re.compile(r"[\u0590-\u05FF]")
