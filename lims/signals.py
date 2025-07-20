"""
Module: signals.py
Description: Handles Django signals for automatically promoting samples to review
once all required test assignments for a parameter are completed.

"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from lims.models import TestAssignment
from lims.utils.result_to_review import promote_samples_for_parameter_if_ready


@receiver(post_save, sender=TestAssignment)
def auto_promote_samples(sender, instance, **kwargs):
    """
    Signal handler for post_save event on TestAssignment.

    This function is triggered whenever a TestAssignment is saved.
    If the status of the assignment is 'completed', it checks whether all 
    related samples for the parameter are ready and promotes them for review.

    Args:
        sender (Model): The model class (TestAssignment) that sent the signal.
        instance (TestAssignment): The actual instance being saved.
        **kwargs: Additional keyword arguments provided by the signal.
    """
    # Only promote samples when the test assignment status is marked as completed
    if instance.status == "completed":
        parameter = instance.parameter
        client = instance.sample.client

        # Promote samples for review if all assignments for this parameter are ready
        promote_samples_for_parameter_if_ready(parameter, client)
