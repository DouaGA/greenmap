from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from claims import views as claims_views
from django.conf import settings
from django.conf.urls.static import static
from authentication.views import authentication_redirect

urlpatterns = [
    path('', include('claims.urls')),
    path('authentication/', authentication_redirect, name='auth_redirect'),
    path('authentication/', include('authentication.urls')),    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),  # URLs d'authentification par défaut de Django
    path('api/municipality/', claims_views.municipality_lookup, name='municipality_lookup'),
    path('profile/', claims_views.agent_profile, name='agent_profile'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)