from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db.models import F, ExpressionWrapper, DurationField, Avg, Count
from datetime import timedelta
from lims.models import *

class Command(BaseCommand):
    help = "Generate weekly efficiency snapshots for each analyst"

    def handle(self, *args, **kwargs):
        today = now().date()
        last_monday = today - timedelta(days=today.weekday())
        previous_monday = last_monday - timedelta(days=7)

        results = TestResult.objects.filter(
            started_at__isnull=False,
            recorded_at__isnull=False,
            recorded_at__date__gte=previous_monday,
            recorded_at__date__lt=last_monday
        ).annotate(
            duration=ExpressionWrapper(
                F("recorded_at") - F("started_at"),
                output_field=DurationField()
            )
        )

        stats = results.values(
            "test_assignment__analyst"
        ).annotate(
            avg_duration=Avg("duration"),
            test_count=Count("id")
        )

        for stat in stats:
            EfficiencySnapshot.objects.update_or_create(
                analyst_id=stat["test_assignment__analyst"],
                week_start=previous_monday,
                week_end=last_monday - timedelta(days=1),
                defaults={
                    "average_duration": stat["avg_duration"],
                    "total_tests": stat["test_count"]
                }
            )

        self.stdout.write(self.style.SUCCESS("Efficiency snapshots created ✅"))
