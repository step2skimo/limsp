from django.conf import settings
from .sample import Sample
from .parameter import Parameter
from django.db import models
from django.contrib.auth import get_user_model
from simple_history.models import HistoricalRecords
User = get_user_model()


class TestAssignment(models.Model):
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    analyst = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    assigned_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending')  
    equipment_used = models.ForeignKey(
    'lims.Equipment',  
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    help_text="Equipment used for this test"
)
    is_control = models.BooleanField(default=False)
    is_reference = models.BooleanField(default=False)
    manager_comment = models.TextField(null=True, blank=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.parameter.name} - {self.sample.sample_code}"

class TestResult(models.Model):
    test_assignment = models.OneToOneField(TestAssignment, on_delete=models.CASCADE)
    value = models.FloatField(null=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    recorded_at = models.DateTimeField(null=True, auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=20, choices=[('manual', 'Manual'), ('system', 'System')], default='manual')
    calculation_note = models.TextField(blank=True, null=True)
    history = HistoricalRecords()
    def __str__(self):
        return f"{self.test_assignment} = {self.value}"




