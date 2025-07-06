from django.core.management.base import BaseCommand
from lims.models import Sample
from lims.utils.result_to_review import promote_sample_if_ready

class Command(BaseCommand):
    help = "Promotes all samples to UNDER_REVIEW if their parameter assignments are completed"

    def handle(self, *args, **kwargs):
        count = 0
        seen = set()

        for sample in Sample.objects.all():
            key = (sample.client_id, *[a.parameter_id for a in sample.testassignment_set.all()])
            if key not in seen:
                for assignment in sample.testassignment_set.all():
                    promote_sample_if_ready(assignment.parameter, sample.client)
                seen.add(key)
                count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Promotion complete. {count} batches checked."))
