from typing import Final
import string
import secrets

from cachetools import LRUCache

from django.db import IntegrityError
from .models import Snippet


class SnippetCreationError(Exception): ...


class SnippetNotFoundError(Exception): ...


class SnippetService:
    _max_retry_count: Final[int] = 5
    _min_length: Final[int] = 10

    _snippet_cache: Final[LRUCache[str, str]] = LRUCache(2000)

    def get_snippet(self, snippet_id: str, key: str | None = None) -> str:
        if not (raw_snippet := self._snippet_cache.get(snippet_id, None)):
            try:
                raw_snippet = Snippet.objects.get(snippet_id=snippet_id).snippet
            except Snippet.DoesNotExist as ex:
                raise SnippetNotFoundError from ex

            self._snippet_cache[snippet_id] = raw_snippet

        if key:
            return self._decrypt(raw_snippet, key)

        return raw_snippet

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
            snippet_instance = Snippet(snippet_id=short_id, snippet=snippet)
            try:
                snippet_instance.save(force_insert=True)

                return short_id
            except IntegrityError:
                count += 1

                continue

        raise SnippetCreationError("max tries to add snippet exceeded")

    def _encrypt(self, content: str, key: str) -> str:
        # TODO: use cryptography since this encryption might be too good
        return content + key

    def _decrypt(self, content: str, key: str) -> str:
        actual_content_length = len(content) - len(key)

        return content[:actual_content_length]


def _generate_short_id(length: int) -> str:
    letters = [secrets.choice(string.ascii_letters) for _ in range(length)]

    return "".join(letters)
