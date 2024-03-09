from django.urls import path

from . import views

app_name = "shorten"
urlpatterns = [
    path("", views.index, name="index"),
]
