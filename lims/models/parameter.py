from django.db import models
from .client import Client
from .equipment import Equipment
from django.conf import settings


class ParameterGroup(models.Model):
    name = models.CharField(max_length=100)
    is_extension = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Parameter(models.Model):
    group = models.ForeignKey(ParameterGroup, on_delete=models.CASCADE)
    default_equipment = models.ForeignKey(
        Equipment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Preferred device for this test"
    )
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=20)
    method = models.CharField(max_length=150)
    ref_limit = models.CharField(max_length=50)
    default_price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.name} ({self.group.name})"
