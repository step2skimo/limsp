"""
Module: expense.py
Description: Defines the Expense model for tracking laboratory-related expenses.
"""

from django.db import models
from django.conf import settings
from simple_history.models import HistoricalRecords


class Expense(models.Model):
    """
    Represents a financial expense entry in the laboratory system.
    Used for tracking costs like consumables, maintenance, and logistics.
    """

    # ----------------------------------------------------------------------------------
    # Expense Categories
    # ----------------------------------------------------------------------------------
    CATEGORY_CHOICES = [
        ("consumables", "Consumables / Reagents"),
        ("maintenance", "Equipment Maintenance"),
        ("salaries", "Salaries / Stipends"),
        ("utilities", "Utilities"),
        ("logistics", "Logistics / Sample Pickup"),
        ("other", "Other"),
    ]

    # ----------------------------------------------------------------------------------
    # Expense Details
    # ----------------------------------------------------------------------------------
    date = models.DateField(help_text="The date the expense was incurred.")
    description = models.CharField(
        max_length=255, help_text="Short description of the expense."
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default="other",
        help_text="Category of the expense."
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="The amount spent (in Naira)."
    )
    note = models.TextField(
        blank=True, help_text="Optional notes about this expense."
    )

    # ----------------------------------------------------------------------------------
    # Metadata
    # ----------------------------------------------------------------------------------
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses_entered",
        help_text="User who entered this expense record."
    )
    created = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this expense record was created."
    )
    history = HistoricalRecords()
    class Meta:
        """
        Metadata for Expense model:
        - Orders expenses by date and creation time (newest first).
        """
        ordering = ["-date", "-created"]

    def __str__(self):
        """
        String representation for admin and debugging.
        Example: '2025-07-19 – Lab Reagents (₦2500.00)'
        """
        return f"{self.date} – {self.description} (₦{self.amount})"
