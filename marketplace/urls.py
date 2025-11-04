# marketplace/urls.py
from django.urls import path
from . import views

app_name = "marketplace"

urlpatterns = [
    path("", views.marketplace_home, name="home"),

    # public
    path("profile/<slug:slug>/", views.profile_public, name="profile"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),

    # join flow
    path("join/", views.join_marketplace_entry, name="join_entry"),
    path("join/step/", views.join_marketplace_steps, name="join_steps"),

    # dashboard (for approved members)
    path("dashboard/", views.studio_dashboard, name="dashboard"),


    path("studio/products/add/", views.product_create, name="product_add"),
    path("studio/products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("studio/products/<int:pk>/delete/", views.product_delete, name="product_delete"),

]
