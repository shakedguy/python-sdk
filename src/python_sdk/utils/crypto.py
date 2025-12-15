from __future__ import annotations

import hashlib
import os
import random
import secrets
import string
import time
from datetime import UTC, datetime
from typing import Literal, Optional, Union
from uuid import UUID

from ..conf.constants import BSON_EXISTS
from .strings import AnyStr, to_base64, to_hex, to_str


def to_object_id(id_: Union[AnyStr, UUID, "ObjectId"]) -> Optional["ObjectId"]:
    if BSON_EXISTS:
        from bson.objectid import ObjectId
    else:
        from ..domain.base.object_id import ObjectId
    if isinstance(id_, ObjectId):
        return id_
    if isinstance(id_, UUID):
        return ObjectId(id_.bytes.hex()[:24])

    try:
        return ObjectId(id_)
    except:  # noqa
        return ObjectId(UUID(id_).bytes.hex()[:24])


def to_object_id_str(id_: Union[AnyStr, UUID, "ObjectId"]) -> Optional[str]:
    object_id = to_object_id(id_)
    return str(object_id) if object_id else None


def encrypt_password(password: str, salt: str) -> str:
    """
    Encrypts a password using the scrypt hashing algorithm.

    Args:
        password (str): The password to encrypt.
        salt (str): The salt to use for encryption.

    Returns:
        str: The encrypted password as a hexadecimal string.
    """
    return hashlib.scrypt(
        password.encode(), salt=salt.encode(), n=16384, r=8, p=1, dklen=32
    ).hex()


def hash_password(password: str) -> str:
    """
    Hashes a password with a randomly generated salt.

    Args:
        password (str): The password to hash.

    Returns:
        str: The hashed password concatenated with the salt.
    """
    salt = secrets.token_hex(16)
    return encrypt_password(password, salt) + salt


def match_password(password: str, hash_str: str) -> bool:
    """
    Checks if a given password matches the hashed password.

    Args:
        password (str): The password to check.
        hash_str (str): The hashed password to compare against.

    Returns:
        bool: True if the password matches, False otherwise.
    """
    salt = hash_str[64:]
    original_pass_hash = hash_str[:64]
    current_pass_hash = encrypt_password(password, salt)
    return original_pass_hash == current_pass_hash


def generate_random_id(
        length: int,
        *,
        simbols: bool = False,
        encoding: Literal["ascii", "hex", "base64"] = "ascii",
        case: Optional[Literal["upper", "lower"]] = None,
) -> str:
    """
    Generates a random ID of the specified length.

    Args:
        length (int): The length of the random ID.
        simbols (bool): Whether to include symbols in the ID, default is False.
        encoding (Literal): The encoding of the ID, one of "ascii", "hex", "base64", default is "ascii".
        case (Optional[Literal]): The case of the ID, one of "upper", "lower", default is None.

    Returns:
        str: The generated random ID.
    """
    characters = string.ascii_uppercase + string.ascii_lowercase + string.digits
    if simbols:
        characters += string.punctuation

    res = "".join(random.choices(characters, k=length))
    if encoding == "hex":
        res = to_hex(res)
    elif encoding == "base64":
        res = to_base64(res)

    if not case:
        return res

    return res.upper() if "up" in case.lower() else res.lower()


def generate_random_token(
        size: int, base: Literal["binary", "octal", "hex", "decimal", "base-64"]
) -> str:
    """
    Generates a random token of the specified size and base.

    Args:
        size (int): The size of the token.
        base (Literal): The base of the token, one of "binary", "octal", "hex", "decimal", "base-64".

    Returns:
        str: The generated random token.

    Raises:
        ValueError: If the base is not one of the specified values.
    """
    bases = {
        "binary": "01",
        "octal": "01234567",
        "hex": "0123456789abcdef",
        "decimal": "0123456789",
        "base-64": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
    }

    if base not in bases:
        raise ValueError("Invalid base")

    return "".join(secrets.choice(bases[base]) for _ in range(size))


def calculate_md5_hash(content: str) -> str:
    """
    Calculates the MD5 hash of the given content.

    Args:
        content (str): The content to hash.

    Returns:
        str: The MD5 hash of the content as a hexadecimal string.
    """
    return hashlib.md5(content.encode()).hexdigest()


def to_stable_uuid(*parts: AnyStr) -> str:
    """
    Converts multiple parts into a stable UUID string.
    Args:
        *parts (AnyStr): The parts to combine into a UUID.
    Returns:
        str: The stable UUID string.
    """
    if not parts:
        return ""
    h = hashlib.md5("|".join(parts).encode()).hexdigest()
    return str(UUID(hex=h.lower())).upper()


def uuidv7() -> str:
    """
    Generates a UUID version 7 string.

    Returns:
        str: The generated UUID version 7 string.
    """

    timestamp = int(time.time() * 1000)
    random_bytes = os.urandom(10)

    uuid_bytes = (
            timestamp.to_bytes(6, byteorder="big")
            + bytes([(random_bytes[0] & 0x0F) | 0x70])
            + bytes([(random_bytes[1] & 0x3F) | 0x80])
            + random_bytes[2:]
    )
    return str(UUID(bytes=uuid_bytes))


def uuidv7_to_datetime(uuid: AnyStr) -> Optional[datetime]:
    """
    Extract the datetime from a UUIDv7 string.

    Args:
        uuid (str): The UUIDv7 string (hex, with or without dashes).

    Returns:
        datetime: The extracted UTC datetime.
    """

    if not uuid:
        return None
    clean_hex = to_str(uuid).replace("-", "")

    if len(clean_hex) != 32:
        raise ValueError("Invalid UUID string length")

    timestamp_ms = int(clean_hex[:12], 16)

    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)


def generate_unique_secure_token(length: Optional[int] = 24) -> str:
    length = length or 24
    base58_alphabet = string.ascii_letters + string.digits
    base58_alphabet = base58_alphabet.translate(str.maketrans("", "", "0OIl"))
    return "".join(secrets.choice(base58_alphabet) for _ in range(length))
