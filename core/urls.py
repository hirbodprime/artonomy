from django.urls import path
from . import views 
from .views_admin import admin_kpi_dashboard
urlpatterns = [
    path('', views.home_view,name='home'),
    path('contact/', views.contact_view,name='contacts'),
    path('about/', views.about_view,name='about'),
    path("kpi/", admin_kpi_dashboard, name="admin_kpi_dashboard"),

]
