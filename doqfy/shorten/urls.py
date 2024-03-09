from django.urls import path

from . import views

app_name = "shorten"
urlpatterns = [
    path("", views.index, name="index"),
    path("<str:short_id>/", views.redirect_to_long_url, name="shortener-redirect"),
]
