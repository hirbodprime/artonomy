# artists/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("explore/",                                   views.category_grid,        name="category_grid"),
    path("explore/<str:cat_slug>/",                    views.subcategory_grid,     name="subcategory_grid"),
    path("explore/<str:cat_slug>/<str:sub_slug>/",     views.subcat_artists_grid,  name="subcat_artists_grid"),
]