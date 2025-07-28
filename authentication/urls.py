from django.urls import path
from .views import CustomLoginView
from .views import (EmailValidationView, UsernameValidationView, 
                    RegistrationView, VerificationView, 
                    LoginView, LogoutView)

urlpatterns = [
    path('register/', RegistrationView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('activate/<uidb64>/<token>/', VerificationView.as_view(), name='activate'),
    path('validate-email/', EmailValidationView.as_view(), name='validate_email'),
    path('validate-username/', UsernameValidationView.as_view(), name='validate_username'),
    path('accounts/login/', CustomLoginView.as_view(), name='login'),

]