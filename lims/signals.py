from django.db.models.signals import post_save
from django.dispatch import receiver
from lims.models import TestAssignment
from lims.utils.result_to_review import promote_samples_for_parameter_if_ready

@receiver(post_save, sender=TestAssignment)
def auto_promote_samples(sender, instance, **kwargs):
    if instance.status == "completed":
        parameter = instance.parameter
        client = instance.sample.client
        promote_samples_for_parameter_if_ready(parameter, client)
