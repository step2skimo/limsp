"""
Module: reagents.py
Description:
    Models for managing reagents, their usage, requests, issues, and inventory audits.
    Includes logic for stock deduction, low-stock alerts, and auditing.
"""

from django.db import models
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from lims.utils.notifications import notify_low_stock
from simple_history.models import HistoricalRecords

# ------------------------------------------------------------------------------------------------
# Reagent Model
# ------------------------------------------------------------------------------------------------
class Reagent(models.Model):
    """
    Represents a chemical reagent in the lab inventory.
    Tracks details such as manufacturer, supplier, storage conditions, and stock.
    """

    name = models.CharField(max_length=100)
    batch_number = models.CharField(max_length=100, blank=True, help_text="Unique batch identifier")
    manufacturer = models.CharField(max_length=100, blank=True, help_text="Name of the manufacturer")
    supplier_name = models.CharField(max_length=100, blank=True, help_text="Name of the supplier")
    supplier_contact = models.CharField(max_length=100, blank=True)
    supplier_email = models.EmailField(blank=True)

    date_received = models.DateField(default=timezone.now)
    expiry_date = models.DateField(null=True, blank=True)

    number_of_containers = models.PositiveIntegerField(
        default=1,
        help_text="Total number of containers (bottles, vials, etc.)"
    )
    quantity_per_container = models.FloatField(
        default=1.0,
        help_text="Amount per container, e.g., 2.5 for 2.5L"
    )

    unit = models.CharField(max_length=20, blank=True, help_text="e.g., L, mL, g")
    storage_condition = models.CharField(max_length=100, blank=True)

    safety_data_sheet = models.FileField(upload_to='sds/', null=True, blank=True)
    certificate_of_analysis = models.FileField(upload_to='coa/', null=True, blank=True)

    low_stock_threshold = models.PositiveIntegerField(
        default=2,
        help_text="Threshold to trigger low stock alert"
    )
    history = HistoricalRecords()
    def __str__(self):
        return f"{self.name} (Batch {self.batch_number})"

    @property
    def total_quantity(self):
        """Returns total available quantity based on containers and quantity per container."""
        return self.number_of_containers * self.quantity_per_container

    @property
    def status(self):
        """
        Returns the current status of the reagent:
        - 'Expired' if past expiry date.
        - 'Low Stock' if containers are below threshold.
        - 'Available' otherwise.
        """
        if self.expiry_date and self.expiry_date <= timezone.now().date():
            return "Expired"
        elif self.number_of_containers <= self.low_stock_threshold:
            return "Low Stock"
        return "Available"


# ------------------------------------------------------------------------------------------------
# Reagent Usage Model
# ------------------------------------------------------------------------------------------------
class ReagentUsage(models.Model):
    """
    Represents the consumption of reagents by analysts.
    Automatically deducts container count and triggers low-stock notifications.
    """

    reagent = models.ForeignKey(Reagent, on_delete=models.CASCADE, null=True, blank=True)
    analyst = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    quantity_used = models.PositiveIntegerField(help_text="Number of containers used")
    date_used = models.DateTimeField(auto_now_add=True)
    purpose = models.TextField()

    def save(self, *args, **kwargs):
        """
        Overrides save to:
        - Deduct container count.
        - Validate availability of containers.
        - Send low stock alerts to managers when threshold is reached.
        """
        if self.quantity_used > self.reagent.number_of_containers:
            raise ValidationError(
                f"Cannot use {self.quantity_used} containers. Only {self.reagent.number_of_containers} available."
            )

        # Deduct container count
        self.reagent.number_of_containers -= self.quantity_used
        self.reagent.save()

        # Notify managers if stock is low
        if self.reagent.number_of_containers <= self.reagent.low_stock_threshold:
            try:
                manager_group = Group.objects.get(name="Manager")
                for manager in manager_group.user_set.all():
                    if manager.email:
                        notify_low_stock(
                            manager_email=manager.email,
                            reagent_name=self.reagent.name,
                            batch_number=self.reagent.batch_number,
                            number_of_bottles=self.reagent.number_of_containers,
                            threshold=self.reagent.low_stock_threshold
                        )
            except Group.DoesNotExist:
                pass  # Manager group not defined yet

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reagent.name} used by {self.analyst.username} on {self.date_used.strftime('%Y-%m-%d')}"


# ------------------------------------------------------------------------------------------------
# Reagent Request Models
# ------------------------------------------------------------------------------------------------
class ReagentRequest(models.Model):
    """
    Represents a request for purchasing or replenishing reagents.
    Can have multiple request items linked to it.
    """

    requested_by = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    reason = models.TextField()
    date_requested = models.DateTimeField(auto_now_add=True)

    def total_amount(self):
        """Returns total cost of all items in the request."""
        return sum(item.total_price() for item in self.items.all())

    def __str__(self):
        return f"Request by {self.requested_by} on {self.date_requested.strftime('%Y-%m-%d')}"


class ReagentRequestItem(models.Model):
    """
    Represents individual reagent items within a reagent request.
    """

    request = models.ForeignKey(ReagentRequest, on_delete=models.CASCADE, related_name='items')
    reagent_name = models.CharField(max_length=100)
    quantity = models.FloatField()
    unit = models.CharField(max_length=10)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.FloatField()

    def total_price(self):
        """Returns total price for this item (quantity × unit price)."""
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.reagent_name} – {self.quantity} {self.unit}"


# ------------------------------------------------------------------------------------------------
# Reagent Issue Model
# ------------------------------------------------------------------------------------------------
class ReagentIssue(models.Model):
    """
    Logs any issues related to reagents, such as contamination, expiration, or leakage.
    """

    ISSUE_CHOICES = [
        ('contamination', 'Contamination'),
        ('expired', 'Expired Reagent'),
        ('leak', 'Leakage'),
        ('other', 'Other'),
    ]

    reagent = models.ForeignKey(Reagent, on_delete=models.CASCADE)
    issue_type = models.CharField(max_length=20, choices=ISSUE_CHOICES)
    description = models.TextField()
    reported_by = models.CharField(max_length=100)
    date_reported = models.DateTimeField(auto_now_add=True)


# ------------------------------------------------------------------------------------------------
# Inventory Audit Model
# ------------------------------------------------------------------------------------------------
class InventoryAudit(models.Model):
    """
    Records inventory audits of reagents to ensure stock accuracy.
    """

    reagent = models.ForeignKey(Reagent, on_delete=models.CASCADE)
    actual_containers = models.PositiveIntegerField()
    notes = models.TextField(blank=True)
    audited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    date_conducted = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Audit for {self.reagent.name} by {self.audited_by.username} on {self.date_conducted.strftime('%Y-%m-%d')}"
