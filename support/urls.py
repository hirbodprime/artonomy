from django.urls import path
from . import views

app_name = "support"

urlpatterns = [
    path("tickets/", views.ticket_list_view, name="ticket_list"),
    path("tickets/new/", views.ticket_create_view, name="ticket_create"),
    path("tickets/<int:pk>/", views.ticket_detail_view, name="ticket_detail"),
]
