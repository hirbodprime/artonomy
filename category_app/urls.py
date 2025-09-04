# urls.py
from django.urls import path
from . import views  # if you put these views in an app named "accounts", adjust import

app_name = "categories"

urlpatterns = [
    path("", views.category_index, name="index"),
    path("<slug:slug>/", views.category_artists, name="detail"),
]
