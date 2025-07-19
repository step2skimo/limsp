from django.db import models
from django.conf import settings

class Expense(models.Model):
    CATEGORY_CHOICES = [
        ("consumables", "Consumables / Reagents"),
        ("maintenance", "Equipment Maintenance"),
        ("salaries", "Salaries / Stipends"),
        ("utilities", "Utilities"),
        ("logistics", "Logistics / Sample Pickup"),
        ("other", "Other"),
    ]

    date = models.DateField()
    description = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="other")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.TextField(blank=True)
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses_entered",
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created"]

    def __str__(self):
        return f"{self.date} – {self.description} (₦{self.amount})"
