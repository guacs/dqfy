from typing import Any

from django.http import HttpRequest
from django.http.response import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.http import QueryDict

from .services import SnippetCreationError, SnippetService


def index(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        return create_shareable_link(request)

    context: dict[str, str] = {}
    if link := request.GET.get("link"):
        context["link"] = link

    return render(request, "index.html", context)


def create_shareable_link(request: HttpRequest) -> HttpResponse:
    context: dict[str, str] = {}

    snippet = request.POST.get("snippet", None)
    if not snippet:
        context["error_message"] = "Please provide a snippet."

        return render(request, "index.html", context)

    base_url = request.build_absolute_uri()
    key = request.POST.get("key", None)
    share_service = SnippetService()

    try:
        link = share_service.add_and_get_shareable_link(snippet, base_url, key)

        return HttpResponseRedirect(_get_route_with_query_params("shareme:index", {"link": link}))
    except SnippetCreationError:
        context["error_message"] = "Something went wrong! Please try again later."

        return render(request, "index.html", context)


def _get_route_with_query_params(viewname: str, query_params: dict[str, Any]) -> str:
    query_dict = QueryDict("", True)
    query_dict.update(query_params)

    base_url = reverse(viewname)

    return f"{base_url}?{query_dict.urlencode()}"
