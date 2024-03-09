import base64
import os
import secrets
import string
from dataclasses import dataclass
from typing import Final

from cachetools import LRUCache
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.db import IntegrityError

from .models import Snippet


class SnippetCreationError(Exception): ...


class SnippetNotFoundError(Exception): ...


class DecryptionError(Exception): ...


@dataclass
class EncryptedSnippet:
    snippet: str
    """The encrypted snippet."""

    salt: bytes
    """The salt used to encrypt the snippet."""


class SnippetService:
    _max_retry_count: Final[int] = 5
    _min_length: Final[int] = 10
    _salt_length: Final[int] = 16

    _snippet_cache: Final[LRUCache[str, Snippet]] = LRUCache(3000)

    def get_snippet(self, snippet_id: str, key: str | None = None) -> tuple[str, bool]:
        """Get the snippet for the given snippet ID.

        Returns a tuple containing the snippet and a boolean indicating whether the returned
        snippet is encrypted or not. If `True`, then it's encrypted and if `False`, then it's
        decrypted.
        """

        if (snippet := self._snippet_cache.get(snippet_id, None)) is None:
            try:
                snippet = Snippet.objects.get(snippet_id=snippet_id)
            except Snippet.DoesNotExist as ex:
                raise SnippetNotFoundError from ex

        if key:
            if snippet.salt is None:
                raise ValueError("snippet does not have a salt")

            try:
                encrypted_snippet = EncryptedSnippet(snippet=snippet.snippet, salt=snippet.salt)
                return self._decrypt(key, encrypted_snippet), False
            except InvalidToken as ex:
                raise DecryptionError from ex

        return snippet.snippet, snippet.encrypted

    def add_and_get_shareable_link(self, snippet: str, base_url: str, key: str | None = None) -> str:
        """Create a shareable link for the given snippet.

        If a key is provided, then the snippet is encrypted before saving it.
        """

        snippet_id = self.add_snipppet(snippet, key)

        if base_url.endswith("/"):
            return f"{base_url}{snippet_id}"

        return f"{base_url}/{snippet_id}"

    def add_snipppet(self, snippet: str, key: str | None = None) -> str:
        """Add the snippet to the database.

        If the key is provided, then the snippet will be encrypted.

        Returns
        -------
            The ID of the created snippet.

        """

        encrypted_snippet = None
        if key:
            encrypted_snippet = self._encrypt(snippet, key)

        if encrypted_snippet is None:
            snippet_instance = Snippet(snippet=snippet, encrypted=False, salt=None)
        else:
            snippet_instance = Snippet(snippet=encrypted_snippet.snippet, salt=encrypted_snippet.salt, encrypted=True)

        count = 0
        while count < self._max_retry_count:
            snippet_instance.snippet_id = _generate_short_id(self._min_length + count)
            try:
                snippet_instance.save(force_insert=True)
                self._snippet_cache[snippet_instance.snippet_id] = snippet_instance

                return snippet_instance.snippet_id
            except IntegrityError:
                count += 1

                continue

        raise SnippetCreationError("max tries to add snippet exceeded")

    def _encrypt(self, content: str, key: str) -> EncryptedSnippet:
        salt = os.urandom(self._salt_length)
        encryption_key = self._generate_key(key, salt)

        fernet = Fernet(encryption_key)
        encrypted = fernet.encrypt(content.encode())

        return EncryptedSnippet(encrypted.decode(), salt)

    def _decrypt(self, key: str, encrypted_snippet: EncryptedSnippet) -> str:
        encryption_key = self._generate_key(key, encrypted_snippet.salt)

        fernet = Fernet(encryption_key)
        decrypted = fernet.decrypt(encrypted_snippet.snippet.encode())

        return decrypted.decode()

    def _generate_key(self, key: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        derived_key = kdf.derive(key.encode())

        return base64.urlsafe_b64encode(derived_key)


def _generate_short_id(length: int) -> str:
    letters = [secrets.choice(string.ascii_letters) for _ in range(length)]

    return "".join(letters)
