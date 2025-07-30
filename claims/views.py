from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from .models import Claim, ClaimType
import json
from datetime import datetime, timedelta
from django.views.decorators.http import require_GET
from django.db.models import Count, Q
from collections import defaultdict
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.files.storage import default_storage
from django.contrib import messages
import os
from .forms import ProfileForm
from .models import Profile  
from .models import Municipality 
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
import csv
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.http import HttpResponse
from openpyxl import Workbook
from io import BytesIO
from django.shortcuts import get_object_or_404
from django.http import JsonResponse


def export_claims(request):
    if request.method == 'POST':
        format_type = request.POST.get('format')
        period = request.POST.get('period', 'all')
        
        # Get filtered queryset based on period
        queryset = Claim.objects.all()
        
        if period == 'today':
            queryset = queryset.filter(created_at__date=timezone.now().date())
        elif period == 'week':
            queryset = queryset.filter(created_at__week=timezone.now().isocalendar()[1])
        elif period == 'month':
            queryset = queryset.filter(created_at__month=timezone.now().month)
        elif period == 'year':
            queryset = queryset.filter(created_at__year=timezone.now().year)
        
        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="claims_{period}.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['ID', 'Title', 'Status', 'Date', 'Type'])  # Adjust fields
            for claim in queryset:
                writer.writerow([claim.id, claim.title, claim.status, claim.created_at, claim.type])
            return response
            
        elif format_type == 'excel':
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="claims_{period}.xlsx"'
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Claims"
            ws.append(['ID', 'Title', 'Status', 'Date', 'Type'])  # Adjust fields
            for claim in queryset:
                ws.append([claim.id, claim.title, claim.status, claim.created_at, claim.type])
            wb.save(response)
            return response
            
    return HttpResponse('Invalid request', status=400)
@login_required
def dashboard(request):
    # Récupérer tous les types de réclamation
    all_types = ClaimType.objects.all()
    type_data = []
    type_labels = []
    
    for claim_type in all_types:
        count = Claim.objects.filter(claim_type=claim_type).count()
        type_labels.append(claim_type.name)
        type_data.append(count)
    
    # Statistiques de statut
    status_data = [
        Claim.objects.filter(status='pending').count(),
        Claim.objects.filter(status='accepted').count(),
        Claim.objects.filter(status='rejected').count()
    ]
    status_labels = ["En attente", "Acceptées", "Rejetées"]
    
    # Données pour le graphique d'évolution (30 derniers jours)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    dates = []
    daily_counts = []
    
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime('%Y-%m-%d'))
        count = Claim.objects.filter(created_at__date=current_date).count()
        daily_counts.append(count)
        current_date += timedelta(days=1)
    
    context = {
        'claim_types': all_types,
        'type_labels': json.dumps(type_labels),
        'type_data': json.dumps(type_data),
        'dates': json.dumps(dates),
        'daily_counts': json.dumps(daily_counts),
        'status_labels': json.dumps(status_labels),
        'status_data': json.dumps(status_data),
        'pending_claims': Claim.objects.filter(status='pending').order_by('-created_at')[:5],
        'accepted_claims': Claim.objects.filter(status='accepted').order_by('-created_at')[:5],
        'rejected_claims': Claim.objects.filter(status='rejected').order_by('-created_at')[:5],
        'total_pending': status_data[0],
        'total_accepted': status_data[1],
        'total_rejected': status_data[2],
        'has_data': Claim.objects.exists(),
        'today': end_date,
    }
    
    return render(request, 'claims/dashboard.html', context)
@login_required
def claim_map(request):
    # Récupérer toutes les municipalités pour le filtre
    municipalities = Municipality.objects.all().order_by('name')
    claim_types = ClaimType.objects.all()
    
    context = {
        'municipalities': municipalities,
        'claim_types': claim_types
    }
    return render(request, 'claims/map.html', context)
@login_required
def claim_stats(request):
    # Statistiques globales
    new_reclamation = Claim.objects.filter(status='pending').order_by('created_at').first()
    total_claims = Claim.objects.count()
    pending = Claim.objects.filter(status='pending').count()
    accepted = Claim.objects.filter(status='accepted').count()
    rejected = Claim.objects.filter(status='rejected').count()

    # Répartition par type
    claims_by_type = (
        Claim.objects.values('claim_type__name')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    # Évolution sur 30 jours
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    date_counts = defaultdict(int)
    current_date = start_date
    while current_date <= end_date:
        date_counts[current_date.strftime('%Y-%m-%d')] = 0
        current_date += timedelta(days=1)
    
    daily_claims = (
        Claim.objects
        .filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
        .extra({'date': "date(created_at)"})
        .values('date')
        .annotate(count=Count('id'))
    )
    
    for item in daily_claims:
        date_counts[item['date']] = item['count']
    
    sorted_dates = sorted(date_counts.items())
    dates = [date for date, count in sorted_dates]
    daily_counts = [count for date, count in sorted_dates]

    # Temps moyen de traitement
    avg_processing_time = None
    processed_claims = Claim.objects.filter(
        Q(status='accepted') | Q(status='rejected'),
        created_at__isnull=False,
        updated_at__isnull=False
    )
    
    if processed_claims.exists():
        avg_hours = sum(
            (claim.updated_at - claim.created_at).total_seconds() / 3600
            for claim in processed_claims
        ) / processed_claims.count()
        avg_processing_time = round(avg_hours, 2)

    context = {
        'total_claims': total_claims,
        'pending': pending,
        'accepted': accepted,
        'rejected': rejected,
        'claims_by_type': claims_by_type,
        'dates': dates,
        'daily_counts': daily_counts,
        'new_reclamation': new_reclamation,
        'total_claims': total_claims,
        'reclamations': Claim.objects.all().order_by('-created_at')[:10],
        'avg_processing_time': avg_processing_time,
    }
    return render(request, 'claims/stats.html', context)

@login_required
def claim_detail(request, claim_id):
    try:
        claim = get_object_or_404(Claim, id=claim_id)
        
        # Vérifier si l'utilisateur est autorisé à voir ce signalement
        if not request.user.is_staff and claim.user != request.user:
            return render(request, 'errors/403.html', status=403)
            
        context = {
            'claim': claim,
            'page_title': f'Détails de la réclamation #{claim.id}',
            'can_edit': request.user.is_staff or claim.user == request.user
        }
        return render(request, 'claims/claim_detail.html', context)
        
    except Exception as e:
        # Loguer l'erreur pour le débogage
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur dans claim_detail: {str(e)}")
        
        # Retourner une réponse d'erreur générique
        return render(request, 'errors/500.html', {
            'error_message': "Une erreur s'est produite lors du chargement des détails du signalement."
        }, status=500)

@require_GET
def api_claim_details(request, claim_id):
    try:
        claim = Claim.objects.get(id=claim_id)
        data = {
            'success': True,
            'id': claim.id,
            'title': claim.title,
            'type': claim.claim_type.name if claim.claim_type else 'Non spécifié',
            'status': claim.get_status_display(),
            'date': claim.created_at.strftime("%Y-%m-%d %H:%M"),
            'description': claim.description,
            'created_by': claim.created_by.username if claim.created_by else None,
            'municipality': claim.municipality.name if claim.municipality else None,
            'claim_type': {
                'id': claim.claim_type.id if claim.claim_type else None,
                'name': claim.claim_type.name if claim.claim_type else None
            }
        }
        return JsonResponse(data)
    except Claim.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Réclamation non trouvée'}, status=404)
    
@require_GET
def api_claims(request):
    # Récupération des paramètres de filtre
    status = request.GET.get('status', 'all')
    claim_type = request.GET.get('type', 'all')
    date = request.GET.get('date', None)
    
    # Filtrage des réclamations
    claims = Claim.objects.all()
    
    if status != 'all':
        claims = claims.filter(status=status)
    
    if claim_type != 'all':
        claims = claims.filter(claim_type__name=claim_type)
    
    if date:
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            claims = claims.filter(created_at__date=date_obj)
        except ValueError:
            return JsonResponse({'error': 'Format de date invalide'}, status=400)
    
    # Sérialisation des données
    data = []
    for claim in claims:
        data.append({
            'id': claim.id,
            'title': claim.title,
            'description': getattr(claim, 'description', ''),  # Safe access to description
            'location_lat': claim.location_lat,
            'location_lng': claim.location_lng,
            'status': claim.status,
            'status_display': claim.get_status_display(),
            'claim_type': {
                'id': claim.claim_type.id if claim.claim_type else None,
                'name': claim.claim_type.name if claim.claim_type else None
            },
            'created_at': claim.created_at.isoformat(),
            'updated_at': claim.updated_at.isoformat() if claim.updated_at else None,
        })
    
    return JsonResponse(data, safe=False)

@require_POST
@csrf_exempt  # Temporarily for debugging, remove in production
def update_claim_status(request, claim_id, status):
    try:
        claim = Claim.objects.get(id=claim_id)
        if status in ['accepted', 'rejected']:
            claim.status = status
            claim.updated_at = timezone.now()
            claim.save()
            return JsonResponse({
                'success': True,
                'message': f'Statut mis à jour vers {status}'
            })
        return JsonResponse({
            'success': False,
            'message': 'Statut invalide'
        }, status=400)
    except Claim.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Réclamation introuvable'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
    
@login_required
def agent_profile(request):
    # Créer le profil s'il n'existe pas
    Profile.objects.get_or_create(user=request.user)
    
    # Gestion de l'upload de photo
    if request.method == 'POST' and 'photo' in request.FILES:
        try:
            profile = request.user.profile
            
            # Supprimer l'ancienne photo si elle existe
            if profile.image and profile.image.name != 'profile_pics/default-profile.jpg':
                old_image_path = profile.image.path
                if default_storage.exists(old_image_path):
                    default_storage.delete(old_image_path)
            
            # Sauvegarder la nouvelle photo
            new_image = request.FILES['photo']
            file_name = f"profile_pics/user_{request.user.id}_{new_image.name}"
            file_path = default_storage.save(file_name, new_image)
            profile.image = file_path
            profile.save()
            messages.success(request, 'Photo de profil mise à jour avec succès!')
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour de la photo: {str(e)}")
    
    return render(request, 'claims/agent_profile.html', {'user': request.user})


@login_required
def edit_profile(request):
    try:
        profile = request.user.profile
    except ObjectDoesNotExist:
        # Créer un profil s'il n'existe pas
        from .models import Profile
        profile = Profile.objects.create(user=request.user)
        messages.info(request, "Un nouveau profil a été créé pour vous.")

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour avec succès!')
            return redirect('agent_profile')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = ProfileForm(instance=profile)

    context = {
        'form': form,
        'municipalities': Municipality.objects.all().order_by('name'),
        'page_title': 'Modifier mon profil'
    }
    
    return render(request, 'claims/edit_profile.html', context)
@require_GET
def municipality_lookup(request):
    postal_code = request.GET.get('postal_code')
    if not postal_code:
        return JsonResponse({'error': 'Code postal requis'}, status=400)
    
    try:
        municipality = Municipality.objects.get(postal_code=postal_code)
        return JsonResponse({
            'municipality': {
                'id': municipality.id,
                'name': municipality.name,
                'wilaya': municipality.wilaya
            }
        })
    except Municipality.DoesNotExist:
        return JsonResponse({'error': 'Municipalité non trouvée'}, status=404)