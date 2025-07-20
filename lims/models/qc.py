"""
Module: qc.py
Description: Defines models for Quality Control (QC) metrics and their historical tracking.
These models ensure analytical results meet defined quality standards.
"""

from django.db import models
from .test_assignment import TestAssignment
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


# --------------------------------------------------------------------------------------
# QCMetrics Model
# --------------------------------------------------------------------------------------
class QCMetrics(models.Model):
    """
    Represents quality control metrics for a single test assignment.
    Evaluates measured values against expected or acceptable ranges to determine pass/fail status.
    """

    # Relationship to a test assignment
    test_assignment = models.OneToOneField(
        TestAssignment,
        on_delete=models.CASCADE,
        related_name='qc_metrics',
        help_text="The test assignment this QC record is associated with."
    )

    # Fixed-value evaluation (e.g., CRM with exact expected value)
    expected_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Expected value for this QC check (if applicable)."
    )
    tolerance = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.0,
        help_text="±% allowed deviation from the expected value."
    )

    # Range-based evaluation (e.g., known acceptable interval)
    min_acceptable = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum acceptable value."
    )
    max_acceptable = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum acceptable value."
    )

    # Raw measurement
    measured_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        help_text="The actual measured value for this QC check."
    )

    # Derived metrics
    recovery_percent = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Calculated recovery percentage relative to the expected value."
    )
    status = models.CharField(
        max_length=10,
        choices=[('pass', 'Pass'), ('fail', 'Fail')],
        blank=True,
        help_text="Indicates whether the QC result passes or fails."
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional comments or observations about this QC check."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        help_text="Timestamp when this QC record was created."
    )

    def save(self, *args, **kwargs):
        """
        Overrides the default save method to:
        - Automatically load control limits from the associated parameter's ControlSpec if available.
        - Compute the recovery percentage and determine the QC status (pass/fail).
        """
        # Auto-load limits from ControlSpec if missing
        if not self.min_acceptable and not self.max_acceptable:
            param = self.test_assignment.parameter
            if hasattr(param, 'control_spec'):
                self.min_acceptable = param.control_spec.min_acceptable
                self.max_acceptable = param.control_spec.max_acceptable

        # If expected value is defined, calculate recovery percentage and status
        if self.expected_value is not None and self.measured_value is not None:
            self.recovery_percent = (self.measured_value / self.expected_value) * 100
            deviation = abs(self.recovery_percent - 100)
            self.status = 'pass' if deviation <= float(self.tolerance or 0) else 'fail'

        # If a value range is defined, determine pass/fail based on min/max limits
        elif (
            self.min_acceptable is not None and
            self.max_acceptable is not None and
            self.measured_value is not None
        ):
            self.status = 'pass' if self.min_acceptable <= self.measured_value <= self.max_acceptable else 'fail'
            self.recovery_percent = None

        # If no criteria are available, default to fail
        else:
            self.status = 'fail'

        super().save(*args, **kwargs)


# --------------------------------------------------------------------------------------
# QCMetricsHistory Model
# --------------------------------------------------------------------------------------
class QCMetricsHistory(models.Model):
    """
    Stores historical QC checks linked to a QCMetrics record.
    Useful for audit trails and tracking changes in QC performance over time.
    """

    qc = models.ForeignKey(
        QCMetrics,
        on_delete=models.CASCADE,
        related_name='history',
        help_text="The QC metrics record this history entry is linked to."
    )
    measured_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Measured value recorded during this historical check."
    )
    status = models.CharField(
        max_length=10,
        choices=[('pass', 'Pass'), ('fail', 'Fail')],
        help_text="Result of the QC check (Pass/Fail)."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this historical QC record was created."
    )
    analyst = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        help_text="The analyst who recorded this QC history entry."
    )
