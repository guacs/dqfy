import secrets
import string
from typing import Final

from django.core.cache import caches
from django.core.cache.backends.base import BaseCache
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError

from .models import Url


class ShortIdGenerationError(Exception):
    ...


class InvalidUrlError(Exception):
    ...


class LongUrlNotFoundError(Exception):
    ...


class ShortenerService:
    """Service that handles the URL shortening/retrieval."""

    MIN_SHORT_ID_LEN: Final[int] = 8
    MAX_SHORT_ID_LEN: Final[int] = 12

    _short_id_cache: Final[BaseCache] = caches["short-id"]
    """Caches the mapping from long url to the corresponding short ID."""

    _long_url_cache: Final[BaseCache] = caches["long-url"]
    """Caches the mapping from short ID to the long url."""

    def get_long_url(self, short_id: str) -> str:
        if long_url := self._long_url_cache.get(short_id, None):
            return long_url

        try:
            url = Url.objects.get(short_id=short_id)
            long_url = url.long_url
            self._long_url_cache.set(short_id, long_url)

            return long_url
        except Url.DoesNotExist as ex:
            raise LongUrlNotFoundError from ex

    def get_short_url(self, long_url: str, base_url: str) -> str:
        short_id = self.get_or_create_short_id(long_url)

        if base_url.endswith("/"):
            return f"{base_url}{short_id}"

        return f"{base_url}/{short_id}"

    def get_or_create_short_id(self, long_url: str) -> str:
        """Get the short ID for the given URL.

        If the short ID already exists, then that is given and if not,
        then a new ID is created and returned.


        Exceptions:
            ShortIdGenerationError: Raised if a unique short ID was not able to be created.
        """

        try:
            validator = URLValidator()
            validator(long_url)
        except ValidationError as ex:
            raise InvalidUrlError from ex

        if short_id := self._short_id_cache.get(long_url, None):
            return short_id

        try:
            url = Url.objects.get(long_url=long_url)
        except Url.DoesNotExist:
            url = Url(long_url=long_url)
            for length in range(self.MIN_SHORT_ID_LEN, self.MAX_SHORT_ID_LEN):
                # Some error is raised. Catch that.
                url.short_id = _generate_short_id(length)
                try:
                    url.save(force_insert=True)
                except IntegrityError:
                    # Try with a longer key length.
                    continue
                break
            else:
                raise ShortIdGenerationError

        assert url.short_id is not None

        short_id = url.short_id
        self._short_id_cache.set(short_id, long_url)
        self._long_url_cache.set(long_url, short_id)

        return short_id


def _generate_short_id(length: int) -> str:
    # TODO: change this to use nanoID
    letters = [secrets.choice(string.ascii_letters) for _ in range(length)]

    return "".join(letters)
