from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Claim, ClaimType
import json
from django.http import JsonResponse
from datetime import datetime, timedelta
from django.views.decorators.http import require_GET
from django.db.models import Count, Q
from collections import defaultdict
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

@login_required
def dashboard(request):
    # Données existantes
    claims_by_type = (
        Claim.objects
        .values('claim_type__name')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    
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
    
    # Nouvelle donnée pour la charte des statuts
    status_distribution = (
        Claim.objects.values('status')
        .annotate(count=Count('id'))
        .order_by('status')
    )
    
    context = {
        'claim_types': ClaimType.objects.all(),
        'type_labels': json.dumps([item['claim_type__name'] for item in claims_by_type]),
        'type_data': json.dumps([item['total'] for item in claims_by_type]),
        'dates': json.dumps(sorted(date_counts.keys())),
        'daily_counts': json.dumps([date_counts[date] for date in sorted(date_counts.keys())]),
        'status_labels': json.dumps([dict(Claim.STATUS_CHOICES)[item['status']] for item in status_distribution]),
        'status_data': json.dumps([item['count'] for item in status_distribution]),
        'pending_claims': Claim.objects.filter(status='pending').order_by('-created_at')[:5],
        'accepted_claims': Claim.objects.filter(status='accepted').order_by('-created_at')[:5],
        'rejected_claims': Claim.objects.filter(status='rejected').order_by('-created_at')[:5],
        'total_pending': Claim.objects.filter(status='pending').count(),
        'total_accepted': Claim.objects.filter(status='accepted').count(),
        'total_rejected': Claim.objects.filter(status='rejected').count(),
        'today': end_date,
    }
    
    return render(request, 'claims/dashboard.html', context)

@login_required
def claim_map(request):
    claims = Claim.objects.all()
    return render(request, 'claims/map.html', {'claims': claims})

@login_required
def claim_stats(request):
    # Statistiques globales
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
        'avg_processing_time': avg_processing_time,
    }
    return render(request, 'claims/stats.html', context)

@require_GET
def api_claims(request):
    # Récupération des paramètres de filtre
    status = request.GET.get('status')
    claim_type = request.GET.get('claim_type')
    date = request.GET.get('date')
    
    # Filtrage des réclamations
    claims = Claim.objects.all()
    
    if status and status != 'all':
        claims = claims.filter(status=status)
    
    if claim_type and claim_type != 'all':
        claims = claims.filter(claim_type_id=claim_type)
    
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
            'description': claim.description,
            'location_lat': float(claim.location_lat),
            'location_lng': float(claim.location_lng),
            'status': claim.status,
            'status_display': claim.get_status_display(),
            'claim_type': {
                'id': claim.claim_type.id,
                'name': claim.claim_type.name
            },
            'created_at': claim.created_at.isoformat(),
            'updated_at': claim.updated_at.isoformat() if claim.updated_at else None,
        })
    
    return JsonResponse(data, safe=False)

@csrf_exempt
@require_POST
@login_required
def update_claim_status(request, claim_id, status):
    try:
        claim = Claim.objects.get(id=claim_id)
        if status in ['accepted', 'rejected']:
            claim.status = status
            claim.save()
            return JsonResponse({
                'success': True,
                'new_status': status,
                'status_display': claim.get_status_display()
            })
        return JsonResponse({'success': False, 'error': 'Statut invalide'}, status=400)
    except Claim.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Réclamation non trouvée'}, status=404)