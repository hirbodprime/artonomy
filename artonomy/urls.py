"""
URL configuration for artonomy project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',include('core.urls')),
    path('account/',include('accounts.urls')),
    path('posts/',include('posts.urls')),
    path("network/", include(("network.urls", "network"), namespace="network")),
    path("market/", include("marketplace.urls", namespace="marketplace")),
    path("suggest/", include(("suggest.urls", "suggest"), namespace="suggest")),
    path("category/", include("category_app.urls", namespace="categories")),
    path("collab/", include("collab.urls", namespace="collab")),



]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL,  document_root=settings.MEDIA_ROOT)


