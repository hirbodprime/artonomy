# dashboard/urls.py
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('admin/', views.admin_overview, name='admin_overview'),
]
