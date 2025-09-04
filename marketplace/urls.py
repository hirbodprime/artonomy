# marketplace/urls.py
from django.urls import path
from . import views

app_name = "marketplace"   # <-- important for namespacing

urlpatterns = [
    path("", views.marketplace_list, name="list"),
    path("item/<int:pk>/", views.marketplace_item, name="item"),
    path("item/<int:pk>/fav/", views.toggle_favorite, name="toggle_favorite"),
    path("add/", views.marketitem_create, name="add"),

]
