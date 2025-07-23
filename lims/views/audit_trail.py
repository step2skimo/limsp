from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.apps import apps
from simple_history.utils import get_history_model_for_model
from simple_history.models import HistoricalChanges

def is_manager(user):
    return user.is_staff or user.groups.filter(name="Manager").exists()

@login_required
def audit_dashboard(request):
    logs = []

    # Get all models from the lims app
    lims_models = apps.get_app_config('lims').get_models()

    # Loop through each model and get its historical changes
    for model in lims_models:
        # Skip historical models
        if model.__name__.startswith("Historical") or issubclass(model, HistoricalChanges):
            continue
        try:
            history_model = get_history_model_for_model(model)
            if history_model:
                logs.extend(history_model.objects.all())
        except Exception:
            # Skip if the model has no history
            continue

    # Sort logs by date (newest first)
    logs = sorted(logs, key=lambda x: x.history_date, reverse=True)

    # Add diff for each log entry
    for log in logs:
        log.diff = get_diff(log)

    return render(request, 'lims/audit/audit_dashboard.html', {'logs': logs})


def get_diff(log):
    """Get difference between previous and current record values."""
    if not log.prev_record:
        return "Created new record"
    changes = []
    prev = log.prev_record.__dict__
    curr = log.__dict__
    for field, value in curr.items():
        if field.startswith('_'):  # Skip internal fields
            continue
        if prev.get(field) != value:
            changes.append(f"{field}: {prev.get(field)} → {value}")
    return "\n".join(changes) or "No changes"
