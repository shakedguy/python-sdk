import hashlib
import os
import random
import secrets
import string
import time
from abc import ABC
from datetime import UTC, datetime
from typing import Literal, Optional, Union
from uuid import UUID

from bson.objectid import ObjectId

from .strings import AnyStr, Strings


class Crypto(ABC):  # noqa
    """
    A utility class for cryptographic operations.

    This class provides methods for password encryption, hashing,
    password matching, random ID generation, random token generation,
    MD5 hash calculation, and UUID version 7 generation.
    """

    @classmethod
    def to_object_id(cls, id_: Union[AnyStr, UUID, ObjectId]) -> Optional[ObjectId]:
        if isinstance(id_, ObjectId):
            return id_
        if isinstance(id_, UUID):
            return ObjectId(id_.bytes.hex()[:24])

        try:
            return ObjectId(id_)
        except:  # noqa
            return ObjectId(UUID(id_).bytes.hex()[:24])

    @classmethod
    def to_object_id_str(cls, id_: Union[AnyStr, UUID, ObjectId]) -> Optional[str]:
        object_id = cls.to_object_id(id_)
        return str(object_id) if object_id else None

    @classmethod
    def encrypt_password(cls, password: str, salt: str) -> str:
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

    @classmethod
    def hash_password(cls, password: str) -> str:
        """
        Hashes a password with a randomly generated salt.

        Args:
            password (str): The password to hash.

        Returns:
            str: The hashed password concatenated with the salt.
        """
        salt = secrets.token_hex(16)
        return cls.encrypt_password(password, salt) + salt

    @classmethod
    def match_password(cls, password: str, hash_str: str) -> bool:
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
        current_pass_hash = cls.encrypt_password(password, salt)
        return original_pass_hash == current_pass_hash

    @classmethod
    def generate_random_id(
            cls,
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
            res = Strings.to_hex(res)
        elif encoding == "base64":
            res = Strings.to_base64(res)

        if not case:
            return res

        return res.upper() if "up" in case.lower() else res.lower()

    @classmethod
    def generate_random_token(
            cls, size: int, base: Literal["binary", "octal", "hex", "decimal", "base-64"]
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

    @classmethod
    def calculate_md5_hash(cls, content: str) -> str:
        """
        Calculates the MD5 hash of the given content.

        Args:
            content (str): The content to hash.

        Returns:
            str: The MD5 hash of the content as a hexadecimal string.
        """
        return hashlib.md5(content.encode()).hexdigest()

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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
        clean_hex = Strings.to_str(uuid).replace("-", "")

        if len(clean_hex) != 32:
            raise ValueError("Invalid UUID string length")

        timestamp_ms = int(clean_hex[:12], 16)

        return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)

    @staticmethod
    def generate_unique_secure_token(length: Optional[int] = 24) -> str:
        length = length or 24
        base58_alphabet = string.ascii_letters + string.digits
        base58_alphabet = base58_alphabet.translate(str.maketrans("", "", "0OIl"))
        return "".join(secrets.choice(base58_alphabet) for _ in range(length))
