# portfolio/urls.py
from django.urls import path
from . import views

app_name = "portfolio"

urlpatterns = [
    path("themes/", views.theme_gallery, name="theme_gallery"),
    path("themes/<slug:slug>/", views.theme_demo, name="theme_demo"),
    path("themes/<slug:slug>/select/", views.theme_select, name="theme_select"),
    path("themes/<slug:slug>/upgrade/", views.upgrade_theme, name="upgrade_theme"),

    path("onboarding/", views.onboarding, name="onboarding"),
    path("me/sites/", views.my_portfolios, name="my_portfolios"),
    path("me/sites/<int:site_id>/primary/", views.set_primary_portfolio, name="set_primary_portfolio"),

    path("@<str:username>/", views.public_portfolio, name="public_portfolio"),
    path("@<str:username>/contact/", views.contact_owner, name="contact_owner"),
]
