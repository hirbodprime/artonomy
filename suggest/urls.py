# suggest/urls.py
from django.urls import path
from . import views
app_name = "suggest"

urlpatterns = [
    # POST -> toggle suggest/unsuggest on a post
    path("toggle/<int:post_id>/", views.toggle_suggestion, name="toggle"),

    # (Optional) simple lists you can hook up later if you want
    path("user/<str:username>/", views.list_suggested_by_user, name="by_user"),
    path("post/<int:post_id>/", views.list_suggesters_for_post, name="for_post"),
]
