
from django.urls import path
from . import views as v

urlpatterns = [
    path('',v.explore_view,name='explore'),
    path('home/',v.home_view,name='home'),
    path('landing/',v.landing_page,name='landing'),
    path('coming-soon/',v.coming_soon_view,name='coming_soon'),
    path('api/home/', v.home_feed_api, name='home_feed_api'),
    path('api/explore/', v.explore_feed_api, name='explore_feed_api'),

]

