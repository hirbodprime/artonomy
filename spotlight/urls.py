from django.urls import path
from .views import activate_spotlight_view

urlpatterns = [
    path("activate/", activate_spotlight_view, name="activate_spotlight"),
]
