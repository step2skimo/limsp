from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from lims.forms import ReagentUsageForm
from lims.models.reagent import ReagentLot, ReagentUsage
from django.db.models import Sum, Count
from django.contrib.auth import get_user_model
from django.utils.timezone import now, timedelta
User = get_user_model()
import csv
from django.http import HttpResponse

@login_required
def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reagent_usage.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Analyst', 'Parameter', 'Reagent Lot', 'Quantity Used', 'Purpose'])

    usage = ReagentUsage.objects.select_related('parameter', 'lot', 'used_by').order_by('-date_used')
    for u in usage:
        writer.writerow([
            u.date_used.strftime('%Y-%m-%d %H:%M'),
            u.used_by.username if u.used_by else 'Unknown',
            u.parameter.name,
            u.lot.lot_number,
            u.quantity_used,
            u.purpose
        ])

    return response



@login_required
def log_reagent_usage(request):
    if request.method == 'POST':
        form = ReagentUsageForm(request.POST)
        if form.is_valid():
            usage = form.save(commit=False)
            usage.used_by = request.user
            usage.save()

            # Auto-decrement lot quantity
            lot = usage.lot
            lot.quantity -= usage.quantity_used
            lot.save()

            return redirect('reagent-usage-success')
    else:
        form = ReagentUsageForm()

    return render(request, 'lims/log_usage.html', {'form': form, 'now': now()})

@login_required
def reagent_usage_success(request):
    return render(request, 'lims/success.html')

@login_required
def reagent_alerts(request):
    expiring_lots = ReagentLot.objects.filter(status='active').filter(expiry_date__lte=now().date() + timedelta(days=30))
    low_stock_lots = ReagentLot.objects.filter(status='active', quantity__lte=10)

    return render(request, 'lims/alerts.html', {
        'expiring_lots': expiring_lots,
        'low_stock_lots': low_stock_lots
    })



@login_required
def manager_reagent_dashboard(request):
    today = now().date()
    thirty_days_later = today + timedelta(days=30)

    # Top 5 reagents used by volume
    top_reagents = (
        ReagentUsage.objects
        .values('lot__reagent__name')
        .annotate(total_used=Sum('quantity_used'))
        .order_by('-total_used')[:5]
    )

    # Usage by each analyst
    usage_by_analyst = list(  # turn into list to modify entries
        ReagentUsage.objects
        .values('used_by__username')
        .annotate(
            total_logs=Count('id'),
            distinct_reagents=Count('lot', distinct=True),
            protocols=Count('parameter__method', distinct=True)
        )
        .order_by('-total_logs')
    )

    # Max log count for progress calculation
    max_logs = max((entry['total_logs'] for entry in usage_by_analyst), default=1)

    # Add progress bar percentage to each analyst
    for entry in usage_by_analyst:
        entry['progress_percent'] = round((entry['total_logs'] / max_logs) * 100, 1)

    # Inventory alerts
    expiring = ReagentLot.objects.filter(status='active', expiry_date__lte=thirty_days_later)
    low_stock = ReagentLot.objects.filter(status='active', quantity__lte=10)

    return render(request, 'lims/reagent_tracking.html', {
        'top_reagents': top_reagents,
        'usage_by_analyst': usage_by_analyst,
        'expiring': expiring,
        'low_stock': low_stock,
        'month': today.strftime('%B %Y'),
    })


@login_required
def usage_history(request):
    usage = ReagentUsage.objects.select_related('parameter', 'lot', 'used_by').order_by('-date_used')
    return render(request, 'lims/usage_history.html', {'usage': usage})

@login_required
def analyst_dashboard(request):

    today = now()
    alerts_expiring = ReagentLot.objects.filter(status='active', expiry_date__lte=today.date() + timedelta(days=30))
    alerts_low_stock = ReagentLot.objects.filter(status='active', quantity__lte=10)

    if request.method == 'POST':
        form = ReagentUsageForm(request.POST)
        if form.is_valid():
            usage = form.save(commit=False)
            usage.used_by = request.user
            usage.save()
            usage.lot.quantity -= usage.quantity_used
            usage.lot.save()
            return redirect('analyst-dashboard')
    else:
        form = ReagentUsageForm()

    recent_usage = (
        ReagentUsage.objects
        .filter(used_by=request.user)
        .select_related('parameter', 'lot__reagent')
        .order_by('-date_used')[:15]
    )

    return render(request, 'lims/analyst_reagent_dashboard.html', {
        'form': form,
        'recent_usage': recent_usage,
        'alerts_expiring': alerts_expiring,
        'alerts_low_stock': alerts_low_stock,
        'now': today,
    })
