# =============================================
#  Main URL file — the "address book" of the site
#  Every URL maps to a function that handles it
# =============================================

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),           # Built-in admin panel

    # Hand off everything else to our events app
    path('', include('events.urls')),

    # Built-in login / logout pages
    path('accounts/', include('django.contrib.auth.urls')),
]

# Serve uploaded images (event banners) during development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
