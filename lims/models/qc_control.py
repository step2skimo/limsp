from django.db import models
from .parameter import Parameter
from simple_history.models import HistoricalRecords

class ControlSpec(models.Model):
    parameter = models.OneToOneField(Parameter, on_delete=models.CASCADE, related_name='control_spec')
    min_acceptable = models.DecimalField(max_digits=8, decimal_places=4)
    max_acceptable = models.DecimalField(max_digits=8, decimal_places=4)
    expected_value = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    default_tolerance = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="±% allowed deviation")
    unit = models.CharField(max_length=10, default='%')
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.parameter.name} [{self.min_acceptable}–{self.max_acceptable} {self.unit}]"

