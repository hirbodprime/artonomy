from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

urlpatterns = [
    # path("i18n/switch/", switch_language, name="switch_language"),

    # endpoint used by the language switcher form
    path("i18n/", include("django.conf.urls.i18n")),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('account/', include('accounts.urls')),
    path('posts/', include('posts.urls')),
    path("network/", include(("network.urls", "network"), namespace="network")),
    path("market/", include("marketplace.urls", namespace="marketplace")),
    path("suggest/", include(("suggest.urls", "suggest"), namespace="suggest")),
    path("category/", include("category_app.urls", namespace="categories")),
    path("collab/", include("collab.urls", namespace="collab")),
    path("dashboard/", include("dashboard.urls", namespace="dashboard")),
    prefix_default_language=False,   
)+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

