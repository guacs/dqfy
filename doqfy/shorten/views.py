from typing import Any

from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseRedirect, QueryDict
from django.http.request import HttpRequest
from django.shortcuts import render
from django.urls import reverse

from .services import InvalidUrlError, LongUrlNotFoundError, ShortenerService, ShortIdGenerationError


def index(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        return shorten_url(request)

    context: dict[str, str] = {}
    if long_url := request.GET.get("long_url"):
        if short_url := request.GET.get("short_url"):
            context["long_url"] = long_url
            context["short_url"] = short_url
        else:
            raise ValidationError("`short_url` must be provided if `long_url` is provided")

    return render(request, "shorten.html", context)


def redirect_to_long_url(request: HttpRequest, short_id: str) -> HttpResponse:
    shortener = ShortenerService()
    try:
        long_url = shortener.get_long_url(short_id)

        return HttpResponseRedirect(long_url)
    except LongUrlNotFoundError:
        return render(request, "not-found.html")


def shorten_url(request: HttpRequest) -> HttpResponse:
    long_url = request.POST["long_url"]

    if not long_url:
        return render(request, "shorten.html", context={"error_message": "Please enter some value for the URL."})

    base_url = request.build_absolute_uri()
    context: dict[str, str] = {"long_url": long_url}

    try:
        shortener = ShortenerService()
        short_url = shortener.get_short_url(long_url, base_url)

        return HttpResponseRedirect(
            _get_route_with_query_params("shorten:index", {"long_url": long_url, "short_url": short_url})
        )

    except ShortIdGenerationError:
        context["error_message"] = "Sorry! Failed to generate a unique short ID for the given URL."

        return render(request, "shorten.html", context)
    except InvalidUrlError:
        context["error_message"] = "Please enter a valid URL."

        return render(request, "shorten.html", context)


def _get_route_with_query_params(viewname: str, query_params: dict[str, Any]) -> str:
    query_dict = QueryDict("", True)
    query_dict.update(query_params)

    base_url = reverse(viewname)

    return f"{base_url}?{query_dict.urlencode()}"
