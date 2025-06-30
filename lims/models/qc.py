# lims/models/qc.py
from django.db import models
from .test_assignment import TestAssignment  
from django.conf import settings
from django.contrib.auth import get_user_model
User = get_user_model()


class QCMetrics(models.Model):
    test_assignment = models.OneToOneField(TestAssignment, on_delete=models.CASCADE, related_name='qc_metrics')

    # Fixed-value evaluation (e.g., CRM with exact value)
    expected_value = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    tolerance = models.DecimalField(max_digits=5, decimal_places=2, default=10.0, help_text="±% allowed deviation")

    # Range-based evaluation (e.g., known acceptable interval)
    min_acceptable = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    max_acceptable = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # Raw result
    measured_value = models.DecimalField(max_digits=8, decimal_places=2, null=True)

    # Derived
    recovery_percent = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=10, choices=[('pass', 'Pass'), ('fail', 'Fail')], blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)


    def save(self, *args, **kwargs):
        # Auto-load limits from ControlSpec if missing
        if not self.min_acceptable and not self.max_acceptable:
            param = self.test_assignment.parameter
            if hasattr(param, 'control_spec'):
                self.min_acceptable = param.control_spec.min_acceptable
                self.max_acceptable = param.control_spec.max_acceptable

        if self.expected_value is not None and self.measured_value is not None:
            self.recovery_percent = (self.measured_value / self.expected_value) * 100
            deviation = abs(self.recovery_percent - 100)
            self.status = 'pass' if deviation <= float(self.tolerance or 0) else 'fail'

        elif (
            self.min_acceptable is not None and 
            self.max_acceptable is not None and 
            self.measured_value is not None
        ):
            self.status = 'pass' if self.min_acceptable <= self.measured_value <= self.max_acceptable else 'fail'
            self.recovery_percent = None

        else:
            self.status = 'fail'  # can't evaluate

        super().save(*args, **kwargs)



class QCMetricsHistory(models.Model):
    qc = models.ForeignKey(QCMetrics, on_delete=models.CASCADE, related_name='history')
    measured_value = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=[('pass', 'Pass'), ('fail', 'Fail')])
    created_at = models.DateTimeField(auto_now_add=True)
    analyst = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
