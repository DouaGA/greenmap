from django.shortcuts import render, redirect
from django.views import View
import json
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.core.mail import EmailMessage
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.template.loader import render_to_string
from .utils import account_activation_token
from django.urls import reverse
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth.views import LoginView

class EmailValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        email = data['email']
        try:
            validate_email(email)
            if User.objects.filter(email=email).exists():
                return JsonResponse({'email_error': 'Email déjà utilisé'}, status=409)
            return JsonResponse({'email_valid': True})
        except ValidationError:
            return JsonResponse({'email_error': 'Email invalide'}, status=400)

class UsernameValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        username = data['username']
        if not str(username).isalnum():
            return JsonResponse({'username_error': 'Le nom d\'utilisateur ne doit contenir que des caractères alphanumériques'}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({'username_error': 'Nom d\'utilisateur déjà utilisé'}, status=409)
        return JsonResponse({'username_valid': True})

class RegistrationView(View):
    def get(self, request):
        return render(request, 'authentication/register.html')

    def post(self, request):
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        context = {'fieldValues': request.POST}

        if not User.objects.filter(username=username).exists() and not User.objects.filter(email=email).exists():
            if len(password) < 6:
                messages.error(request, 'Le mot de passe doit contenir au moins 6 caractères')
                return render(request, 'authentication/register.html', context)

            user = User.objects.create_user(username=username, email=email)
            user.set_password(password)
            user.is_active = False
            user.save()

            current_site = get_current_site(request)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = account_activation_token.make_token(user)

            activate_url = f'http://{current_site.domain}{reverse("activate", kwargs={"uidb64": uid, "token": token})}'

            email_subject = 'Activation de votre compte'
            email_body = render_to_string('authentication/activate_email.html', {
                'user': user,
                'activate_url': activate_url,
            })
            
            email = EmailMessage(
                email_subject,
                email_body,
                'noreply@trulyclaims.com',
                [email],
            )
            email.send(fail_silently=False)
            messages.success(request, 'Compte créé avec succès. Veuillez vérifier votre email pour l\'activation.')
            return render(request, 'authentication/register.html')

        messages.error(request, 'Une erreur est survenue')
        return render(request, 'authentication/register.html', context)

class VerificationView(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)

            if user.is_active:
                messages.info(request, 'Compte déjà activé')
                return redirect('login')
            
            if not account_activation_token.check_token(user, token):
                messages.error(request, 'Lien d\'activation invalide ou expiré')
                return redirect('login')
            
            user.is_active = True
            user.save()
            messages.success(request, 'Compte activé avec succès')
            return redirect('login')

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            messages.error(request, 'Lien d\'activation invalide')
            return redirect('login')

class LoginView(View):
    template_name = 'authentication/login.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('claims_dashboard')
        return render(request, self.template_name)
    
    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.POST.get('next') or 'claims_dashboard'
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                
                # Vérification des informations du profil avant redirection
                if not hasattr(user, 'userprofile'):
                    messages.warning(request, "Veuillez compléter votre profil")
                    return redirect('edit_profile')
                
                return redirect(next_url)
            else:
                messages.error(request, "Votre compte est désactivé")
        else:
            messages.error(request, "Identifiants incorrects")
        
        return render(request, self.template_name, {'next': next_url})

class LogoutView(View):
    @method_decorator(login_required)
    def post(self, request):
        auth.logout(request)
        messages.success(request, 'Vous avez été déconnecté')
        return redirect('login')

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
from django.shortcuts import redirect

def authentication_redirect(request):
    return redirect('login')