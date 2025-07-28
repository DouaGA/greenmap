from django.core.management.base import BaseCommand
from claims.models import Municipality, Wilaya
import json
import os

class Command(BaseCommand):
    help = 'Import/Update municipalities with delegation data'

    def handle(self, *args, **options):
        file_path = os.path.join('claims', 'data', 'zip-postcodes.json')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            for item in data:
                try:
                    # 1. Get or create Wilaya
                    wilaya, _ = Wilaya.objects.get_or_create(
                        name=item['Gov'],
                        defaults={'code': item['Gov'][:2]}
                    )
                    
                    # 2. Update or create Municipality
                    mun, created = Municipality.objects.update_or_create(
                        postal_code=item['zip'],
                        defaults={
                            'name': item['Cite'],
                            'wilaya': wilaya,
                            'delegation': item['Deleg'],  # Champ maintenant disponible
                            'code': f"{item['zip'][:2]}{item['Cite'][:3].upper()}"
                        }
                    )
                    
                    if created:
                        self.stdout.write(f"Created {mun.name} ({mun.postal_code})")
                    else:
                        self.stdout.write(f"Updated {mun.name} ({mun.postal_code})")
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error processing {item['zip']}: {str(e)}"))
        
        self.stdout.write(
            self.style.SUCCESS('Successfully processed all records'))