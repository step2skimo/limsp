from django.core.management.base import BaseCommand
from django.utils import timezone
import random

from lims.models import QCMetrics, TestAssignment, Parameter, Sample, User

class Command(BaseCommand):
    help = "Generate 50 fake QC metrics for Protein"

    def handle(self, *args, **kwargs):
        # get the Protein parameter
        protein_param = Parameter.objects.filter(name__iexact="Protein").first()
        if not protein_param:
            self.stdout.write(self.style.ERROR("❌ No parameter called 'Protein' found."))
            return

        # get any existing sample for the test assignment
        sample = Sample.objects.first()
        if not sample:
            self.stdout.write(self.style.ERROR("❌ No samples found. Add a sample first."))
            return

        # get any analyst user
        analyst = User.objects.filter(groups__name="Analyst").first()
        if not analyst:
            self.stdout.write(self.style.ERROR("❌ No analyst user found. Add an analyst first."))
            return

        for i in range(50):
            # create test assignment
            ta = TestAssignment.objects.create(
                parameter=protein_param,
                sample=sample,
                analyst=analyst,
                is_control=True,
                status="completed"
            )

            # acceptable range
            min_val = 11.5
            max_val = 12.5

            # random value around range
            measured = round(random.uniform(min_val - 1, max_val + 1.5), 2)

            qc = QCMetrics.objects.create(
                test_assignment=ta,
                measured_value=measured,
                min_acceptable=min_val,
                max_acceptable=max_val,
                created_at=timezone.now() - timezone.timedelta(days=50 - i)
            )
            qc.save()

        self.stdout.write(self.style.SUCCESS("✅ 50 fake QC metrics for Protein created."))
