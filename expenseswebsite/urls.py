from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from claims import views as claims_views  # Importez les vues de l'application claims
from django.conf import settings
from django.conf.urls.static import static
from claims import views as claims_views  # Doit fonctionner si claims/views.py existe
urlpatterns = [
    path('', include('claims.urls')),
    path('authentication/', include('authentication.urls')),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('api/municipality/', claims_views.municipality_lookup, name='municipality_lookup'),

    # Ajoutez cette ligne pour le profil de l'agent
    path('profile/', claims_views.agent_profile, name='agent_profile'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)