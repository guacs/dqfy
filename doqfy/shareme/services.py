from typing import Final
import string
import secrets

from cachetools import LRUCache

from django.db import IntegrityError
from .models import Snippet


class SnippetCreationError(Exception): ...


class SnippetNotFoundError(Exception): ...

class DecryptionError(Exception): ...


class SnippetService:
    _max_retry_count: Final[int] = 5
    _min_length: Final[int] = 10

    _snippet_cache: Final[LRUCache[str, tuple[str, bool]]] = LRUCache(2000)

    def get_snippet(self, snippet_id: str, key: str | None = None) -> tuple[str, bool]:
        """Get the snippet for the given snippet ID.

        Returns a tuple containing the snippet and a boolean indicating whether the returned
        snippet is encrypted or not. If `True`, then it's encrypted and if `False`, then it's
        decrypted.
        """
        if snippet_details := self._snippet_cache.get(snippet_id, None):
            raw_snippet, encrypted = snippet_details
        else:
            try:
                snippet = Snippet.objects.get(snippet_id=snippet_id)
                raw_snippet, encrypted = snippet.snippet, snippet.encrypted
            except Snippet.DoesNotExist as ex:
                raise SnippetNotFoundError from ex

            self._snippet_cache[snippet_id] = (raw_snippet, encrypted)

        if key:
            return self._decrypt(raw_snippet, key), False

        return raw_snippet, encrypted

    def add_and_get_shareable_link(self, snippet: str, base_url: str, key: str | None = None) -> str:
        snippet_id = self.add_snipppet(snippet, key)

        if base_url.endswith("/"):
            return f"{base_url}{snippet_id}"

        return f"{base_url}/{snippet_id}"

    def add_snipppet(self, snippet: str, key: str | None = None) -> str:
        """Add the snippet to the database.

        If the key is provided, then the snippet will be encrypted.

        Returns:
            The ID of the created snippet.
        """

        if key:
            snippet = self._encrypt(snippet, key)

        count = 0
        while count < self._max_retry_count:
            short_id = _generate_short_id(self._min_length + count)
            snippet_instance = Snippet(snippet_id=short_id, snippet=snippet, encrypted=bool(key))
            try:
                snippet_instance.save(force_insert=True)
                self._snippet_cache[short_id] = (snippet, bool(key))

                return short_id
            except IntegrityError:
                count += 1

                continue

        raise SnippetCreationError("max tries to add snippet exceeded")

    def _encrypt(self, content: str, key: str) -> str:
        # TODO: use cryptography since this encryption might be too good
        return content + key

    def _decrypt(self, content: str, key: str) -> str:

        if len(key) < 10:
            raise DecryptionError

        actual_content_length = len(content) - len(key)

        return content[:actual_content_length]


def _generate_short_id(length: int) -> str:
    letters = [secrets.choice(string.ascii_letters) for _ in range(length)]

    return "".join(letters)
