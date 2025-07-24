from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.apps import apps
from simple_history.utils import get_history_model_for_model
from simple_history.models import HistoricalChanges
from django.core.paginator import Paginator


def is_manager(user):
    return user.is_staff or user.groups.filter(name="Manager").exists()


def get_diff(log):
    """Get difference between previous and current record values."""
    if not log.prev_record:
        return "Created new record"
    changes = []
    prev = log.prev_record.__dict__
    curr = log.__dict__
    for field, value in curr.items():
        if field.startswith('_'):  
            continue
        if prev.get(field) != value:
            changes.append(f"{field}: {prev.get(field)} → {value}")
    return "\n".join(changes) or "No changes"



@login_required
def audit_dashboard(request):
    logs = []

    # Filters from query params
    action_filter = request.GET.get('action')
    user_filter = request.GET.get('user')
    role_filter = request.GET.get('role')

    # Get all models from the lims app
    lims_models = apps.get_app_config('lims').get_models()

    # Collect logs from history models
    for model in lims_models:
        if model.__name__.startswith("Historical"):
            continue
        try:
            history_model = get_history_model_for_model(model)
            if history_model:
                logs.extend(history_model.objects.all())
        except Exception:
            continue

    # Filter logs and prepare data
    filtered_logs = []
    for log in logs:
        user = log.history_user

        if action_filter and log.history_type != action_filter:
            continue
        if user_filter and (not user or user.username.lower() != user_filter.lower()):
            continue
        if role_filter and (not user or getattr(user, 'role', '') != role_filter):
            continue

        log.diff = get_diff(log)
        log.display_user = user.get_full_name() or user.username if user else "System"
        log.display_role = getattr(user, 'role', '') if user else ""
        filtered_logs.append(log)

    # Sort logs by date descending
    sorted_logs = sorted(filtered_logs, key=lambda x: x.history_date, reverse=True)

    # Apply pagination
    paginator = Paginator(sorted_logs, 20)  # Show 20 logs per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, 'lims/audit/audit_dashboard.html', {
        'logs': page_obj.object_list,
        'page_obj': page_obj
    })
