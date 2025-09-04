# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("<int:pk>/", views.single_post_view, name="single_post"),
    path("like/<int:pk>/", views.toggle_like, name="post_like"),
    path("save/<int:pk>/", views.toggle_save, name="post_save"),
    path("comment/<int:pk>/", views.post_add_comment, name="post_add_comment"),
    path("new/", views.post_new_start, name="post_new_start"),            # step 1
    path("new/media/", views.post_new_media, name="post_new_media"),      # step 2 (photo/video)
    path("new/text/", views.post_new_text, name="post_new_text"),         # step 2 (text)
    path("new/category/", views.post_new_category, name="post_new_category"),  # step 3
    path("new/review/", views.post_new_review, name="post_new_review"),   # step 4
    path("new/reset/", views.post_new_reset, name="post_new_reset"),      # optional reset


]
