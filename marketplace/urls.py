# marketplace/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Artpieces
    path("art/", views.artpieces_list, name="artpieces"),
    path("u/<str:username>/art/", views.artpieces_list, name="user_artpieces"),
    path("art/<str:slug>/<int:pk>/", views.artpiece_detail, name="artpiece_detail"),

    # NEW: Art posts (content)
    path("post/<str:slug>/<int:pk>/", views.artpost_detail, name="artpost_detail"),
    path("post/<int:pk>/like/", views.artpost_toggle_like, name="artpost_toggle_like"),

    # Services
    path("services/", views.services_list, name="services"),
    path("u/<str:username>/services/", views.services_list, name="user_services"),
    path("services/<str:slug>/<int:pk>/", views.service_detail, name="service_detail"),
]