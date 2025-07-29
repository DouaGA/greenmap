from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save

class ClaimType(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class Claim(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('accepted', 'Acceptée'),
        ('rejected', 'Rejetée'),
    ]
    title = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    claim_type = models.ForeignKey(ClaimType, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Réclamation'
        verbose_name_plural = 'Réclamations'

from django.db import models

from django.db import models

class Wilaya(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=2)  # Code à 2 chiffres

    def __str__(self):
        return self.name

class Municipality(models.Model):
    name = models.CharField(max_length=100)
    wilaya = models.ForeignKey(Wilaya, on_delete=models.CASCADE)
    postal_code = models.CharField(max_length=10)
    delegation = models.CharField(max_length=100, blank=True, default='')    
    code = models.CharField(max_length=10, blank=True, null=True)    
    class Meta:
        verbose_name_plural = "Municipalities"

    def __str__(self):
        return f"{self.name} ({self.postal_code})"
    
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    image = models.ImageField(
        upload_to='profile_pics/',
        default='profile_pics/default-profile.jpg'
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    municipality = models.ForeignKey(
        Municipality, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    address = models.CharField(max_length=200, blank=True)  # Nouveau champ
    bio = models.TextField(blank=True)  # Nouveau champ
    def __str__(self):
        return f"Profil de {self.user.username}"

# Création automatique du profil lors de la création d'un utilisateur
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
        
def get_absolute_url(self):
    from django.urls import reverse
    return reverse('claim_detail', kwargs={'claim_id': self.id})