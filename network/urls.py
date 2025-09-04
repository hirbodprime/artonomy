from django.urls import path
from . import views

app_name = "network"

urlpatterns = [
    path("u/<str:username>/followers/", views.followers_list, name="followers_list"),
    path("u/<str:username>/following/", views.following_list, name="following_list"),
    path("toggle-follow/<int:user_id>/", views.toggle_follow, name="toggle_follow"),
]
