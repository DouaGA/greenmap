from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='claims_dashboard'),
    path('map/', views.claim_map, name='claims_map'),
    path('stats/', views.claim_stats, name='claims_stats'),
    path('update-status/<int:claim_id>/<str:status>/', 
         views.update_claim_status, 
         name='update_claim_status'),
    path('api/claims/', views.api_claims, name='api_claims'),
]