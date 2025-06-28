from django.core.management.base import BaseCommand
from lims.models import QCMetrics, TestAssignment
from django.utils import timezone

class Command(BaseCommand):
    help = "Remove only today’s fake Protein QC metrics"

    def handle(self, *args, **kwargs):
        today = timezone.now().date()

        qcs = QCMetrics.objects.filter(
            test_assignment__parameter__name__iexact="Protein",
            test_assignment__is_control=True,
            created_at__date=today
        )

        count = qcs.count()
        for qc in qcs:
            ta = qc.test_assignment
            qc.delete()
            ta.delete()

        self.stdout.write(self.style.SUCCESS(f"✅ Removed {count} fake Protein QC metrics created today."))
