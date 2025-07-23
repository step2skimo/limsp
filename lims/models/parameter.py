"""
Module: parameter.py
Description: Defines models for test parameters and their groups.
These models are used to categorize and manage test types within the LIMS.
"""

from django.db import models
from .client import Client
from .equipment import Equipment
from django.conf import settings
from simple_history.models import HistoricalRecords

# --------------------------------------------------------------------------------------
# Parameter Group Model
# --------------------------------------------------------------------------------------
class ParameterGroup(models.Model):
    """
    Represents a group of related test parameters.
    Example: 'Proximate Analysis', 'Mycotoxins', etc.
    """

    name = models.CharField(
        max_length=100,
        help_text="Name of the parameter group (e.g., Proximate Analysis)."
    )
    is_extension = models.BooleanField(
        default=False,
        help_text="Indicates if this is an extension parameter group."
    )

    def __str__(self):
        """
        String representation of the parameter group.
        """
        return self.name


# --------------------------------------------------------------------------------------
# Parameter Model
# --------------------------------------------------------------------------------------
class Parameter(models.Model):
    """
    Represents a specific test parameter within a parameter group.
    Example: 'Protein', 'Aflatoxin B1', etc.
    """

    group = models.ForeignKey(
        ParameterGroup,
        on_delete=models.CASCADE,
        help_text="The group this parameter belongs to."
    )
    default_equipment = models.ForeignKey(
        Equipment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Preferred equipment for this test (if any)."
    )
    name = models.CharField(
        max_length=100,
        help_text="Name of the parameter (e.g., Moisture)."
    )
    unit = models.CharField(
        max_length=20,
        help_text="Measurement unit for this parameter (e.g., %, mg/kg)."
    )
    method = models.CharField(
        max_length=150,
        help_text="Method used for analyzing this parameter."
    )
    ref_limit = models.CharField(
        max_length=50,
        help_text="Reference limit or threshold for this parameter."
    )
    default_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Default price for analyzing this parameter."
    )

    def __str__(self):
        """
        String representation of the parameter (including its group).
        Example: 'Protein (Proximate Analysis)'
        """
        return f"{self.name} ({self.group.name})"
