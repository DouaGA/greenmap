from django.db import models
from django.contrib.auth.models import User

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
    description = models.TextField()
    claim_type = models.ForeignKey(ClaimType, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    location_lat = models.DecimalField(max_digits=9, decimal_places=6)
    location_lng = models.DecimalField(max_digits=9, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Réclamation'
        verbose_name_plural = 'Réclamations'