from django.db import models
from .client import Client


class SampleStatus(models.TextChoices):
    RECEIVED = 'received', 'Received'
    ASSIGNED = 'assigned', 'Assigned'
    IN_PROGRESS = 'in_progress', 'In Progress'
    UNDER_REVIEW = 'under_review', 'Under Review'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'

class Sample(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    sample_code = models.CharField(max_length=50, unique=True)
    sample_type = models.CharField(max_length=100)
    weight = models.DecimalField(max_digits=6, decimal_places=2)
    temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    humidity = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=SampleStatus.choices, default=SampleStatus.RECEIVED)
    received_date = models.DateField(auto_now_add=True)
    
def __str__(self):
    tag = " [QC]" if self.sample_type == "QC" else ""
    return f"{self.sample_code}{tag}"
