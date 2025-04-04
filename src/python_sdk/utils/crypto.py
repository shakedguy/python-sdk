import hashlib
import os
import random
import secrets
import time
from abc import ABC
from typing import Literal


class Crypto(ABC):  # noqa
    """
    A utility class for cryptographic operations.

    This class provides methods for password encryption, hashing,
    password matching, random ID generation, random token generation,
    MD5 hash calculation, and UUID version 7 generation.
    """

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
    def generate_random_id(cls, length: int) -> str:
        """
        Generates a random ID of the specified length.

        Args:
            length (int): The length of the random ID.

        Returns:
            str: The generated random ID.
        """
        characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        return "".join(random.choices(characters, k=length))

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

    @classmethod
    def uuid7(cls) -> str:
        """
        Generates a UUID version 7 string.

        Returns:
            str: The generated UUID version 7 string.
        """
        timestamp = int(time.time() * 1000).to_bytes(6, byteorder="big")
        random_bytes = os.urandom(10)
        uuid_bytes = (
            timestamp
            + bytes([(random_bytes[0] & 0x0F) | 0x70])
            + bytes([(random_bytes[1] & 0x3F) | 0x80])
            + random_bytes[2:]
        )
        return uuid_bytes.hex().upper()
