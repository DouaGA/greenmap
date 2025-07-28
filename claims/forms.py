from django import forms
from django.contrib.auth.models import User
from .models import Profile
from .models import Municipality
class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image', 'phone', 'municipality', 'postal_code', 'address', 'bio']
        
    # Ajoutez les champs User si nécessaire
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=False)
    postal_code = forms.CharField(max_length=10, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.municipality:
            self.fields['postal_code'].initial = self.instance.municipality.postal_code
    def clean_postal_code(self):
        postal_code = self.cleaned_data.get('postal_code')
        if postal_code:
            try:
                municipality = Municipality.objects.get(postal_code=postal_code)
                self.cleaned_data['municipality'] = municipality
            except Municipality.DoesNotExist:
                raise forms.ValidationError("Code postal non reconnu")
        return postal_code
class MunicipalityForm(forms.ModelForm):
    class Meta:
        model = Municipality
        fields = ['name', 'wilaya', 'postal_code']  # Add postal_code here