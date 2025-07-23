"""
Module: models.py
Description: Defines database models for lab equipment and calibration records.
These models are part of the Laboratory Information Management System (LIMS).
"""

from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

# --------------------------------------------------------------------------------------
# Allowed Parameters (Predefined Analysis Types)
# --------------------------------------------------------------------------------------
# This list defines all the supported analysis parameters for tests performed
# in the laboratory. It can be used for dropdowns, validations, or choices.
ALLOWED_PARAMETERS = [
    # 🔬 Proximate Analysis
    ("Protein", "Protein"),
    ("Fat", "Fat"),
    ("Moisture", "Moisture"),
    ("Ash", "Ash"),
    ("Fiber", "Fiber"),

    # 🌾 Fiber Fractions
    ("Neutral Detergent Fiber", "Neutral Detergent Fiber"),
    ("Acid Detergent Fiber", "Acid Detergent Fiber"),
    ("Acid Detergent Lignin", "Acid Detergent Lignin"),

    # 🔬 Mycotoxins
    ("Total Aflatoxins", "Total Aflatoxins"),
    ("Aflatoxin B1", "Aflatoxin B1"),

    # ⚡ Energy
    ("Gross Energy", "Gross Energy"),

    # 💊 Vitamins (for use with HPLC)
    ("Vitamin A", "Vitamin A"),
    ("Vitamin C", "Vitamin C"),
    ("Vitamin E", "Vitamin E"),
    ("Vitamin B1", "Vitamin B1"),
    ("Vitamin B2", "Vitamin B2"),
]


# --------------------------------------------------------------------------------------
# Equipment Model
# --------------------------------------------------------------------------------------
class Equipment(models.Model):
    """
    Represents laboratory equipment.
    Stores basic details, including supported parameters and operational status.
    """

    parameters_supported = models.ManyToManyField(
        "lims.Parameter",  # Link to Parameter model
        blank=True,
        help_text="Parameters this equipment can analyze."
    )
    name = models.CharField(max_length=100, help_text="Name of the equipment.")
    serial_number = models.CharField(
        max_length=100, unique=True, help_text="Unique serial number."
    )
    model = models.CharField(
        max_length=100, blank=True, help_text="Model number (optional)."
    )
    category = models.CharField(
        max_length=50, blank=True, help_text="Category of the equipment."
    )
    date_installed = models.DateField(help_text="Installation date.")
    manufacturer = models.CharField(
        max_length=100, blank=True, help_text="Manufacturer's name."
    )
    is_active = models.BooleanField(
        default=True, help_text="Indicates whether equipment is active."
    )
    history = HistoricalRecords()
    def __str__(self):
        """
        String representation of equipment for admin and debugging.
        """
        return f"{self.name} ({self.serial_number})"


# --------------------------------------------------------------------------------------
# Calibration Record Model
# --------------------------------------------------------------------------------------
class CalibrationRecord(models.Model):
    """
    Stores calibration history for laboratory equipment.
    Tracks calibration dates, validity, and associated certificates.
    """

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name="calibrations",
        help_text="Equipment that this calibration record belongs to."
    )
    calibration_date = models.DateField(help_text="Date when calibration was performed.")
    calibrated_by = models.CharField(
        max_length=100, help_text="Name of the person/organization that calibrated it."
    )
    expires_on = models.DateField(help_text="Date when calibration expires.")
    certificate = models.FileField(
        upload_to="calibration_certificates/",
        blank=True,
        null=True,
        help_text="Upload calibration certificate (optional)."
    )
    comments = models.TextField(
        blank=True, help_text="Additional comments about the calibration."
    )
    history = HistoricalRecords()
    def is_valid(self):
        """
        Checks if the calibration is still valid (not expired).
        """
        return self.expires_on >= timezone.now().date()

    def __str__(self):
        """
        String representation of the calibration record.
        """
        return f"{self.equipment.name} calibrated {self.calibration_date}"
