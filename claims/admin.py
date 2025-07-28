from django.contrib import admin
from .models import Claim, ClaimType

class ClaimAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'get_claim_type', 'status', 'created_at', 'get_created_by')
    list_filter = ('status', 'claim_type', 'created_at')
    search_fields = ('title', 'description')
    list_per_page = 20

    def get_claim_type(self, obj):
        return obj.claim_type.name
    get_claim_type.short_description = 'Type'

    def get_created_by(self, obj):
        return obj.created_by.username if obj.created_by else None
    get_created_by.short_description = 'Créé par'

admin.site.register(Claim, ClaimAdmin)
admin.site.register(ClaimType)