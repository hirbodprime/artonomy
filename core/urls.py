
from django.urls import path
from . import views as v

urlpatterns = [
    path('',v.explore_view,name='explore'),
    path('home/',v.home_view,name='home'),
    path('landing/',v.landing_page,name='landing'),
    path('coming-soon/',v.coming_soon_view,name='coming_soon')
]

