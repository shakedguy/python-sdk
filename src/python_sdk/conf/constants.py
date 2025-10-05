from httpx import Limits, Timeout

SQL_OPERATORS = {
    "eq": "=",
    "ne": "!=",
    "gt": ">",
    "lt": "<",
    "gte": ">=",
    "lte": "<=",
    "like": "LIKE",
    "ilike": "ILIKE",
    "in": "IN",
    "not_in": "NOT IN",
}


MONGO_OPERATORS = {
    "eq": "$eq",
    "ne": "$ne",
    "gt": "$gt",
    "lt": "$lt",
    "gte": "$gte",
    "lte": "$lte",
    "like": "$regex",
    "ilike": "$regex",
    "in": "$in",
    "not_in": "$nin",
}

DATE_ONLY_REGEX_PATTERNS = {
    r"\d{2}-\d{2}-\d{4}": "%d-%m-%Y",  # 12-12-2021
    r"\d{2}/\d{2}/\d{4}": "%d/%m/%Y",  # 12/12/2021
    r"\d{2}.\d{2}.\d{4}": "%d.%m.%Y",  # 12.12.2021
    r"\d{4}-\d{2}-\d{2}": "%Y-%m-%d",  # 2021-12-12
    r"\d{2}/\d{2}/\d{2}": "%d/%m/%y",  # 12/12/21
    r"\d{2}.\d{2}.\d{2}": "%d.%m.%y",  # 12.12.21
    r"\d{2}-\d{2}-\d{2}": "%d-%m-%y",  # 12-12-21
}

TIME_ONLY_REGEX_PATTERNS = {
    r"\d{2}:\d{2}:\d{2}": "%H:%M:%S",  # 12:30:30
    r"\d{2}:\d{2}": "%H:%M",  # 12:30
    r"\d{2}": "%H",  # 12
    r"\d{2}:\d{2}:\d{2}.\d{6}": "%H:%M:%S.%f",  # 12:30:30.123456
}

DATETIME_REGEX_PATTERNS = {
    **{
        rf"{date_key} {time_key}": rf"{date_value} {time_value}"
        for date_key, date_value in DATE_ONLY_REGEX_PATTERNS.items()
        for time_key, time_value in TIME_ONLY_REGEX_PATTERNS.items()
    },
    **DATE_ONLY_REGEX_PATTERNS,
    **TIME_ONLY_REGEX_PATTERNS,
}


DATETIME_JS_TO_PY = {
    "YYYY-MM-DD": "%Y-%m-%d",
    "DD-MM-YYYY": "%d-%m-%Y",
    "DD/MM/YYYY": "%d/%m/%Y",
    "YYYY/MM/DD": "%Y/%m/%d",
    "DD.MM.YYYY": "%d.%m.%Y",
    "YYYY.MM.DD": "%Y.%m.%d",
    "YYYY-MM-DD HH:mm:ss": "%Y-%m-%d %H:%M:%S",
    "DD-MM-YYYY HH:mm:ss": "%d-%m-%Y %H:%M:%S",
    "DD/MM/YYYY HH:mm:ss": "%d/%m/%Y %H:%M:%S",
    "YYYY/MM/DD HH:mm:ss": "%Y/%m/%d %H:%M:%S",
    "DD.MM.YYYY HH:mm:ss": "%d.%m.%Y %H:%M:%S",
    "YYYY.MM.DD HH:mm:ss": "%Y.%m.%d %H:%M:%S",
    "YYYY-MM-DD HH:mm": "%Y-%m-%d %H:%M",
    "DD-MM-YYYY HH:mm": "%d-%m-%Y %H:%M",
    "DD/MM/YYYY HH:mm": "%d/%m/%Y %H:%M",
    "YYYY/MM/DD HH:mm": "%Y/%m/%d %H:%M",
    "DD.MM.YYYY HH:mm": "%d.%m.%Y %H:%M",
    "YYYY.MM.DD HH:mm": "%Y.%m.%d %H:%M",
    "YYYY-MM-DD HH:mm:ss.SSSSSS": "%Y-%m-%d %H:%M:%S.%f",
    "DD-MM-YYYY HH:mm:ss.SSSSSS": "%d-%m-%Y %H:%M:%S.%f",
    "DD/MM/YYYY HH:mm:ss.SSSSSS": "%d/%m/%Y %H:%M:%S.%f",
    "YYYY/MM/DD HH:mm:ss.SSSSSS": "%Y/%m/%d %H:%M:%S.%f",
    "DD.MM.YYYY HH:mm:ss.SSSSSS": "%d.%m.%Y %H:%M:%S.%f",
    "YYYY.MM.DD HH:mm:ss.SSSSSS": "%Y.%m.%d %H:%M:%S.%f",
    "YYYY-MM-DD HH:mm.SSSSSS": "%Y-%m-%d %H:%M.%f",
    "DD-MM-YYYY HH:mm.SSSSSS": "%d-%m-%Y %H:%M.%f",
    "DD/MM/YYYY HH:mm.SSSSSS": "%d/%m/%Y %H:%M.%f",
    "YYYY/MM/DD HH:mm.SSSSSS": "%Y/%m/%d %H:%M.%f",
    "DD.MM.YYYY HH:mm.SSSSSS": "%d.%m.%Y %H:%M.%f",
    "YYYY.MM.DD HH:mm.SSSSSS": "%Y.%m.%d %H:%M.%f",
}


VALID_VARIABLES_PATTERNS = [
    r"\${{(.*?)}}",  # ${{key}}
    r"\${(.*?)}",  # ${key}
    r"{{(.*?)}}",  # {{key}}
    r"{(.*?)}",  # {key}
]
DEFAULT_TIMEOUT_CONFIG = Timeout(timeout=5.0)
DEFAULT_LIMITS = Limits(max_connections=100, max_keepalive_connections=20)
DEFAULT_MAX_REDIRECTS = 20


MIMETYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "bmp": "image/bmp",
    "json": "application/json",
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "csv": "text/csv",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "txt": "text/plain",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "mp4": "video/mp4",
    "yml": "application/x-yaml",
    "yaml": "application/x-yaml",
    "zip": "application/zip",
    "tar": "application/x-tar",
    "gz": "application/gzip",
    "tgz": "application/gzip",
    "html": "text/html",
    "htm": "text/html",
    "xml": "text/xml",
    "svg": "image/svg+xml",
}


CACHE_PREFIX = "cache:"